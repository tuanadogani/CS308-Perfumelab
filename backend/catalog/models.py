from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

TWO_PLACES = Decimal("0.01")
DEFAULT_COST_RATIO = Decimal("0.50")  # req 11: cost defaults to 50% of the sale price


class Category(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class NoteFamily(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Gender(models.TextChoices):
    WOMEN = "Women", "Women"
    MEN = "Men", "Men"
    UNISEX = "Unisex", "Unisex"


class Product(models.Model):
    # Req 9 mandatory fields: id, name, model, serial number, description,
    # quantity in stock, price, warranty status, distributor.
    name = models.CharField(max_length=200)
    model = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    stock = models.PositiveIntegerField(default=0)  # PositiveIntegerField => CHECK (stock >= 0)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # current selling price
    base_price = models.DecimalField(max_digits=10, decimal_places=2)  # price before any discount
    discount_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # percent
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    warranty_status = models.CharField(max_length=200)
    distributor = models.CharField(max_length=200)

    # Perfume specific
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.UNISEX)
    volume_ml = models.PositiveIntegerField()
    families = models.ManyToManyField(NoteFamily, blank=True, related_name="products")
    popularity = models.PositiveIntegerField(default=0)  # bumped on every purchase
    active = models.BooleanField(default=True)  # soft delete; orders keep referencing the row
    # File name inside catalog/product_images/ (blank = frontend draws a bottle instead).
    image = models.CharField(max_length=200, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["price"]),
            models.Index(fields=["-popularity"]),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name="product_price_gte_0"),
            models.CheckConstraint(condition=Q(base_price__gte=0), name="product_base_price_gte_0"),
            models.CheckConstraint(
                condition=Q(discount_rate__gte=0, discount_rate__lte=100),
                name="product_discount_0_100",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.base_price is None:
            self.base_price = self.price
        super().save(*args, **kwargs)

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def effective_cost(self):
        if self.cost is not None:
            return self.cost
        return (self.price * DEFAULT_COST_RATIO).quantize(TWO_PLACES, ROUND_HALF_UP)

    def apply_discount(self, rate):
        """Sales manager sets a discount; the new price is computed automatically (req 11)."""
        rate = Decimal(str(rate))
        if not Decimal("0") <= rate <= Decimal("100"):
            raise ValidationError("Discount rate must be between 0 and 100.")
        self.discount_rate = rate
        self.price = (self.base_price * (Decimal("100") - rate) / Decimal("100")).quantize(
            TWO_PLACES, ROUND_HALF_UP
        )
        self.save(update_fields=["discount_rate", "price"])

    def clear_discount(self):
        self.apply_discount(0)

    def __str__(self):
        return f"{self.name} ({self.volume_ml} ml)"


class NoteTier(models.TextChoices):
    TOP = "top", "Top"
    HEART = "heart", "Heart"
    BASE = "base", "Base"


class ProductNote(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="notes")
    tier = models.CharField(max_length=5, choices=NoteTier.choices)
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product", "tier", "name"], name="unique_product_note"),
        ]

    def __str__(self):
        return f"{self.tier}: {self.name}"
