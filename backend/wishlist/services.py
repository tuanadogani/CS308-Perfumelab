import logging
from functools import partial

from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import transaction

from accounts.models import Role
from catalog.models import Product

from .models import Notification, WishlistItem

log = logging.getLogger(__name__)


def _send_discount_email(email, message, product_id):
    try:
        sent = send_mail("An item on your wishlist is on sale", message, None, [email])
        if not sent:
            log.warning("Wishlist discount email was not sent for product %s", product_id)
    except Exception:
        log.exception("Wishlist discount email failed for product %s", product_id)


@transaction.atomic
def set_discount(manager, products, rate):
    """Sales manager discounts products; wishlist owners are notified automatically (req 11)."""
    if manager.role != "sales_manager":
        raise PermissionDenied("Only sales managers can set discounts.")
    notes = []
    product_ids = [product.pk for product in products]
    locked_products = Product.objects.select_for_update().filter(pk__in=product_ids).order_by("pk")
    for product in locked_products:
        previous_rate = product.discount_rate
        product.apply_discount(rate)
        if product.discount_rate <= 0:
            continue

        message = f"{product.name} is now {rate}% off: {product.price} TL"
        owners = WishlistItem.objects.filter(product=product).values_list(
            "user_id", "user__role", "user__email",
        )
        for user_id, role, email in owners:
            notes.append(Notification(user_id=user_id, product=product, message=message))
            if previous_rate == 0 and role == Role.CUSTOMER and email:
                transaction.on_commit(
                    partial(_send_discount_email, email, message, product.pk),
                )
    Notification.objects.bulk_create(notes)
    return len(notes)
