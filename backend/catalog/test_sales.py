from decimal import Decimal

from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase

from catalog.factories import make_product, make_user
from catalog.models import Product

BASE = "/api/sales/products/"


class SalesPricingApiTests(APITestCase):
    def setUp(self):
        self.manager = make_user("sales_manager")
        self.product = make_product(price="1000.00")
        self.client.force_authenticate(self.manager)

    def price_url(self, product=None):
        return f"{BASE}{(product or self.product).pk}/price/"

    def test_sales_manager_sets_price(self):
        response = self.client.patch(self.price_url(), {"price": "1250.50"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.base_price, Decimal("1250.50"))
        self.assertEqual(self.product.price, Decimal("1250.50"))
        self.assertEqual(response.data["price"], 1250.5)

    def test_new_price_keeps_active_discount(self):
        self.product.apply_discount(20)
        self.client.patch(self.price_url(), {"price": "2000.00"}, format="json")
        self.product.refresh_from_db()
        self.assertEqual(self.product.base_price, Decimal("2000.00"))
        self.assertEqual(self.product.price, Decimal("1600.00"))

    def test_unpriced_products_are_listed_until_priced(self):
        new = make_product(price="0.00")
        ids = [p["id"] for p in self.client.get(BASE + "?unpriced=true").data]
        self.assertEqual(ids, [new.pk])
        self.client.patch(self.price_url(new), {"price": "500.00"}, format="json")
        self.assertEqual(self.client.get(BASE + "?unpriced=true").data, [])

    def test_inactive_product_can_be_priced(self):
        hidden = make_product(price="0.00", active=False)
        self.assertEqual(self.client.patch(self.price_url(hidden), {"price": "99.90"}, format="json").status_code, 200)
        self.assertIn(hidden.pk, [p["id"] for p in self.client.get(BASE).data])

    def test_invalid_prices_rejected(self):
        for bad in ("0", "-5", "abc", "12345678901"):
            response = self.client.patch(self.price_url(), {"price": bad}, format="json")
            self.assertEqual(response.status_code, 400, bad)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("1000.00"))

    def test_unknown_product_returns_404(self):
        self.assertEqual(self.client.patch(f"{BASE}999999/price/", {"price": "10"}, format="json").status_code, 404)

    def test_other_roles_cannot_set_prices(self):
        for role in ("customer", "product_manager", "support_agent"):
            self.client.force_authenticate(make_user(role))
            self.assertEqual(self.client.get(BASE).status_code, 403)
            self.assertEqual(self.client.patch(self.price_url(), {"price": "1"}, format="json").status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.patch(self.price_url(), {"price": "1"}, format="json").status_code, 401)

    def test_new_price_shows_in_public_catalog(self):
        self.client.patch(self.price_url(), {"price": "777.00"}, format="json")
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f"/api/products/{self.product.pk}/").data["price"], 777.0)

    def test_model_rejects_non_positive_price(self):
        with self.assertRaises(ValidationError):
            self.product.set_base_price(0)
        self.assertEqual(Product.objects.get(pk=self.product.pk).price, Decimal("1000.00"))
