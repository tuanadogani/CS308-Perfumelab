from rest_framework import serializers

from .models import Invoice, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    productId = serializers.IntegerField(source="product_id")
    productName = serializers.CharField(source="product.name", read_only=True)
    brand = serializers.CharField(source="product.brand.name", read_only=True)
    unitPrice = serializers.FloatField(source="unit_price")
    unitCost = serializers.FloatField(source="unit_cost")
    lineTotal = serializers.FloatField(source="line_total", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "productId",
            "productName",
            "brand",
            "quantity",
            "unitPrice",
            "unitCost",
            "lineTotal",
        ]


class InvoiceCustomerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.EmailField()
    taxId = serializers.CharField(source="tax_id")


class InvoiceSerializer(serializers.ModelSerializer):
    orderId = serializers.IntegerField(source="order_id")
    issuedAt = serializers.DateTimeField(source="issued_at")
    total = serializers.FloatField()
    status = serializers.CharField(source="order.status")
    shippingAddress = serializers.CharField(source="order.shipping_address")
    cardLast4 = serializers.CharField(source="order.card_last4")
    customer = InvoiceCustomerSerializer(source="order.user", read_only=True)
    items = OrderItemSerializer(source="order.items", many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "number",
            "orderId",
            "issuedAt",
            "total",
            "status",
            "shippingAddress",
            "cardLast4",
            "customer",
            "items",
        ]

