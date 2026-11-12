from django.conf import settings
from django.db import models
from django.db.models import Q


class RefundStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class RefundRequest(models.Model):
    order_item = models.OneToOneField("orders.OrderItem", on_delete=models.PROTECT, related_name="refund")
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=RefundStatus.choices, default=RefundStatus.REQUESTED)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # frozen at request time
    requested_at = models.DateTimeField(auto_now_add=True)
    received_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(amount__gte=0), name="refund_amount_gte_0")]
