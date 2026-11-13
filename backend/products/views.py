from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import serializers as drf_serializers
from django.utils import timezone
from django.db.models import Q, Avg
from .models import Category, Product, Order, OrderItem, Comment, Rating
from .serializers import (
    CategorySerializer, ProductSerializer, ProductListSerializer,
    OrderSerializer, DeliveryListSerializer, CommentSerializer, RatingSerializer
)


class IsProductManager(IsAuthenticated):
    """Permission class for Product Manager role"""
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return hasattr(request.user, 'role') and request.user.role == 'product_manager'


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Category management for Product Manager - Requirement 12
    GET /api/categories/ - List all categories (public)
    POST /api/categories/ - Create category (PM only)
    PUT/PATCH /api/categories/{id}/ - Update category (PM only)
    DELETE /api/categories/{id}/ - Delete category (PM only)
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsProductManager()]


class ProductViewSet(viewsets.ModelViewSet):
    """
    Product management - Requirement 9, 12
    GET /api/products/ - List products with search, filter, sort (public)
    GET /api/products/{id}/ - Get product details (public)
    POST /api/products/ - Create product (PM only)
    PUT/PATCH /api/products/{id}/ - Update product (PM only)
    DELETE /api/products/{id}/ - Delete product (PM only)
    PATCH /api/products/{id}/update-stock/ - Update stock (PM only)
    """
    queryset = Product.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'brand', 'model']
    ordering_fields = ['price', 'popularity_score', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsProductManager()]

    def get_queryset(self):
        queryset = Product.objects.all()

        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__name=category)

        # Filter by brand
        brand = self.request.query_params.get('brand')
        if brand:
            queryset = queryset.filter(brand=brand)

        # Filter by scent family
        family = self.request.query_params.get('family')
        if family:
            queryset = queryset.filter(scent_family=family)

        # Search query
        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) | Q(description__icontains=q)
            )

        # Sort by price or popularity
        sort = self.request.query_params.get('sort')
        if sort == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort == 'popularity':
            queryset = queryset.order_by('-popularity_score')

        return queryset

    @action(detail=True, methods=['patch'], permission_classes=[IsProductManager])
    def update_stock(self, request, pk=None):
        """Update product stock - Requirement 12"""
        product = self.get_object()
        new_stock = request.data.get('stock')

        if new_stock is None:
            return Response(
                {'error': 'Stock value is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            new_stock = int(new_stock)
            if new_stock < 0:
                raise ValueError('Stock cannot be negative')
        except (ValueError, TypeError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        product.stock = new_stock
        product.save()

        serializer = self.get_serializer(product)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    """
    Order management
    GET /api/orders/ - List orders (authenticated users see their own, PM sees all)
    GET /api/orders/{id}/ - Get order details
    POST /api/orders/ - Create order (customer)
    PATCH /api/orders/{id}/update-status/ - Update order status (PM only)
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'role') and user.role == 'product_manager':
            # PM sees all orders
            return Order.objects.all()
        # Customers see only their own orders
        return Order.objects.filter(customer=user)

    @action(detail=True, methods=['patch'], permission_classes=[IsProductManager])
    def update_status(self, request, pk=None):
        """Update order status - Requirement 12"""
        order = self.get_object()
        new_status = request.data.get('status')

        valid_statuses = ['processing', 'in_transit', 'delivered', 'cancelled']
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = new_status
        if new_status == 'delivered':
            order.delivered_at = timezone.now()
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)


class DeliveryListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Delivery list for Product Manager - Requirement 12
    GET /api/deliveries/ - List all pending deliveries with addresses
    """
    serializer_class = DeliveryListSerializer
    permission_classes = [IsProductManager]

    def get_queryset(self):
        # Show orders that are not cancelled
        queryset = Order.objects.exclude(status='cancelled')

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset


class CommentViewSet(viewsets.ModelViewSet):
    """
    Comment management - Requirement 5, 12
    GET /api/comments/ - List comments (approved only for public, all for PM)
    POST /api/comments/ - Create comment (customer with delivered order)
    PATCH /api/comments/{id}/approve/ - Approve comment (PM only)
    PATCH /api/comments/{id}/reject/ - Reject comment (PM only)
    """
    serializer_class = CommentSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        elif self.action == 'create':
            return [IsAuthenticated()]
        return [IsProductManager()]

    def get_queryset(self):
        user = self.request.user

        # Product Managers see all comments
        if user.is_authenticated and hasattr(user, 'role') and user.role == 'product_manager':
            queryset = Comment.objects.all()

            # Filter by status for PM
            status_filter = self.request.query_params.get('status')
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            return queryset

        # Public users see only approved comments
        queryset = Comment.objects.filter(status='approved')

        # Filter by product
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        return queryset

    def perform_create(self, serializer):
        """Ensure user has received the product before commenting - Requirement 5"""
        order_id = self.request.data.get('order')
        product_id = self.request.data.get('product')

        try:
            order = Order.objects.get(
                id=order_id,
                customer=self.request.user,
                status='delivered',
                items__product_id=product_id
            )
        except Order.DoesNotExist:
            raise drf_serializers.ValidationError(
                'You can only comment on products you have received.'
            )

        serializer.save(customer=self.request.user)

    @action(detail=True, methods=['patch'], permission_classes=[IsProductManager])
    def approve(self, request, pk=None):
        """Approve comment - Requirement 12"""
        comment = self.get_object()
        comment.status = 'approved'
        comment.reviewed_at = timezone.now()
        comment.save()

        serializer = self.get_serializer(comment)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], permission_classes=[IsProductManager])
    def reject(self, request, pk=None):
        """Reject comment - Requirement 12"""
        comment = self.get_object()
        comment.status = 'rejected'
        comment.reviewed_at = timezone.now()
        comment.save()

        serializer = self.get_serializer(comment)
        return Response(serializer.data)


class RatingViewSet(viewsets.ModelViewSet):
    """
    Rating management - Requirement 5 (submitted directly without approval)
    GET /api/ratings/ - List ratings
    POST /api/ratings/ - Create rating (customer with delivered order)
    """
    serializer_class = RatingSerializer
    queryset = Rating.objects.all()

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Rating.objects.all()

        # Filter by product
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        return queryset

    def perform_create(self, serializer):
        """Ensure user has received the product before rating - Requirement 5"""
        order_id = self.request.data.get('order')
        product_id = self.request.data.get('product')

        try:
            order = Order.objects.get(
                id=order_id,
                customer=self.request.user,
                status='delivered',
                items__product_id=product_id
            )
        except Order.DoesNotExist:
            raise drf_serializers.ValidationError(
                'You can only rate products you have received.'
            )

        serializer.save(customer=self.request.user)
