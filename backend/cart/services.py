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


def get_cart(user=None, session_key=None):
    """The cart of a logged-in user, or of a guest identified by their session key (req 4).

    Created on first use, so the frontend never has to "create a cart" first.
    """
    if user is not None and user.is_authenticated:
        return Cart.objects.get_or_create(user=user)[0]
    if not session_key:
        raise ValidationError("A guest cart needs a session key.")
    return Cart.objects.get_or_create(session_key=session_key)[0]


def set_quantity(cart, product, quantity):
    """Change a line to an exact quantity (the cart page's + / - buttons). 0 removes it.

    Still never more than the stock; an empty or inactive product can only be removed.
    """
    if quantity < 0:
        raise ValidationError("Quantity cannot be negative.")
    if quantity == 0:
        remove_from_cart(cart, product)
        return None
    if not product.active or product.stock <= 0:
        raise ValidationError("This product is out of stock.")
    item, _ = CartItem.objects.update_or_create(
        cart=cart, product=product, defaults={"quantity": min(quantity, product.stock)}
    )
    return item


def remove_from_cart(cart, product):
    CartItem.objects.filter(cart=cart, product=product).delete()


def clear_cart(cart):
    cart.items.all().delete()


def cart_lines(cart):
    """Lines with their product in one query, for showing the cart (no N+1 queries)."""
    return cart.items.select_related("product", "product__brand").order_by("pk")
