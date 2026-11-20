from django.utils import timezone
from rest_framework import serializers

from orders.customer_serializers import CustomerOrderSerializer

from .models import CreditCard


class CheckoutSerializer(serializers.Serializer):
    """Card details typed on the checkout page (req 4, 15).

    The full number and the CVV are only checked here; they are never saved (req 17).
    """

    cardNumber = serializers.CharField(max_length=30)
    holderName = serializers.CharField(max_length=150)
    expiryMonth = serializers.IntegerField(min_value=1, max_value=12)
    expiryYear = serializers.IntegerField(min_value=2000, max_value=2100)
    cvv = serializers.RegexField(r"^\d{3,4}$", write_only=True)
    shippingAddress = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_cardNumber(self, value):
        digits = "".join(ch for ch in value if ch.isdigit())
        if not 13 <= len(digits) <= 19 or any(not (ch.isdigit() or ch in " -") for ch in value):
            raise serializers.ValidationError("Card number must have 13-19 digits.")
        return digits

    def validate(self, data):
        today = timezone.localdate()
        if (data["expiryYear"], data["expiryMonth"]) < (today.year, today.month):
            raise serializers.ValidationError({"expiryYear": "This card has expired."})
        return data


class SavedCardSerializer(serializers.ModelSerializer):
    """What the checkout page may show about a saved card: never the number."""

    holderName = serializers.CharField(source="holder_name")
    expiryMonth = serializers.IntegerField(source="expiry_month")
    expiryYear = serializers.IntegerField(source="expiry_year")

    class Meta:
        model = CreditCard
        fields = ["id", "brand", "last4", "holderName", "expiryMonth", "expiryYear"]
        read_only_fields = fields


class InvoiceSummarySerializer(serializers.Serializer):
    number = serializers.CharField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    issuedAt = serializers.DateTimeField(source="issued_at")


class CheckoutResultSerializer(serializers.Serializer):
    """Everything the 'thank you / invoice' screen needs after paying (req 4)."""

    order = CustomerOrderSerializer(source="*")
    invoice = InvoiceSummarySerializer()
    transactionId = serializers.CharField(source="payment.transaction_id")
    cardLast4 = serializers.CharField(source="card_last4")
