"""Product manager API: catalog maintenance, delivery workflow and moderation."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Avg
from django.shortcuts import get_object_or_404
from rest_framework import serializers, generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsProductManager
from orders.models import Delivery, Order
from orders.services import advance_status
from reviews.models import Comment
from reviews.services import review_comment
from .models import Brand, Category, NoteFamily, Product, ProductNote
from .serializers import ProductSerializer


class ManagedProductSerializer(serializers.ModelSerializer):
    brand = serializers.CharField(max_length=100)
    category = serializers.SlugRelatedField(slug_field='slug', queryset=Category.objects.all())
    families = serializers.ListField(child=serializers.CharField(max_length=50), required=False)
    notes = serializers.DictField(child=serializers.ListField(child=serializers.CharField(max_length=100)), required=False)

    class Meta:
        model = Product
        fields = ['id', 'name', 'model', 'serial_number', 'description', 'stock',
                  'warranty_status', 'distributor', 'brand', 'category', 'gender',
                  'volume_ml', 'families', 'notes', 'active']
        read_only_fields = ['id']
        extra_kwargs = {'volume_ml': {'min_value': 1}, 'stock': {'min_value': 0}}

    def validate_notes(self, value):
        if set(value) - {'top', 'heart', 'base'}:
            raise serializers.ValidationError('Allowed tiers: top, heart, base.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        # Pricing belongs to the sales manager; new products start at zero.
        return self._save(None, validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        return self._save(instance, validated_data)

    def _save(self, instance, data):
        families = data.pop('families', None)
        notes = data.pop('notes', None)
        if 'brand' in data:
            data['brand'] = Brand.objects.get_or_create(name=data['brand'])[0]
        if instance is None:
            instance = Product.objects.create(price=0, base_price=0, **data)
        else:
            # Update only supplied fields, preserving concurrent sales/stock changes.
            for key, value in data.items():
                setattr(instance, key, value)
            if data:
                instance.save(update_fields=list(data))
        if families is not None:
            instance.families.set([NoteFamily.objects.get_or_create(name=name)[0] for name in set(families)])
        if notes is not None:
            instance.notes.all().delete()
            ProductNote.objects.bulk_create([
                ProductNote(product=instance, tier=tier, name=name)
                for tier, names in notes.items() for name in set(names)
            ])
        return instance

    def to_representation(self, instance):
        data = ProductSerializer(instance, context=self.context).data
        data['active'] = instance.active
        return data


class ManagerProducts(generics.ListCreateAPIView):
    permission_classes = [IsProductManager]
    serializer_class = ManagedProductSerializer
    pagination_class = None
    queryset = Product.objects.select_related('brand', 'category').prefetch_related('notes', 'families').annotate(avg_rating=Avg('ratings__score')).order_by('id')


class ManagerProduct(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsProductManager]
    serializer_class = ManagedProductSerializer
    queryset = ManagerProducts.queryset
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def perform_destroy(self, instance):
        instance.active = False
        instance.save(update_fields=['active'])


class ManagedCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'slug', 'name']
        read_only_fields = ['id']


class ManagerCategories(generics.ListCreateAPIView):
    permission_classes = [IsProductManager]
    serializer_class = ManagedCategorySerializer
    queryset = Category.objects.all()
    pagination_class = None


class ManagerCategory(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsProductManager]
    serializer_class = ManagedCategorySerializer
    queryset = Category.objects.all()

    def perform_destroy(self, instance):
        if instance.products.exists():
            raise ValidationError('Move all products (including inactive products) before deleting this category.')
        instance.delete()


class DeliverySerializer(serializers.ModelSerializer):
    orderId = serializers.IntegerField(source='order_item.order_id')
    customerId = serializers.IntegerField(source='customer_id')
    productId = serializers.IntegerField(source='product_id')
    productName = serializers.CharField(source='order_item.product.name')
    totalPrice = serializers.DecimalField(source='total_price', max_digits=12, decimal_places=2)
    address = serializers.CharField(source='delivery_address')
    status = serializers.CharField(source='order_item.order.status')

    class Meta:
        model = Delivery
        fields = ['id', 'orderId', 'customerId', 'productId', 'productName', 'quantity', 'totalPrice', 'address', 'status', 'completed']


class ManagerDeliveries(generics.ListAPIView):
    permission_classes = [IsProductManager]
    serializer_class = DeliverySerializer
    pagination_class = None
    queryset = Delivery.objects.select_related('order_item__order', 'order_item__product').exclude(order_item__order__status__in=['cancelled', 'refunded']).order_by('-id')


class ManagerOrderStatus(APIView):
    permission_classes = [IsProductManager]

    @transaction.atomic
    def patch(self, request, pk):
        order = get_object_or_404(Order.objects.select_for_update(), pk=pk)
        from orders.services import NEXT_STATUS
        if request.data.get('status') != NEXT_STATUS.get(order.status) or order.status not in NEXT_STATUS:
            raise ValidationError('Only processing → in_transit → delivered transitions are allowed.')
        try:
            order = advance_status(order)
        except DjangoValidationError as error:
            raise ValidationError(error.messages)
        return Response({'id': order.pk, 'status': order.status})


class CommentSerializer(serializers.ModelSerializer):
    productName = serializers.CharField(source='product.name')
    customerName = serializers.CharField(source='user.name')

    class Meta:
        model = Comment
        fields = ['id', 'product_id', 'productName', 'customerName', 'text', 'approved', 'reviewed_at', 'created_at']


class ManagerComments(generics.ListAPIView):
    permission_classes = [IsProductManager]
    serializer_class = CommentSerializer
    pagination_class = None
    queryset = Comment.objects.select_related('product', 'user')


class ModerationInput(serializers.Serializer):
    approve = serializers.BooleanField(required=True)


class ManagerComment(APIView):
    permission_classes = [IsProductManager]

    @transaction.atomic
    def patch(self, request, pk):
        data = ModerationInput(data=request.data)
        data.is_valid(raise_exception=True)
        comment = get_object_or_404(Comment.objects.select_for_update().select_related('product', 'user'), pk=pk)
        return Response(CommentSerializer(review_comment(comment, request.user, data.validated_data['approve'])).data)
