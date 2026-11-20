"""The customer's own invoice on screen and as PDF (Scrum 44, 39)."""
from django.urls import reverse
from rest_framework.test import APITestCase

from cart.models import Cart
from cart.services import add_to_cart
from catalog.factories import make_product, make_user
from orders.services import place_order


class CustomerInvoiceApiTests(APITestCase):
    def setUp(self):
        self.user = make_user(name="Ada Lovelace")
        self.product = make_product(price="1250.00", stock=4)
        cart = Cart.objects.create(user=self.user)
        add_to_cart(cart, self.product, 2)
        self.order = place_order(self.user, cart)
        self.client.force_authenticate(self.user)

    def test_invoice_data_for_the_screen(self):
        response = self.client.get(reverse("customer-invoice", args=[self.order.pk]))
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data["number"], self.order.invoice.number)
        self.assertEqual(data["total"], "2500.00")
        self.assertEqual(data["customerName"], "Ada Lovelace")
        self.assertEqual(data["items"][0]["quantity"], 2)
        self.assertTrue(data["pdfUrl"].endswith(f"/api/orders/{self.order.pk}/invoice/pdf/"))

    def test_invoice_pdf(self):
        response = self.client.get(reverse("customer-invoice-pdf", args=[self.order.pk]) + "?download=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn("attachment", response["Content-Disposition"])

    def test_other_customer_gets_404(self):
        self.client.force_authenticate(make_user())
        for name in ("customer-invoice", "customer-invoice-pdf"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name, args=[self.order.pk])).status_code, 404)

    def test_login_required(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse("customer-invoice", args=[self.order.pk])).status_code, 401)
