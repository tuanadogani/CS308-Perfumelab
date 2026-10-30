from django.core.exceptions import PermissionDenied
from django.db import transaction

from .models import Notification, WishlistItem


@transaction.atomic
def set_discount(manager, products, rate):
    """Sales manager discounts products; wishlist owners are notified automatically (req 11)."""
    if manager.role != "sales_manager":
        raise PermissionDenied("Only sales managers can set discounts.")
    notes = []
    for product in products:
        product.apply_discount(rate)
        if float(rate) > 0:
            for user_id in WishlistItem.objects.filter(product=product).values_list("user_id", flat=True):
                notes.append(Notification(
                    user_id=user_id, product=product,
                    message=f"{product.name} is now {rate}% off: {product.price} TL",
                ))
    Notification.objects.bulk_create(notes)
    return len(notes)
