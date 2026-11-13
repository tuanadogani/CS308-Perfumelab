from rest_framework import serializers
from .models import Category, Product, Order, OrderItem, Comment, Rating
from django.contrib.auth import get_user_model

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'product_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_product_count(self, obj):
        return obj.products.count()


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    discounted_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'model', 'serial_number', 'description', 'stock',
            'price', 'warranty_status', 'distributor', 'category', 'category_name',
            'brand', 'scent_family', 'top_notes', 'heart_notes', 'base_notes',
            'size_ml', 'image_url', 'cost_price', 'discount_rate', 'discounted_price',
            'popularity_score', 'average_rating', 'rating_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'popularity_score']

    def get_average_rating(self, obj):
        ratings = obj.ratings.all()
        if ratings.exists():
            return round(sum(r.rating for r in ratings) / ratings.count(), 1)
        return None

    def get_rating_count(self, obj):
        return obj.ratings.count()


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product listings"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    discounted_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'model', 'price', 'discounted_price', 'stock',
            'category_name', 'brand', 'scent_family', 'image_url', 'average_rating'
        ]

    def get_average_rating(self, obj):
        ratings = obj.ratings.all()
        if ratings.exists():
            return round(sum(r.rating for r in ratings) / ratings.count(), 1)
        return None


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_model = serializers.CharField(source='product.model', read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_model', 'quantity', 'price_at_purchase', 'total_price']
        read_only_fields = ['price_at_purchase']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'customer_name', 'customer_email', 'status',
            'total_price', 'delivery_address', 'payment_method',
            'items', 'created_at', 'updated_at', 'delivered_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class DeliveryListSerializer(serializers.ModelSerializer):
    """Delivery list for Product Manager - Requirement 12"""
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    is_delivered = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'customer_name', 'customer_email', 'status',
            'total_price', 'delivery_address', 'items', 'is_delivered',
            'created_at', 'delivered_at'
        ]
        read_only_fields = ['created_at', 'delivered_at']

    def get_is_delivered(self, obj):
        return obj.status == 'delivered'


class CommentSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Comment
        fields = [
            'id', 'product', 'product_name', 'customer', 'customer_name',
            'customer_email', 'order', 'comment_text', 'status',
            'created_at', 'updated_at', 'reviewed_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'reviewed_at', 'customer']

    def create(self, validated_data):
        validated_data['customer'] = self.context['request'].user
        return super().create(validated_data)


class RatingSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = Rating
        fields = ['id', 'product', 'customer', 'customer_name', 'order', 'rating', 'created_at']
        read_only_fields = ['created_at', 'customer']

    def create(self, validated_data):
        validated_data['customer'] = self.context['request'].user
        return super().create(validated_data)
