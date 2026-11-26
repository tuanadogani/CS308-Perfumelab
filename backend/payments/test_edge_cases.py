"""Checkout service regressions; HTTP checkout is not implemented yet."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import connection, connections, transaction
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from cart.models import Cart
from cart.services import add_to_cart
from catalog.factories import make_product, make_user
from catalog.models import Product
from orders.models import Delivery, Invoice, Order, OrderItem
from payments.bank import PaymentDeclined
from payments.models import CreditCard, Payment
from payments.services import checkout


NUMBER = "4242 4242 4242 4242"


class CheckoutEdgeCaseTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product(stock=3)
        self.cart = Cart.objects.create(user=self.user)
        add_to_cart(self.cart, self.product, 2)
        self.card = CreditCard.from_number(self.user, NUMBER, "Customer", 12, 2030)

    def assert_rejected_without_changes(self, exception, message, **kwargs):
        stock = Product.objects.get(pk=self.product.pk).stock
        lines = list(self.cart.items.values_list("product_id", "quantity"))
        with patch("payments.services.bank.charge", return_value="TXN-UNEXPECTED") as charge:
            with self.assertRaisesRegex(exception, message):
                checkout(self.user, self.cart, self.card, NUMBER, **kwargs)
            charge.assert_not_called()
        for model in (Order, OrderItem, Delivery, Invoice, Payment):
            self.assertFalse(model.objects.exists(), model.__name__)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, stock)
        self.assertEqual(list(self.cart.items.values_list("product_id", "quantity")), lines)

    def test_empty_cart_does_not_charge_or_create_order(self):
        self.cart.items.all().delete()
        self.assert_rejected_without_changes(ValidationError, "empty")

    def test_stock_exhausted_after_adding_to_cart(self):
        Product.objects.filter(pk=self.product.pk).update(stock=0)
        self.assert_rejected_without_changes(ValidationError, "stock")

    def test_stock_reduced_below_requested_quantity(self):
        Product.objects.filter(pk=self.product.pk).update(stock=1)
        self.assert_rejected_without_changes(ValidationError, "stock")

    def test_product_deactivated_after_adding_to_cart(self):
        Product.objects.filter(pk=self.product.pk).update(active=False)
        self.assert_rejected_without_changes(ValidationError, "stock")

    def test_missing_or_whitespace_profile_address(self):
        for address in ("", " \n\t "):
            with self.subTest(address=address):
                self.user.home_address = address
                self.assert_rejected_without_changes(ValidationError, "address")

    def test_explicit_blank_shipping_address_is_not_replaced_by_profile(self):
        for address in ("", " \n\t "):
            with self.subTest(address=address):
                self.assert_rejected_without_changes(
                    ValidationError, "address", shipping_address=address
                )

    def test_profile_address_is_used_when_no_override_is_supplied(self):
        order = checkout(self.user, self.cart, self.card, NUMBER)
        self.assertEqual(order.shipping_address, self.user.home_address)

    def test_other_customers_cart_cannot_be_checked_out(self):
        other = make_user()
        self.cart.user = other
        self.cart.save(update_fields=["user"])
        self.assert_rejected_without_changes(ValidationError, "cart")

    def test_bank_connection_failure_rolls_back_all_checkout_writes(self):
        with patch("payments.services.bank.charge", side_effect=ConnectionError("bank unavailable")):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                with self.assertRaises(ConnectionError):
                    checkout(self.user, self.cart, self.card, NUMBER)
        self.assertEqual(callbacks, [])
        for model in (Order, OrderItem, Delivery, Invoice, Payment):
            self.assertFalse(model.objects.exists(), model.__name__)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(self.cart.items.get().quantity, 2)

    def test_expired_saved_card_is_rejected_before_charge(self):
        CreditCard.objects.filter(pk=self.card.pk).update(expiry_year=2000)
        self.card.refresh_from_db()
        self.assert_rejected_without_changes(PaymentDeclined, "expired")

    def test_invalid_card_input_is_not_silently_normalized(self):
        for value in (None, 4242424242424242, "letters4242424242424242", "４２４２４２４２４２４２４２４２"):
            with self.subTest(value=value), patch("payments.services.bank.charge") as charge:
                with self.assertRaises(PaymentDeclined):
                    checkout(self.user, self.cart, self.card, value)
                charge.assert_not_called()
        self.assertFalse(Order.objects.exists())

    def test_missing_card_rejected_without_creating_order(self):
        with self.assertRaises(PaymentDeclined):
            checkout(self.user, self.cart, None, NUMBER)
        self.assertFalse(Order.objects.exists())


class CardInputEdgeCaseTests(TestCase):
    def test_invalid_fields_do_not_save_card(self):
        user = make_user()
        valid = dict(number=NUMBER, holder_name="Customer", expiry_month=12, expiry_year=2030)
        for changes in (
            {"number": None}, {"number": "abcd4242424242424242"},
            {"number": "1234"}, {"number": "4" * 20},
            {"holder_name": "  "}, {"expiry_month": 0}, {"expiry_month": 13},
            {"expiry_month": "12"}, {"expiry_year": 2000}, {"expiry_year": None},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    CreditCard.from_number(user, **(valid | changes))
                self.assertFalse(CreditCard.objects.exists())

    def test_card_is_valid_through_end_of_expiry_month(self):
        from django.utils import timezone
        today = timezone.localdate()
        card = CreditCard.from_number(make_user(), NUMBER, "Customer", today.month, today.year)
        self.assertTrue(card.matches(NUMBER))


@skipUnlessDBFeature("has_select_for_update")
class ConcurrentCheckoutTests(TransactionTestCase):
    """Use separate PostgreSQL connections and the complete payment transaction."""

    def race(self, same_cart=False):
        product = make_product(stock=2 if same_cart else 1)
        users = [make_user(), make_user()]
        carts, cards = [], []
        for user in users:
            cart = Cart.objects.create(user=user)
            add_to_cart(cart, product)
            carts.append(cart)
            cards.append(CreditCard.from_number(user, NUMBER, "Customer", 12, 2030))
        if same_cart:
            users[1], carts[1], cards[1] = users[0], carts[0], cards[0]
        barrier = Barrier(2, timeout=10)

        def buy(index):
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("SET LOCAL statement_timeout = '15s'")
                    barrier.wait()
                    try:
                        order = checkout(users[index], carts[index], cards[index], NUMBER)
                        return ("ok", order.pk)
                    except ValidationError as exc:
                        return ("rejected", " ".join(exc.messages))
            finally:
                connections.close_all()

        with patch("payments.services._send_invoice"):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(buy, i) for i in range(2)]
                results = [future.result(timeout=25) for future in futures]
        self.assertEqual(sorted(result[0] for result in results), ["ok", "rejected"])
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Invoice.objects.count(), 1)
        product.refresh_from_db()
        self.assertEqual(product.stock, 1 if same_cart else 0)
        if not same_cart:
            loser = next(i for i, result in enumerate(results) if result[0] == "rejected")
            self.assertIn("stock", results[loser][1])
            self.assertEqual(carts[loser].items.get().quantity, 1)

    def test_two_customers_buying_last_item_only_one_is_charged(self):
        self.race()

    def test_duplicate_concurrent_checkout_of_same_cart_creates_one_order(self):
        self.race(same_cart=True)
