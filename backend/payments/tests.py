from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

User = get_user_model()


class CreditCardTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("card@example.com", "TestPassword!2026")

    def make(self, number="4111 1111 1111 1111"):
        from payments.models import CreditCard
        return CreditCard.from_number(self.user, number, "Card Holder", 12, 2030, brand="Visa")

    def test_full_number_is_never_stored(self):
        card = self.make()
        self.assertNotIn("4111111111111111", card.number_hash)
        self.assertEqual(card.last4, "1111")
        self.assertTrue(card.number_hash.startswith(("pbkdf2_", "argon2", "bcrypt")))

    def test_matches_checks_hash(self):
        card = self.make()
        self.assertTrue(card.matches("4111-1111-1111-1111"))
        self.assertFalse(card.matches("4111111111111112"))

    def test_short_number_rejected(self):
        with self.assertRaises(ValueError):
            self.make("1234")

    def test_expiry_month_constraint(self):
        from payments.models import CreditCard
        with self.assertRaises(IntegrityError), transaction.atomic():
            CreditCard.objects.create(
                user=self.user, number_hash="x", last4="1111", holder_name="A",
                expiry_month=13, expiry_year=2030,
            )


class CheckoutPaymentTests(TestCase):
    NUMBER = "4242 4242 4242 4242"

    def setUp(self):
        from catalog.factories import make_product, make_user
        from cart.models import Cart
        from cart.services import add_to_cart
        from payments.models import CreditCard
        self.user = make_user()
        self.product = make_product(price="1000.00", stock=5)
        self.cart = Cart.objects.create(user=self.user)
        add_to_cart(self.cart, self.product, 2)
        self.card = CreditCard.from_number(self.user, self.NUMBER, "Card Holder", 12, 2030, brand="Visa")

    def pay(self, **kw):
        from payments.services import checkout
        return checkout(self.user, self.cart, kw.pop("card", self.card), kw.pop("number", self.NUMBER), **kw)

    def test_successful_checkout_records_payment_and_stock(self):
        order = self.pay()
        self.assertEqual(order.payment.amount, 2000)
        self.assertTrue(order.payment.transaction_id.startswith("TXN-"))
        self.assertEqual(order.card_last4, "4242")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    def test_declined_card_keeps_nothing(self):
        from payments.bank import PaymentDeclined
        from orders.models import Order
        from payments.models import CreditCard, Payment
        bad = CreditCard.from_number(self.user, "4000 0000 0000 0002", "Card Holder", 12, 2030)
        with self.assertRaises(PaymentDeclined):
            self.pay(card=bad, number="4000 0000 0000 0002")
        self.assertEqual((Order.objects.count(), Payment.objects.count()), (0, 0))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(self.cart.items.count(), 1)

    def test_wrong_number_for_saved_card_rejected(self):
        from payments.bank import PaymentDeclined
        with self.assertRaises(PaymentDeclined):
            self.pay(number="4242 4242 4242 4243")

    def test_cannot_pay_with_someone_elses_card(self):
        from catalog.factories import make_user
        from payments.bank import PaymentDeclined
        from payments.models import CreditCard
        theirs = CreditCard.from_number(make_user(), self.NUMBER, "Other", 12, 2030)
        with self.assertRaises(PaymentDeclined):
            self.pay(card=theirs)

    def test_invoice_email_has_pdf_attached_after_commit(self):
        from django.core import mail
        with self.captureOnCommitCallbacks(execute=True):
            order = self.pay()
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [self.user.email])
        name, content, mimetype = message.attachments[0]
        self.assertEqual(name, f"{order.invoice.number}.pdf")
        self.assertEqual(mimetype, "application/pdf")
        self.assertTrue(content.startswith(b"%PDF"))

    def test_stored_hash_matches_rerendered_pdf(self):
        import hashlib
        from orders.invoices import render_invoice_pdf
        with self.captureOnCommitCallbacks(execute=True):
            order = self.pay()
        order.invoice.refresh_from_db()
        self.assertEqual(order.invoice.pdf_sha256, hashlib.sha256(render_invoice_pdf(order.invoice)).hexdigest())

    def test_email_failure_does_not_undo_the_order(self):
        from unittest import mock
        with mock.patch("payments.services.seal_and_email", side_effect=RuntimeError("smtp down")):
            with self.captureOnCommitCallbacks(execute=True):
                order = self.pay()
        self.assertEqual(order.payment.amount, 2000)

    def test_no_email_when_payment_fails(self):
        from django.core import mail
        from payments.bank import PaymentDeclined
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(PaymentDeclined):
                self.pay(number="4242 4242 4242 4243")
        self.assertEqual(len(mail.outbox), 0)
