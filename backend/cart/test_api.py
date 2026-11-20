"""HTTP tests for the cart API used by the cart and checkout pages (Scrum 44, 39)."""
from django.urls import reverse
from rest_framework.test import APITestCase

from catalog.factories import make_product, make_user

from .models import Cart


class CartApiTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product(price="750.00", stock=3)
        self.client.force_authenticate(self.user)

    def add(self, product, quantity=1):
        return self.client.post(reverse("cart-items"), {"productId": product.pk, "quantity": quantity}, format="json")

    def test_new_customer_sees_empty_cart(self):
        response = self.client.get(reverse("cart"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"items": [], "itemCount": 0, "total": "0.00"})

    def test_add_item_and_totals(self):
        response = self.add(self.product, 2)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["total"], "1500.00")
        self.assertEqual(response.data["itemCount"], 2)
        line = response.data["items"][0]
        self.assertEqual((line["productId"], line["quantity"], line["lineTotal"]), (self.product.pk, 2, "1500.00"))

    def test_quantity_is_capped_at_stock(self):
        response = self.add(self.product, 10)
        self.assertEqual(response.data["items"][0]["quantity"], 3)

    def test_out_of_stock_product_cannot_be_added(self):
        empty = make_product(stock=0)
        response = self.add(empty)
        self.assertEqual(response.status_code, 400)
        self.assertIn("out of stock", response.data["message"])

    def test_inactive_product_cannot_be_added(self):
        response = self.add(make_product(active=False))
        self.assertEqual(response.status_code, 400)

    def test_unknown_product_is_404(self):
        response = self.client.post(reverse("cart-items"), {"productId": 999999}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_zero_or_negative_quantity_is_rejected(self):
        for qty in (0, -1):
            with self.subTest(qty=qty):
                self.assertEqual(self.add(self.product, qty).status_code, 400)

    def test_set_quantity_and_zero_removes(self):
        self.add(self.product, 1)
        url = reverse("cart-item", args=[self.product.pk])
        self.assertEqual(self.client.patch(url, {"quantity": 2}, format="json").data["itemCount"], 2)
        self.assertEqual(self.client.patch(url, {"quantity": 0}, format="json").data["items"], [])

    def test_remove_and_clear(self):
        other = make_product()
        self.add(self.product)
        self.add(other)
        response = self.client.delete(reverse("cart-item", args=[self.product.pk]))
        self.assertEqual([l["productId"] for l in response.data["items"]], [other.pk])
        self.assertEqual(self.client.delete(reverse("cart")).data["itemCount"], 0)

    def test_merge_guest_cart_after_login(self):
        self.add(self.product, 1)  # already in the account's cart
        sold_out, extra = make_product(stock=0), make_product(price="100.00")
        body = {"items": [
            {"productId": self.product.pk, "quantity": 5},  # 1 + 5 capped at stock 3
            {"productId": extra.pk, "quantity": 2},
            {"productId": sold_out.pk, "quantity": 1},
            {"productId": 999999, "quantity": 1},
        ]}
        response = self.client.post(reverse("cart-merge"), body, format="json")
        self.assertEqual(response.status_code, 200)
        quantities = {l["productId"]: l["quantity"] for l in response.data["items"]}
        self.assertEqual(quantities, {self.product.pk: 3, extra.pk: 2})
        self.assertEqual(sorted(response.data["skipped"]), sorted([sold_out.pk, 999999]))

    def test_each_customer_sees_only_their_cart(self):
        self.add(self.product)
        self.client.force_authenticate(make_user())
        self.assertEqual(self.client.get(reverse("cart")).data["items"], [])
        self.assertEqual(Cart.objects.get(user=self.user).items.count(), 1)

    def test_login_required(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse("cart")).status_code, 401)
