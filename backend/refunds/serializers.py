from rest_framework import serializers

from .models import RefundRequest, RefundStatus


class RefundRequestSerializer(serializers.ModelSerializer):
    orderItemId = serializers.IntegerField(source="order_item_id", read_only=True)
    requestedAt = serializers.DateTimeField(source="requested_at", read_only=True)
    decidedAt = serializers.DateTimeField(source="decided_at", read_only=True)
    receivedAt = serializers.DateTimeField(source="received_at", read_only=True)

    class Meta:
        model = RefundRequest
        fields = ["id", "orderItemId", "reason", "status", "amount", "requestedAt", "receivedAt", "decidedAt"]
        read_only_fields = fields


class CreateRefundSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class SalesRefundSerializer(RefundRequestSerializer):
    orderId = serializers.IntegerField(source="order_item.order_id", read_only=True)
    customerId = serializers.IntegerField(source="order_item.order.user_id", read_only=True)
    customerName = serializers.CharField(source="order_item.order.user.name", read_only=True)
    customerEmail = serializers.EmailField(source="order_item.order.user.email", read_only=True)
    productId = serializers.IntegerField(source="order_item.product_id", read_only=True)
    productName = serializers.CharField(source="order_item.product.name", read_only=True)
    quantity = serializers.IntegerField(source="order_item.quantity", read_only=True)
    unitPrice = serializers.DecimalField(source="order_item.unit_price", max_digits=10, decimal_places=2, read_only=True)
    receivedBy = serializers.IntegerField(source="received_by_id", read_only=True, allow_null=True)
    decidedBy = serializers.IntegerField(source="decided_by_id", read_only=True, allow_null=True)

    class Meta(RefundRequestSerializer.Meta):
        fields = RefundRequestSerializer.Meta.fields + [
            "orderId", "customerId", "customerName", "customerEmail",
            "productId", "productName", "quantity", "unitPrice", "receivedBy", "decidedBy",
        ]
        read_only_fields = fields


class RefundFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=RefundStatus.choices, required=False)


class RefundDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
