from django.conf import settings
from django.db import models
from django.db.models import Q


class OrderStatus(models.TextChoices):
    PROCESSING = "processing", "Processing"
    IN_TRANSIT = "in_transit", "In transit"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"
    REFUNDED = "refunded", "Refunded"


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=12, choices=OrderStatus.choices, default=OrderStatus.PROCESSING)
    shipping_address = models.TextField()  # snapshot: later profile edits must not change old orders
    total = models.DecimalField(max_digits=12, decimal_places=2)
    card_last4 = models.CharField(max_length=4, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["user", "-created_at"])]
        constraints = [models.CheckConstraint(condition=Q(total__gte=0), name="order_total_gte_0")]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField()
    # Price paid at purchase time. Refunds use THIS, not the current price (req 16).
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)  # for profit/loss (req 11)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(quantity__gte=1), name="order_item_quantity_gte_1")]

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class Delivery(models.Model):
    """One row per order line: the product manager's delivery list (req 12)."""

    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name="delivery")
    delivery_address = models.TextField()
    completed = models.BooleanField(default=False)

    @property
    def customer_id(self):
        return self.order_item.order.user_id

    @property
    def product_id(self):
        return self.order_item.product_id

    @property
    def quantity(self):
        return self.order_item.quantity

    @property
    def total_price(self):
        return self.order_item.line_total


class Invoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="invoice")
    number = models.CharField(max_length=20, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    pdf_sha256 = models.CharField(max_length=64, blank=True)  # integrity hash of the emailed PDF (req 17)
