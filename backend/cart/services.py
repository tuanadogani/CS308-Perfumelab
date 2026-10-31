from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Cart, CartItem


def add_to_cart(cart, product, quantity=1):
    """Out-of-stock products can be found but never added (req 7); never more than the stock."""
    if quantity < 1:
        raise ValidationError("Quantity must be at least 1.")
    if not product.active or product.stock <= 0:
        raise ValidationError("This product is out of stock.")
    item = CartItem.objects.filter(cart=cart, product=product).first()
    if item is None:
        return CartItem.objects.create(cart=cart, product=product, quantity=min(quantity, product.stock))
    item.quantity = min(item.quantity + quantity, product.stock)
    item.save(update_fields=["quantity"])
    return item


@transaction.atomic
def merge_guest_cart(guest_cart, user):
    """On login, keep what the guest already added (req 4). Quantities are summed, capped at stock."""
    user_cart, _ = Cart.objects.get_or_create(user=user)
    for item in guest_cart.items.select_related("product"):
        if item.product.active and item.product.stock > 0:
            add_to_cart(user_cart, item.product, item.quantity)
    guest_cart.delete()
    return user_cart
