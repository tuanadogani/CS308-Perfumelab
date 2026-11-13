from django.db import models
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    # Requirement 9: Required product properties
    name = models.CharField(max_length=255)
    model = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    stock = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    warranty_status = models.CharField(max_length=100)
    distributor = models.CharField(max_length=255)

    # Additional fields for perfume products
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    brand = models.CharField(max_length=100, blank=True)
    scent_family = models.CharField(max_length=100, blank=True)
    top_notes = models.CharField(max_length=255, blank=True)
    heart_notes = models.CharField(max_length=255, blank=True)
    base_notes = models.CharField(max_length=255, blank=True)
    size_ml = models.IntegerField(null=True, blank=True)
    image_url = models.URLField(blank=True)

    # For sales manager (Requirement 11)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Cost for profit calculation, defaults to 50% of sale price")
    discount_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Discount percentage (0-100)")

    # Popularity tracking for sorting
    popularity_score = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.model})"

    @property
    def discounted_price(self):
        if self.discount_rate > 0:
            return self.price * (1 - self.discount_rate / 100)
        return self.price

    @property
    def effective_cost_price(self):
        """Return cost price or default to 50% of sale price"""
        return self.cost_price if self.cost_price else self.price * 0.5


class Order(models.Model):
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_address = models.TextField()

    # Payment info (hashed/encrypted in production - Requirement 17)
    payment_method = models.CharField(max_length=50)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.customer.email}"


class OrderItem(models.Model):
    """Delivery list item - Requirement 12"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ['order', 'product']

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    @property
    def total_price(self):
        return self.quantity * self.price_at_purchase


class Comment(models.Model):
    """Product comments - Requirement 5"""
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='comments')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, help_text="User must have received the product to comment")

    comment_text = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.customer.email} on {self.product.name}"


class Rating(models.Model):
    """Product ratings - Requirement 5 (submitted directly without approval)"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, help_text="User must have received the product to rate")

    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], help_text="Rating from 1 to 5 stars")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['product', 'customer', 'order']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating} stars by {self.customer.email} for {self.product.name}"
