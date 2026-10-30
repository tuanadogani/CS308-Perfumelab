from datetime import timedelta

from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from cart.models import Cart
from cart.services import add_to_cart
from catalog.factories import make_product, make_user
from orders.models import Order, OrderStatus
from orders.services import advance_status, place_order
from wishlist.services import set_discount

from .models import RefundStatus
from .services import decide_refund, request_refund


def delivered_order(user, product, qty=1):
    cart = Cart.objects.create(user=user)
    add_to_cart(cart, product, qty)
    order = place_order(user, cart)
    advance_status(order)
    advance_status(order)
    return order


class RefundTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.sales = make_user("sales_manager")
        self.product = make_product(price="1000.00", stock=5)
        self.order = delivered_order(self.user, self.product, 2)
        self.item = self.order.items.get()

    def test_request_on_delivered_order(self):
        refund = request_refund(self.user, self.item, "Not my scent")
        self.assertEqual(refund.status, RefundStatus.REQUESTED)
        self.assertEqual(refund.amount, 2000)

    def test_not_allowed_before_delivery(self):
        cart, _ = Cart.objects.get_or_create(user=self.user)
        add_to_cart(cart, self.product)
        fresh = place_order(self.user, cart)
        with self.assertRaises(ValidationError):
            request_refund(self.user, fresh.items.get())

    def test_not_allowed_after_30_days(self):
        Order.objects.filter(pk=self.order.pk).update(created_at=timezone.now() - timedelta(days=31))
        self.item.order.refresh_from_db()
        with self.assertRaises(ValidationError):
            request_refund(self.user, self.item)

    def test_allowed_on_day_30(self):
        Order.objects.filter(pk=self.order.pk).update(created_at=timezone.now() - timedelta(days=29))
        self.item.order.refresh_from_db()
        self.assertEqual(request_refund(self.user, self.item).status, RefundStatus.REQUESTED)

    def test_cannot_refund_someone_elses_order(self):
        with self.assertRaises(PermissionDenied):
            request_refund(make_user(), self.item)

    def test_cannot_request_twice(self):
        request_refund(self.user, self.item)
        with self.assertRaises(ValidationError):
            request_refund(self.user, self.item)

    def test_approval_restocks_and_emails_customer(self):
        refund = request_refund(self.user, self.item)
        stock_before = self.product.__class__.objects.get(pk=self.product.pk).stock
        decide_refund(refund, self.sales, approve=True)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, stock_before + 2)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user.email, mail.outbox[0].to)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.REFUNDED)

    def test_rejection_keeps_stock(self):
        refund = request_refund(self.user, self.item)
        stock_before = self.product.__class__.objects.get(pk=self.product.pk).stock
        decide_refund(refund, self.sales, approve=False)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, stock_before)
        self.assertEqual(len(mail.outbox), 0)

    def test_only_sales_manager_decides(self):
        refund = request_refund(self.user, self.item)
        with self.assertRaises(PermissionDenied):
            decide_refund(refund, make_user("product_manager"), approve=True)

    def test_cannot_decide_twice(self):
        refund = request_refund(self.user, self.item)
        decide_refund(refund, self.sales, approve=True)
        with self.assertRaises(ValidationError):
            decide_refund(refund, self.sales, approve=True)


class DiscountedRefundTests(TestCase):
    def test_refund_uses_price_paid_even_after_campaign_ends(self):
        user, sales = make_user(), make_user("sales_manager")
        product = make_product(price="1000.00")
        set_discount(sales, [product], 30)  # campaign running
        order = delivered_order(user, product)
        set_discount(sales, [product], 0)  # campaign over, price back to 1000
        refund = request_refund(user, order.items.get())
        self.assertEqual(refund.amount, 700)
