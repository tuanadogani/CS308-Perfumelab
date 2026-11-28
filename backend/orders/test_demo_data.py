"""Delivery backfill migration and the reset_demo_customer command."""
import importlib
from decimal import Decimal
from io import StringIO

from django.apps import apps
from django.core.management import CommandError, call_command
from django.test import TestCase
from rest_framework.test import APIClient

from cart.models import Cart
from cart.services import add_to_cart
from catalog.factories import make_product, make_user
from orders.models import Delivery, Invoice, Order, OrderItem
from orders.services import advance_status, place_order
from payments.models import CreditCard, Payment
from payments.services import checkout
from refunds.models import RefundRequest
from refunds.services import request_refund
from reviews.models import Comment, Rating
from reviews.services import submit_comment, submit_rating

backfill = importlib.import_module("orders.migrations.0004_backfill_deliveries").backfill


def bare_order(user, product, status="processing"):
    """An order inserted without checkout: no Delivery, Invoice or Payment (like old demo data)."""
    order = Order.objects.create(user=user, status=status, shipping_address="Moda, Istanbul", total=Decimal("100"))
    item = OrderItem.objects.create(order=order, product=product, quantity=1, unit_price=Decimal("100"), unit_cost=Decimal("50"))
    return order, item


class DeliveryBackfillTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product(price="100.00")

    def test_creates_missing_delivery_rows(self):
        _, item = bare_order(self.user, self.product)
        backfill(apps, None)
        delivery = Delivery.objects.get(order_item=item)
        self.assertEqual(delivery.delivery_address, "Moda, Istanbul")
        self.assertFalse(delivery.completed)

    def test_marks_delivered_and_refunded_orders_completed(self):
        _, delivered = bare_order(self.user, self.product, "delivered")
        _, refunded = bare_order(self.user, self.product, "refunded")
        _, transit = bare_order(self.user, self.product, "in_transit")
        backfill(apps, None)
        self.assertTrue(Delivery.objects.get(order_item=delivered).completed)
        self.assertTrue(Delivery.objects.get(order_item=refunded).completed)
        self.assertFalse(Delivery.objects.get(order_item=transit).completed)

    def test_keeps_existing_rows_and_is_repeatable(self):
        cart = Cart.objects.create(user=self.user)
        add_to_cart(cart, self.product, 1)
        order = place_order(self.user, cart)
        bare_order(self.user, self.product)
        backfill(apps, None)
        backfill(apps, None)
        self.assertEqual(Delivery.objects.count(), 2)
        self.assertEqual(Delivery.objects.filter(order_item__order=order).count(), 1)

    def test_backfilled_order_shows_up_for_the_product_manager_and_can_advance(self):
        order, _ = bare_order(self.user, self.product)
        backfill(apps, None)
        client = APIClient()
        client.force_authenticate(make_user(role="product_manager"))
        ids = [row["orderId"] for row in client.get("/api/product-manager/deliveries/").json()]
        self.assertIn(order.pk, ids)
        self.assertEqual(client.patch(f"/api/product-manager/orders/{order.pk}/status/", {"status": "in_transit"}, format="json").status_code, 200)
        advance_status(order)
        self.assertTrue(Delivery.objects.get(order_item__order=order).completed)


class ResetDemoCustomerTests(TestCase):
    NUMBER = "4242424242424242"

    def setUp(self):
        self.customer = make_user()
        self.other = make_user()
        self.product = make_product(price="100.00", stock=20)

    def buy(self, user):
        cart, _ = Cart.objects.get_or_create(user=user)
        add_to_cart(cart, self.product, 1)
        card = CreditCard.from_number(user, self.NUMBER, "Test", 12, 2030)
        return checkout(user, cart, card, self.NUMBER, shipping_address="Istanbul")

    def run_reset(self, email):
        out = StringIO()
        call_command("reset_demo_customer", email=email, stdout=out)
        return out.getvalue()

    def test_removes_orders_reviews_refunds_and_cart(self):
        order = self.buy(self.customer)
        advance_status(order)
        advance_status(order)
        item = order.items.get()
        request_refund(self.customer, item)
        submit_rating(self.customer, self.product, 5)
        submit_comment(self.customer, self.product, "Lovely")
        bare_order(self.customer, self.product)
        cart = Cart.objects.get(user=self.customer)
        add_to_cart(cart, self.product, 2)

        output = self.run_reset(self.customer.email)

        self.assertIn("2 orders", output)
        self.assertFalse(Order.objects.filter(user=self.customer).exists())
        self.assertFalse(OrderItem.objects.filter(order__user=self.customer).exists())
        self.assertFalse(Invoice.objects.exists())
        self.assertFalse(Payment.objects.exists())
        self.assertFalse(RefundRequest.objects.exists())
        self.assertFalse(Rating.objects.filter(user=self.customer).exists())
        self.assertFalse(Comment.objects.filter(user=self.customer).exists())
        self.assertFalse(cart.items.exists())
        self.assertTrue(self.customer.cards.exists())  # account and saved card stay

    def test_leaves_other_customers_alone(self):
        self.buy(self.customer)
        theirs = self.buy(self.other)
        self.run_reset(self.customer.email)
        self.assertTrue(Order.objects.filter(pk=theirs.pk).exists())
        self.assertTrue(Payment.objects.filter(order=theirs).exists())

    def test_refuses_staff_and_unknown_accounts(self):
        manager = make_user(role="product_manager")
        with self.assertRaises(CommandError):
            self.run_reset(manager.email)
        with self.assertRaises(CommandError):
            self.run_reset("nobody@example.com")

    def test_customer_can_review_again_only_after_a_new_delivery(self):
        order = self.buy(self.customer)
        advance_status(order)
        advance_status(order)
        self.run_reset(self.customer.email)
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            submit_rating(self.customer, self.product, 4)
