"""Two "add to cart" requests for the same product arriving at once (e.g. a double click).

TransactionTestCase + real threads: each thread has its own database connection, like two
web requests. Needs PostgreSQL (the project database); SQLite queues writes so the race never happens.
"""
import threading

from django.db import connection
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from catalog.factories import make_product, make_user

from .models import CartItem


def add_at_the_same_time(user, product, times, quantity=1):
    """POST /api/cart/items/ `times` times in parallel; return the status codes."""
    barrier = threading.Barrier(times)
    codes = []

    def add():
        try:
            client = APIClient()
            client.force_authenticate(user)
            barrier.wait(timeout=10)
            codes.append(client.post("/api/cart/items/", {"productId": product.pk, "quantity": quantity},
                                     format="json").status_code)
        except Exception as exc:  # a crash shows up in the assertion instead of being hidden
            codes.append(type(exc).__name__)
        finally:
            connection.close()

    threads = [threading.Thread(target=add) for _ in range(times)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not any(t.is_alive() for t in threads), "an add-to-cart thread hung (deadlock?)"
    return codes


class ConcurrentAddToCartTests(TransactionTestCase):
    def test_double_click_adds_both_without_error(self):
        user, product = make_user(), make_product(stock=10)
        self.assertEqual(add_at_the_same_time(user, product, 2), [201, 201])
        self.assertEqual(CartItem.objects.get(cart__user=user, product=product).quantity, 2)

    def test_many_parallel_adds_keep_one_line_and_respect_stock(self):
        user, product = make_user(), make_product(stock=5)
        codes = add_at_the_same_time(user, product, 8)
        self.assertEqual(codes, [201] * 8)
        line = CartItem.objects.get(cart__user=user, product=product)
        self.assertEqual(line.quantity, 5)  # 8 clicks, but never more than the stock
