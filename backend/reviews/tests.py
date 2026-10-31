from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

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
