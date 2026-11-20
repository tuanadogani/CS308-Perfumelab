"""HTTP tests for POST /api/checkout/ and GET /api/cards/ (Scrum 41, 39)."""
from django.core import mail
from django.urls import reverse
from rest_framework.test import APITestCase

from cart.models import Cart
from cart.services import add_to_cart
from catalog.factories import make_product, make_user
from orders.models import Invoice, Order
from payments.models import CreditCard, Payment

GOOD = "4242 4242 4242 4242"
DECLINED = "4000 0000 0000 0002"  # the mock bank declines cards ending in 0002


def card_body(number=GOOD, **extra):
    body = {"cardNumber": number, "holderName": "Ada Lovelace", "expiryMonth": 12,
            "expiryYear": 2030, "cvv": "123"}
    body.update(extra)
    return body


class CheckoutApiTests(APITestCase):
    url = reverse("checkout")

    def setUp(self):
        self.user = make_user(name="Ada Lovelace")
        self.product = make_product(price="1000.00", stock=5)
        self.cart = Cart.objects.create(user=self.user)
        add_to_cart(self.cart, self.product, 2)
        self.client.force_authenticate(self.user)

    def test_successful_checkout_returns_order_and_invoice(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url, card_body(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["order"]["total"], "2000.00")
        self.assertTrue(response.data["invoice"]["number"].startswith("INV-"))
        self.assertEqual(response.data["cardLast4"], "4242")
        self.assertTrue(response.data["transactionId"].startswith("TXN-"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertFalse(self.cart.items.exists())
        self.assertEqual(len(mail.outbox), 1)  # invoice emailed (req 4)

    def test_card_number_and_cvv_are_never_stored_or_returned(self):
        response = self.client.post(self.url, card_body(), format="json")
        text = response.content.decode()
        self.assertNotIn("4242424242424242", text)
        self.assertNotIn("cvv", text)
        card = CreditCard.objects.get(user=self.user)
        self.assertNotIn("4242424242424242", card.number_hash)

    def test_same_card_twice_is_saved_once(self):
        self.client.post(self.url, card_body(), format="json")
        add_to_cart(self.cart, self.product, 1)
        response = self.client.post(self.url, card_body(number="4242-4242-4242-4242"), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(CreditCard.objects.filter(user=self.user).count(), 1)

    def test_declined_card_keeps_everything_as_before(self):
        response = self.client.post(self.url, card_body(DECLINED), format="json")
        self.assertEqual(response.status_code, 402)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertFalse(CreditCard.objects.exists())  # a declined card is not saved
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(self.cart.items.get().quantity, 2)

    def test_retry_after_decline_gets_the_next_invoice_number(self):
        self.client.post(self.url, card_body(DECLINED), format="json")
        first = self.client.post(self.url, card_body(), format="json").data["invoice"]["number"]
        add_to_cart(self.cart, self.product, 1)
        second = self.client.post(self.url, card_body(), format="json").data["invoice"]["number"]
        self.assertEqual(int(second[4:]), int(first[4:]) + 1)  # no gap after the decline

    def test_empty_cart_is_rejected(self):
        self.cart.items.all().delete()
        response = self.client.post(self.url, card_body(), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("empty", response.data["message"])

    def test_product_sold_out_after_adding_to_cart(self):
        self.product.stock = 1  # someone else bought the rest meanwhile
        self.product.save()
        response = self.client.post(self.url, card_body(), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Not enough stock", response.data["message"])
        self.assertEqual(self.cart.items.get().quantity, 2)
        self.assertEqual(Order.objects.count(), 0)

    def test_product_removed_from_sale_after_adding_to_cart(self):
        self.product.active = False
        self.product.save()
        response = self.client.post(self.url, card_body(), format="json")
        self.assertEqual(response.status_code, 400)

    def test_custom_shipping_address_is_used(self):
        response = self.client.post(self.url, card_body(shippingAddress="Kadikoy, Istanbul"), format="json")
        self.assertEqual(response.data["order"]["shippingAddress"], "Kadikoy, Istanbul")

    def test_missing_address_is_rejected(self):
        self.user.home_address = ""
        self.user.save()
        response = self.client.post(self.url, card_body(), format="json")
        self.assertEqual(response.status_code, 400)

    def test_invalid_card_input_is_rejected(self):
        bad = [
            card_body(number="1234"),
            card_body(number="4242abcd42424242"),
            card_body(cvv="12"),
            card_body(expiryMonth=13),
            card_body(expiryYear=2020),  # expired
        ]
        for body in bad:
            with self.subTest(body=body):
                self.assertEqual(self.client.post(self.url, body, format="json").status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_login_required(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(self.url, card_body(), format="json").status_code, 401)

    def test_staff_cannot_checkout(self):
        self.client.force_authenticate(make_user(role="sales_manager"))
        self.assertEqual(self.client.post(self.url, card_body(), format="json").status_code, 403)


class SavedCardApiTests(APITestCase):
    def test_lists_only_own_cards_without_number(self):
        user, other = make_user(), make_user()
        CreditCard.from_number(user, GOOD, "Ada", 12, 2030, brand="Visa")
        CreditCard.from_number(other, "5555 5555 5555 4444", "Bob", 1, 2031)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("saved-cards"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([c["last4"] for c in response.data], ["4242"])
        self.assertNotIn("number_hash", response.data[0])
