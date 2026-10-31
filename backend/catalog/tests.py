from decimal import Decimal
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from .factories import make_product
from .models import Product
from .selectors import search_products


class ProductModelTests(TestCase):
    def test_discount_sets_new_price_and_keeps_base(self):
        p = make_product(price="1000.00")
        p.apply_discount(25)
        p.refresh_from_db()
        self.assertEqual(p.price, Decimal("750.00"))
        self.assertEqual(p.base_price, Decimal("1000.00"))

    def test_clear_discount_restores_price(self):
        p = make_product(price="800.00")
        p.apply_discount(50)
        p.clear_discount()
        p.refresh_from_db()
        self.assertEqual(p.price, Decimal("800.00"))

    def test_discount_out_of_range_rejected(self):
        with self.assertRaises(ValidationError):
            make_product().apply_discount(120)

    def test_cost_defaults_to_half_of_price(self):
        self.assertEqual(make_product(price="900.00").effective_cost, Decimal("450.00"))

    def test_explicit_cost_wins(self):
        self.assertEqual(make_product(price="900.00", cost=Decimal("300.00")).effective_cost, Decimal("300.00"))

    def test_stock_cannot_go_negative_in_database(self):
        p = make_product(stock=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.filter(pk=p.pk).update(stock=-1)

    def test_serial_number_is_unique(self):
        make_product(serial_number="DUP")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_product(serial_number="DUP")

    def test_negative_price_rejected_in_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_product(price="-1.00")


class SearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rose = make_product(name="Rose Velours", description="Turkish rose and oud", price="500", popularity=10)
        cls.cedar = make_product(name="Cedar Noir", description="Woody leather", price="300", popularity=90, stock=0)
        cls.citrus = make_product(name="Citrus Day", description="Lemon and rose water", price="700", popularity=50)

    def names(self, **kw):
        return [p.name for p in search_products(Product.objects.all(), **kw)]

    def test_search_matches_name(self):
        self.assertEqual(self.names(q="cedar"), ["Cedar Noir"])

    def test_search_matches_description(self):
        self.assertCountEqual(self.names(q="rose"), ["Rose Velours", "Citrus Day"])

    def test_out_of_stock_still_searchable(self):
        self.assertIn("Cedar Noir", self.names(q="cedar"))

    def test_sort_price_ascending_and_descending(self):
        self.assertEqual(self.names(sort="price_asc"), ["Cedar Noir", "Rose Velours", "Citrus Day"])
        self.assertEqual(self.names(sort="price_desc"), ["Citrus Day", "Rose Velours", "Cedar Noir"])

    def test_sort_by_popularity_is_default(self):
        self.assertEqual(self.names(), ["Cedar Noir", "Citrus Day", "Rose Velours"])


class ProductApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_products", stdout=StringIO())

    def test_seed_is_idempotent(self):
        before = Product.objects.count()
        call_command("seed_products", stdout=StringIO())
        self.assertEqual(Product.objects.count(), before)
        self.assertGreaterEqual(before, 25)

    def test_list_is_public_and_has_contract_fields(self):
        data = self.client.get("/api/products/").json()
        first = data[0]
        for key in ("id", "name", "brand", "serialNumber", "stock", "price", "warrantyStatus",
                    "distributor", "volumeMl", "notes", "families"):
            self.assertIn(key, first)
        self.assertEqual(set(first["notes"]), {"top", "heart", "base"})

    def test_filter_by_category_and_sort(self):
        data = self.client.get("/api/products/?category=cologne&sort=price_asc").json()
        self.assertTrue(data)
        self.assertTrue(all(p["category"] == "cologne" for p in data))
        prices = [p["price"] for p in data]
        self.assertEqual(prices, sorted(prices))

    def test_out_of_stock_product_is_listed(self):
        data = self.client.get("/api/products/?q=Baccarat").json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["stock"], 0)
        self.assertFalse(data[0]["inStock"])

    def test_detail_and_categories(self):
        pid = Product.objects.first().pk
        self.assertEqual(self.client.get(f"/api/products/{pid}/").status_code, 200)
        self.assertEqual(self.client.get("/api/products/999999/").status_code, 404)
        self.assertEqual(len(self.client.get("/api/categories/").json()), 4)
