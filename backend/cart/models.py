from django.conf import settings
from django.db import models
from django.db.models import Q


class Cart(models.Model):
    """A logged-in user's cart, or an anonymous cart identified by a session key (req 4)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="cart"
    )
    session_key = models.CharField(max_length=64, null=True, blank=True, unique=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # exactly one owner: a user XOR a guest session
            models.CheckConstraint(
                condition=(Q(user__isnull=False, session_key__isnull=True)
                           | Q(user__isnull=True, session_key__isnull=False)),
                name="cart_has_exactly_one_owner",
            ),
        ]

    @property
    def total(self):
        return sum(item.product.price * item.quantity for item in self.items.select_related("product"))


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="one_line_per_product_in_cart"),
            models.CheckConstraint(condition=Q(quantity__gte=1), name="cart_item_quantity_gte_1"),
        ]
