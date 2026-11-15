from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from catalog.models import Product

from .models import Delivery, Invoice, InvoiceCounter, Order, OrderItem, OrderStatus

# Allowed forward moves for the product manager (req 12). Cancelling is the customer's own action.
NEXT_STATUS = {
    OrderStatus.PROCESSING: OrderStatus.IN_TRANSIT,
    OrderStatus.IN_TRANSIT: OrderStatus.DELIVERED,
}


def next_invoice_number():
    """Next gapless invoice number. Must run inside the checkout transaction."""
    counter, _ = InvoiceCounter.objects.select_for_update().get_or_create(name="invoice")
    counter.last += 1
    counter.save(update_fields=["last"])
    return f"INV-{counter.last:07d}"


@transaction.atomic
def place_order(user, cart, card=None, shipping_address=None):
    """Turn the cart into an order.

    Product rows are locked with SELECT ... FOR UPDATE in id order, so two customers buying
    the last bottle at the same time cannot both succeed and deadlocks are avoided (req 18).
    """
    lines = list(cart.items.select_related("product"))
    if not lines:
        raise ValidationError("Your cart is empty.")
    address = shipping_address or user.home_address
    if not address:
        raise ValidationError("A delivery address is required.")

    locked = {
        p.pk: p
        for p in Product.objects.select_for_update().filter(pk__in=[l.product_id for l in lines]).order_by("pk")
    }
    for line in lines:
        product = locked[line.product_id]
        if not product.active or product.stock < line.quantity:
            raise ValidationError(f"Not enough stock for {product.name}.")

    order = Order.objects.create(
        user=user, shipping_address=address, total=0, card_last4=card.last4 if card else ""
    )
    total = 0
    for line in lines:
        product = locked[line.product_id]
        item = OrderItem.objects.create(
            order=order, product=product, quantity=line.quantity,
            unit_price=product.price, unit_cost=product.effective_cost,
        )
        Delivery.objects.create(order_item=item, delivery_address=address)
        Product.objects.filter(pk=product.pk).update(
            stock=F("stock") - line.quantity, popularity=F("popularity") + line.quantity
        )
        total += item.line_total
    order.total = total
    order.save(update_fields=["total"])
    Invoice.objects.create(order=order, number=next_invoice_number(), total=total)
    cart.items.all().delete()
    return order


@transaction.atomic
def cancel_order(order):
    """Only a 'processing' order can be cancelled (req 14). Stock goes back on the shelf."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != OrderStatus.PROCESSING:
        raise ValidationError("Only orders in 'processing' status can be cancelled.")
    for item in order.items.all():
        Product.objects.filter(pk=item.product_id).update(
            stock=F("stock") + item.quantity, popularity=F("popularity") - item.quantity
        )
    order.status = OrderStatus.CANCELLED
    order.save(update_fields=["status"])
    return order


@transaction.atomic
def advance_status(order):
    """Product manager moves processing -> in_transit -> delivered (req 3, 12)."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    nxt = NEXT_STATUS.get(order.status)
    if nxt is None:
        raise ValidationError(f"Cannot advance an order that is '{order.status}'.")
    order.status = nxt
    if nxt == OrderStatus.DELIVERED:
        order.delivered_at = timezone.now()
        Delivery.objects.filter(order_item__order=order).update(completed=True)
    order.save(update_fields=["status", "delivered_at"])
    return order
