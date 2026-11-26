import re

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class CreditCard(models.Model):
    """Only a salted hash and the last four digits are stored (req 15, 17).

    The full card number and the CVV never touch the database.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cards")
    number_hash = models.CharField(max_length=128)
    last4 = models.CharField(max_length=4)
    brand = models.CharField(max_length=20, blank=True)
    holder_name = models.CharField(max_length=150)
    expiry_month = models.PositiveSmallIntegerField()
    expiry_year = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(expiry_month__gte=1, expiry_month__lte=12),
                name="card_expiry_month_1_12",
            ),
        ]

    @classmethod
    def from_number(cls, user, number, holder_name, expiry_month, expiry_year, brand=""):
        digits = cls.normalize_number(number)
        if not isinstance(holder_name, str) or not holder_name.strip():
            raise ValueError("Card holder name is required.")
        if (type(expiry_month) is not int or type(expiry_year) is not int
                or not 1 <= expiry_month <= 12 or not 1 <= expiry_year <= 9999):
            raise ValueError("Invalid card expiry date.")
        today = timezone.localdate()
        if (expiry_year, expiry_month) < (today.year, today.month):
            raise ValueError("The card has expired.")
        return cls.objects.create(
            user=user, number_hash=make_password(digits), last4=digits[-4:], brand=brand,
            holder_name=holder_name.strip(), expiry_month=expiry_month, expiry_year=expiry_year,
        )

    @staticmethod
    def normalize_number(number):
        if not isinstance(number, str) or not re.fullmatch(r"[0-9 -]+", number):
            raise ValueError("Card number must contain only digits, spaces or hyphens.")
        digits = number.replace(" ", "").replace("-", "")
        if not 13 <= len(digits) <= 19:
            raise ValueError("Card number must have 13-19 digits.")
        return digits

    def matches(self, number):
        try:
            digits = self.normalize_number(number)
        except ValueError:
            return False
        return check_password(digits, self.number_hash)

    def __str__(self):
        return f"{self.brand or 'Card'} ****{self.last4}"


class Payment(models.Model):
    """Confirmation from the (mock-up) bank for one order (req 4)."""

    order = models.OneToOneField("orders.Order", on_delete=models.PROTECT, related_name="payment")
    card = models.ForeignKey(CreditCard, null=True, on_delete=models.SET_NULL, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_id = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(amount__gte=0), name="payment_amount_gte_0")]


class PaymentRefund(models.Model):
    """Bank confirmation tied to the original payment and one returned order line."""

    refund_request = models.OneToOneField(
        "refunds.RefundRequest", on_delete=models.PROTECT, related_name="payment_refund"
    )
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="refunds")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="payment_refund_amount_gte_0"),
        ]
