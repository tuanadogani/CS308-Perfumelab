from rest_framework import serializers

from .models import RefundRequest


class RefundRequestSerializer(serializers.ModelSerializer):
    orderItemId = serializers.IntegerField(source="order_item_id", read_only=True)
    requestedAt = serializers.DateTimeField(source="requested_at", read_only=True)
    decidedAt = serializers.DateTimeField(source="decided_at", read_only=True)

    class Meta:
        model = RefundRequest
        fields = ["id", "orderItemId", "reason", "status", "amount", "requestedAt", "decidedAt"]
        read_only_fields = fields


class CreateRefundSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=2000)
