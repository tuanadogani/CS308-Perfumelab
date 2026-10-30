from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from orders.models import OrderItem, OrderStatus

from .models import Comment, Rating


def has_received(user, product):
    """Products must be delivered before they can be rated or commented on (req 5)."""
    return OrderItem.objects.filter(
        order__user=user, product=product,
        order__status__in=[OrderStatus.DELIVERED],
    ).exists()


def submit_rating(user, product, score):
    if not has_received(user, product):
        raise ValidationError("You can only rate products that were delivered to you.")
    rating, _ = Rating.objects.update_or_create(user=user, product=product, defaults={"score": score})
    return rating


def submit_comment(user, product, text):
    if not has_received(user, product):
        raise ValidationError("You can only comment on products that were delivered to you.")
    if not text.strip():
        raise ValidationError("Comment cannot be empty.")
    return Comment.objects.create(user=user, product=product, text=text.strip())


def review_comment(comment, manager, approve):
    if manager.role != "product_manager":
        raise PermissionDenied("Only product managers can moderate comments.")
    comment.approved = approve
    comment.reviewed_by = manager
    comment.reviewed_at = timezone.now()
    comment.save(update_fields=["approved", "reviewed_by", "reviewed_at"])
    return comment


def visible_comments(product):
    return Comment.objects.filter(product=product, approved=True)
