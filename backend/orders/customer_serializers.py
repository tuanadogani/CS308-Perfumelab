from rest_framework import serializers

from refunds.serializers import RefundRequestSerializer

from .models import Order, OrderItem


class CustomerOrderItemSerializer(serializers.ModelSerializer):
    productId = serializers.IntegerField(source="product_id", read_only=True)
    productName = serializers.CharField(source="product.name", read_only=True)
    unitPrice = serializers.DecimalField(source="unit_price", max_digits=10, decimal_places=2, read_only=True)
    lineTotal = serializers.DecimalField(source="line_total", max_digits=12, decimal_places=2, read_only=True)
    refund = RefundRequestSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "productId", "productName", "quantity", "unitPrice", "lineTotal", "refund"]
        read_only_fields = fields


class CustomerOrderSerializer(serializers.ModelSerializer):
    shippingAddress = serializers.CharField(source="shipping_address", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    deliveredAt = serializers.DateTimeField(source="delivered_at", read_only=True)
    items = CustomerOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "status", "total", "shippingAddress", "createdAt", "deliveredAt", "items"]
        read_only_fields = fields
