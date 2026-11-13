from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from cart.models import Cart
from cart.services import add_to_cart
from catalog.factories import make_product, make_user
from orders.services import advance_status, place_order

from .models import Rating
from .services import review_comment, submit_comment, submit_rating, visible_comments


def buy(user, product, deliver=True):
    cart = Cart.objects.create(user=user)
    add_to_cart(cart, product)
    order = place_order(user, cart)
    if deliver:
        advance_status(order)
        advance_status(order)
    return order


class ReviewRulesTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product()

    def test_cannot_rate_without_buying(self):
        with self.assertRaises(ValidationError):
            submit_rating(self.user, self.product, 5)

    def test_cannot_rate_before_delivery(self):
        buy(self.user, self.product, deliver=False)
        with self.assertRaises(ValidationError):
            submit_rating(self.user, self.product, 5)

    def test_can_rate_after_delivery_and_it_is_live_at_once(self):
        buy(self.user, self.product)
        self.assertEqual(submit_rating(self.user, self.product, 4).score, 4)

    def test_rating_again_updates_instead_of_duplicating(self):
        buy(self.user, self.product)
        submit_rating(self.user, self.product, 2)
        submit_rating(self.user, self.product, 5)
        self.assertEqual(Rating.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Rating.objects.get().score, 5)

    def test_rating_range_enforced_by_database(self):
        for bad in (0, 6):
            with self.assertRaises(IntegrityError), transaction.atomic():
                Rating.objects.create(user=self.user, product=self.product, score=bad)

    def test_comment_hidden_until_approved(self):
        buy(self.user, self.product)
        comment = submit_comment(self.user, self.product, "Lovely")
        self.assertEqual(visible_comments(self.product).count(), 0)
        review_comment(comment, make_user("product_manager"), approve=True)
        self.assertEqual(visible_comments(self.product).count(), 1)

    def test_disapproved_comment_stays_hidden(self):
        buy(self.user, self.product)
        comment = submit_comment(self.user, self.product, "Meh")
        review_comment(comment, make_user("product_manager"), approve=False)
        self.assertEqual(visible_comments(self.product).count(), 0)

    def test_only_product_manager_can_moderate(self):
        buy(self.user, self.product)
        comment = submit_comment(self.user, self.product, "Hi")
        for role in ("customer", "sales_manager", "support_agent"):
            with self.assertRaises(PermissionDenied):
                review_comment(comment, make_user(role), approve=True)

    def test_empty_comment_rejected(self):
        buy(self.user, self.product)
        with self.assertRaises(ValidationError):
            submit_comment(self.user, self.product, "   ")

    def test_rating_shows_in_product_api_average(self):
        buy(self.user, self.product)
        submit_rating(self.user, self.product, 4)
        data = self.client.get(f"/api/products/{self.product.pk}/").json()
        self.assertEqual(data["rating"], 4.0)


class CommentApiTests(APITestCase):
    def setUp(self):
        self.customer = make_user(name="Ayşe Yılmaz")
        self.product = make_product()
        self.url = f"/api/products/{self.product.pk}/comments/"

    def test_guest_sees_only_approved_comments(self):
        buy(self.customer, self.product)
        approved = submit_comment(self.customer, self.product, "Lovely scent")
        submit_comment(self.customer, self.product, "Still waiting")
        review_comment(approved, make_user("product_manager"), approve=True)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([c["text"] for c in response.data], ["Lovely scent"])

    def test_comment_shows_name_but_not_email(self):
        buy(self.customer, self.product)
        comment = submit_comment(self.customer, self.product, "Nice")
        review_comment(comment, make_user("product_manager"), approve=True)
        data = self.client.get(self.url).data[0]
        self.assertEqual(data["customerName"], "Ayşe Yılmaz")
        self.assertNotIn(self.customer.email, str(data))

    def test_guest_cannot_post_comment(self):
        response = self.client.post(self.url, {"text": "Hi"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_customer_can_comment_after_delivery_and_it_waits_for_approval(self):
        buy(self.customer, self.product)
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.url, {"text": "  Smells great  "}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["text"], "Smells great")
        self.assertFalse(response.data["approved"])
        self.assertEqual(self.client.get(self.url).data, [])

    def test_cannot_comment_before_delivery(self):
        buy(self.customer, self.product, deliver=False)
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.url, {"text": "Too early"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("delivered", response.data["message"])

    def test_empty_comment_rejected(self):
        buy(self.customer, self.product)
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.url, {"text": "   "}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_staff_roles_cannot_post_comments(self):
        for role in ("sales_manager", "product_manager", "support_agent"):
            self.client.force_authenticate(make_user(role))
            response = self.client.post(self.url, {"text": "Hi"}, format="json")
            self.assertEqual(response.status_code, 403)

    def test_unknown_or_inactive_product_returns_404(self):
        self.assertEqual(self.client.get("/api/products/999999/comments/").status_code, 404)
        self.product.active = False
        self.product.save(update_fields=["active"])
        self.assertEqual(self.client.get(self.url).status_code, 404)
