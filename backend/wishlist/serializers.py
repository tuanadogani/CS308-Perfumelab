from decimal import Decimal
from rest_framework import serializers

from .models import Notification


class SetDiscountSerializer(serializers.Serializer):
    product_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1, required=False
    )
    productIds = serializers.ListField(
        child=serializers.IntegerField(), min_length=1, required=False
    )
    discount_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal("0"), max_value=Decimal("100"), required=False
    )
    discountRate = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal("0"), max_value=Decimal("100"), required=False
    )

    def validate(self, attrs):
        ids = attrs.get("product_ids")
        if ids is None:
            ids = attrs.get("productIds")
        if not ids:
            raise serializers.ValidationError({"product_ids": "At least one product id is required."})

        rate = attrs.get("discount_rate")
        if rate is None:
            rate = attrs.get("discountRate")
        if rate is None:
            raise serializers.ValidationError({"discount_rate": "Discount rate is required."})

        attrs["resolved_product_ids"] = ids
        attrs["resolved_discount_rate"] = rate
        return attrs


class NotificationSerializer(serializers.ModelSerializer):
    productId = serializers.IntegerField(source="product_id", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "productId", "message", "read", "createdAt"]
        read_only_fields = ["id", "productId", "message", "createdAt"]

