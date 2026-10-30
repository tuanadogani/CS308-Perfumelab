from django.conf import settings
from django.db import models
from django.db.models import Q


class Rating(models.Model):
    """1-5 stars. Visible immediately, no approval needed (req 5)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ratings")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="ratings")
    score = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="one_rating_per_user_product"),
            models.CheckConstraint(condition=Q(score__gte=1, score__lte=5), name="rating_score_1_5"),
        ]


class Comment(models.Model):
    """Hidden until a product manager approves it (req 5, 12)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="comments")
    text = models.TextField()
    approved = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="reviewed_comments",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["product", "approved"])]
        ordering = ["-created_at"]
