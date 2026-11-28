"""Wipe a customer's shopping history so a demo can start from scratch.

    python manage.py reset_demo_customer                    # customer@demo.com
    python manage.py reset_demo_customer --email ada@x.com

Removes the customer's orders (with their lines, deliveries, invoices, payments and
refunds), ratings, comments, cart and notifications. The account, saved cards and
wishlist are kept. Stock is NOT put back; run `python manage.py seed_products` afterwards
to reset the catalog's stock and prices.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Role
from cart.models import CartItem
from orders.models import Invoice, Order
from payments.models import Payment, PaymentRefund
from refunds.models import RefundRequest
from reviews.models import Comment, Rating
from wishlist.models import Notification


class Command(BaseCommand):
    help = "Delete a customer's orders, reviews, cart and notifications (for demo rehearsals)."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="customer@demo.com")

    @transaction.atomic
    def handle(self, email, **options):
        user = get_user_model().objects.filter(email=email).first()
        if user is None:
            raise CommandError(f"No user with email {email}.")
        if user.role != Role.CUSTOMER:
            raise CommandError(f"{email} is not a customer; refusing to touch staff accounts.")

        orders = Order.objects.filter(user=user)
        # Protected relations first, children before parents.
        PaymentRefund.objects.filter(payment__order__in=orders).delete()
        RefundRequest.objects.filter(order_item__order__in=orders).delete()
        Payment.objects.filter(order__in=orders).delete()
        Invoice.objects.filter(order__in=orders).delete()
        counts = {
            "orders": orders.count(),
            "ratings": Rating.objects.filter(user=user).delete()[0],
            "comments": Comment.objects.filter(user=user).delete()[0],
            "cart lines": CartItem.objects.filter(cart__user=user).delete()[0],
            "notifications": Notification.objects.filter(user=user).delete()[0],
        }
        orders.delete()  # order lines and deliveries cascade
        summary = ", ".join(f"{n} {label}" for label, n in counts.items())
        self.stdout.write(self.style.SUCCESS(f"Reset {email}: removed {summary}."))
