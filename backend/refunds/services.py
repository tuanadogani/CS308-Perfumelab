from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from catalog.models import Product
from orders.models import Order, OrderStatus

from .models import RefundRequest, RefundStatus

REFUND_WINDOW = timedelta(days=30)


@transaction.atomic
def request_refund(user, order_item, reason=""):
    """Customer asks to return a delivered item within 30 days of purchase (req 16)."""
    order = Order.objects.get(pk=order_item.order_id)  # fresh status, not a cached copy
    if order.user_id != user.pk:
        raise PermissionDenied("This is not your order.")
    if order.status != OrderStatus.DELIVERED:
        raise ValidationError("Only delivered orders can be refunded.")
    if timezone.now() - order.created_at > REFUND_WINDOW:
        raise ValidationError("The 30-day refund window has passed.")
    if RefundRequest.objects.filter(order_item=order_item).exists():
        raise ValidationError("A refund was already requested for this item.")
    # unit_price is the price paid at purchase time, so a discount applied then is preserved.
    return RefundRequest.objects.create(
        order_item=order_item, reason=reason, amount=order_item.unit_price * order_item.quantity
    )


@transaction.atomic
def decide_refund(refund, manager, approve):
    """Sales manager approves after the product is back in the store: restock + email (req 16)."""
    if manager.role != "sales_manager":
        raise PermissionDenied("Only sales managers can decide refunds.")
    refund = RefundRequest.objects.select_for_update().get(pk=refund.pk)
    if refund.status != RefundStatus.REQUESTED:
        raise ValidationError("This request was already decided.")
    refund.status = RefundStatus.APPROVED if approve else RefundStatus.REJECTED
    refund.decided_by = manager
    refund.decided_at = timezone.now()
    refund.save(update_fields=["status", "decided_by", "decided_at"])
    if approve:
        item = refund.order_item
        Product.objects.filter(pk=item.product_id).update(
            stock=F("stock") + item.quantity, popularity=F("popularity") - item.quantity
        )
        order = item.order
        if not order.items.exclude(refund__status=RefundStatus.APPROVED).exists():
            order.status = OrderStatus.REFUNDED
            order.save(update_fields=["status"])
        send_mail(
            "Your refund was approved",
            f"We refunded {refund.amount} TL for {item.product.name}.",
            None, [order.user.email], fail_silently=True,
        )
    return refund
