"""Checkouts running at the same moment (req 18 concurrency, Scrum 39).

TransactionTestCase + real threads: each thread has its own database connection, so the
row locks in place_order are really exercised (a normal TestCase would share one).
"""
import threading

from django.db import connection
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient

from cart.models import Cart
from cart.services import add_to_cart
from catalog.factories import make_product, make_user
from orders.models import Invoice, Order
from payments.models import Payment

CARD = {"cardNumber": "4242424242424242", "holderName": "Buyer", "expiryMonth": 12,
        "expiryYear": 2030, "cvv": "123"}


def run_together(*users):
    """POST /api/checkout/ for every user at the same instant; return the status codes."""
    barrier = threading.Barrier(len(users))
    codes = []

    def buy(user):
        try:
            client = APIClient()
            client.force_authenticate(user)
            barrier.wait(timeout=10)
            codes.append(client.post(reverse("checkout"), CARD, format="json").status_code)
        except Exception as exc:  # surface crashes in the assertion instead of hiding them
            codes.append(type(exc).__name__)
        finally:
            connection.close()

    threads = [threading.Thread(target=buy, args=(u,)) for u in users]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not any(t.is_alive() for t in threads), "a checkout thread hung (deadlock?)"
    return sorted(codes, key=str)


def cart_with(user, product, quantity):
    cart, _ = Cart.objects.get_or_create(user=user)
    add_to_cart(cart, product, quantity)
    return cart


class ConcurrentCheckoutTests(TransactionTestCase):
    def test_two_customers_race_for_the_last_bottle(self):
        last = make_product(stock=1)
        ada, bob = make_user(), make_user()
        cart_with(ada, last, 1)
        cart_with(bob, last, 1)
        self.assertEqual(run_together(ada, bob), [201, 400])
        last.refresh_from_db()
        self.assertEqual(last.stock, 0)  # never negative, never oversold
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)

    def test_stock_is_split_correctly_between_parallel_buyers(self):
        product = make_product(stock=5)
        buyers = [make_user() for _ in range(3)]
        for user in buyers:
            cart_with(user, product, 2)  # 3 x 2 = 6 wanted, only 5 in stock
        self.assertEqual(run_together(*buyers), [201, 201, 400])
        product.refresh_from_db()
        self.assertEqual(product.stock, 1)

    def test_parallel_orders_get_unique_gapless_invoice_numbers(self):
        buyers = [make_user() for _ in range(4)]
        for user in buyers:
            cart_with(user, make_product(stock=3), 1)  # different products: no stock conflict
        self.assertEqual(run_together(*buyers), [201] * 4)
        numbers = sorted(int(n[4:]) for n in Invoice.objects.values_list("number", flat=True))
        self.assertEqual(numbers, list(range(numbers[0], numbers[0] + 4)))

    def test_double_click_on_pay_creates_one_order(self):
        product = make_product(stock=10)
        ada = make_user()
        cart_with(ada, product, 2)
        self.assertEqual(run_together(ada, ada), [201, 400])  # second one finds the cart empty
        product.refresh_from_db()
        self.assertEqual(product.stock, 8)
        self.assertEqual(Order.objects.filter(user=ada).count(), 1)
        self.assertEqual(Payment.objects.count(), 1)
