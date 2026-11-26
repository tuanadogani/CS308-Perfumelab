from rest_framework.test import APITestCase

from .factories import make_product
from .models import Product


class SearchInjectionTests(APITestCase):
    def test_sql_payloads_are_literal_search_text_and_do_not_modify_data(self):
        first = make_product(name="Rose")
        second = make_product(name="Cedar")
        for payload in ("' OR 1=1 --", "'; DROP TABLE catalog_product; --", "%'; SELECT pg_sleep(5); --"):
            with self.subTest(payload=payload):
                response = self.client.get("/api/products/", {"q": payload})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, [])
                self.assertEqual(set(Product.objects.values_list("pk", flat=True)), {first.pk, second.pk})
        # Apostrophes remain legitimate searchable data; no destructive sanitization.
        literal = make_product(name="L'Occitane")
        response = self.client.get("/api/products/", {"q": "L'Occitane"})
        self.assertEqual([row["id"] for row in response.data], [literal.pk])
