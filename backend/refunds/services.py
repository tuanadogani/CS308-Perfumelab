from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounts.models import Role
from catalog.models import Product
from orders.models import Order, OrderItem, OrderStatus

from .models import RefundRequest, RefundStatus

REFUND_WINDOW = timedelta(days=30)


@transaction.atomic
def request_refund(user, order_item, reason=""):
    """Customer asks to return a delivered item within 30 days of purchase (req 16)."""
    # Serialize requests for an order so duplicate submissions return a validation
    # error rather than racing into the database's one-to-one constraint.
    order = Order.objects.select_for_update().get(pk=order_item.order_id)
    order_item = OrderItem.objects.get(pk=order_item.pk, order=order)
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
def receive_return(refund, manager):
    """Record physical receipt once; receipt itself does not restock or approve."""
    if manager.role != Role.SALES_MANAGER:
        raise PermissionDenied("Only sales managers can receive returns.")
    refund = RefundRequest.objects.select_for_update().get(pk=refund.pk)
    if refund.status != RefundStatus.REQUESTED:
        raise ValidationError("This request was already decided.")
    if refund.received_at is None:
        refund.received_at = timezone.now()
        refund.received_by = manager
        refund.save(update_fields=["received_at", "received_by"])
    return refund


@transaction.atomic
def decide_refund(refund, manager, approve):
    """Sales manager approves after the product is back in the store: restock + email (req 16)."""
    if manager.role != Role.SALES_MANAGER:
        raise PermissionDenied("Only sales managers can decide refunds.")
    # Serialize decisions for different lines of the same order as well, so the
    # last approval reliably marks the whole order refunded.
    order_id = RefundRequest.objects.values_list("order_item__order_id", flat=True).get(pk=refund.pk)
    order = Order.objects.select_for_update().get(pk=order_id)
    refund = RefundRequest.objects.select_for_update().get(pk=refund.pk)
    if refund.status != RefundStatus.REQUESTED:
        raise ValidationError("This request was already decided.")
    if approve:
        if refund.received_at is None:
            raise ValidationError("The returned product must be received before approval.")
        if order.status != OrderStatus.DELIVERED:
            raise ValidationError("Only delivered orders can be refunded.")
    refund.status = RefundStatus.APPROVED if approve else RefundStatus.REJECTED
    refund.decided_by = manager
    refund.decided_at = timezone.now()
    refund.save(update_fields=["status", "decided_by", "decided_at"])
    if approve:
        item = refund.order_item
        Product.objects.filter(pk=item.product_id).update(
            stock=F("stock") + item.quantity, popularity=F("popularity") - item.quantity
        )
        if not order.items.exclude(refund__status=RefundStatus.APPROVED).exists():
            order.status = OrderStatus.REFUNDED
            order.save(update_fields=["status"])
        send_mail(
            "Your refund was approved",
            f"We refunded {refund.amount} TL for {item.product.name}.",
            None, [order.user.email], fail_silently=True,
        )
    return refund
