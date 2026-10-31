import threading

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase, TransactionTestCase

from cart.models import Cart
from cart.services import add_to_cart
from catalog.factories import make_product, make_user

from .models import Delivery, Order, OrderStatus
from .services import advance_status, cancel_order, place_order


def cart_with(user, product, qty=1):
    cart, _ = Cart.objects.get_or_create(user=user)
    add_to_cart(cart, product, qty)
    return cart


class CheckoutTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product(price="1000.00", stock=5, popularity=0)

    def test_stock_decreases_and_popularity_grows(self):
        place_order(self.user, cart_with(self.user, self.product, 2))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.product.popularity, 2)

    def test_order_snapshots_price_and_total(self):
        order = place_order(self.user, cart_with(self.user, self.product, 2))
        self.product.apply_discount(50)  # later price change must not touch the old order
        item = order.items.get()
        self.assertEqual(item.unit_price, 1000)
        self.assertEqual(order.total, 2000)
        self.assertEqual(item.unit_cost, 500)

    def test_creates_invoice_delivery_and_clears_cart(self):
        cart = cart_with(self.user, self.product)
        order = place_order(self.user, cart)
        self.assertTrue(order.invoice.number.startswith("INV-"))
        self.assertFalse(Delivery.objects.get(order_item__order=order).completed)
        self.assertEqual(cart.items.count(), 0)
        self.assertEqual(order.status, OrderStatus.PROCESSING)

    def test_empty_cart_rejected(self):
        with self.assertRaises(ValidationError):
            place_order(self.user, Cart.objects.create(user=self.user))

    def test_missing_address_rejected(self):
        user = make_user(home_address="")
        with self.assertRaises(ValidationError):
            place_order(user, cart_with(user, self.product))

    def test_insufficient_stock_rolls_everything_back(self):
        cart = cart_with(self.user, self.product, 3)
        self.product.__class__.objects.filter(pk=self.product.pk).update(stock=1)
        with self.assertRaises(ValidationError):
            place_order(self.user, cart)
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)


class LifecycleTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product(stock=5)
        self.order = place_order(self.user, cart_with(self.user, self.product, 2))

    def test_cancel_processing_order_restocks(self):
        cancel_order(self.order)
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.CANCELLED)
        self.assertEqual(self.product.stock, 5)

    def test_cannot_cancel_after_shipping(self):
        advance_status(self.order)
        with self.assertRaises(ValidationError):
            cancel_order(self.order)

    def test_cannot_cancel_twice(self):
        cancel_order(self.order)
        with self.assertRaises(ValidationError):
            cancel_order(self.order)

    def test_status_moves_processing_to_delivered(self):
        self.assertEqual(advance_status(self.order).status, OrderStatus.IN_TRANSIT)
        delivered = advance_status(self.order)
        self.assertEqual(delivered.status, OrderStatus.DELIVERED)
        self.assertIsNotNone(delivered.delivered_at)
        self.assertTrue(Delivery.objects.get(order_item__order=delivered).completed)

    def test_cannot_advance_past_delivered(self):
        advance_status(self.order)
        advance_status(self.order)
        with self.assertRaises(ValidationError):
            advance_status(self.order)

    def test_delivery_list_properties(self):
        d = Delivery.objects.get(order_item__order=self.order)
        self.assertEqual((d.customer_id, d.product_id, d.quantity), (self.user.pk, self.product.pk, 2))
        self.assertEqual(d.total_price, self.order.total)


class ConcurrencyTests(TransactionTestCase):
    """Req 18: two customers racing for the last bottle - exactly one may win."""

    def test_last_bottle_sold_only_once(self):
        product = make_product(stock=1)
        users = [make_user() for _ in range(4)]
        carts = [cart_with(u, product) for u in users]
        results, barrier = [], threading.Barrier(len(users))

        def buy(user, cart):
            try:
                barrier.wait()
                place_order(user, cart)
                results.append("ok")
            except ValidationError:
                results.append("rejected")
            finally:
                connection.close()

        threads = [threading.Thread(target=buy, args=(u, c)) for u, c in zip(users, carts)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        product.refresh_from_db()
        self.assertEqual(results.count("ok"), 1)
        self.assertEqual(product.stock, 0)
        self.assertEqual(Order.objects.count(), 1)
