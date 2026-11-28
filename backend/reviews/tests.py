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

    def test_xss_payload_is_plain_json_text_and_stays_hidden_until_approval(self):
        from .models import Comment
        payload = '<script>alert("xss")</script><img src=x onerror=alert(1)>'
        buy(self.customer, self.product)
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.url, {"text": payload}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["text"], payload)
        self.assertEqual(self.client.get(self.url).data, [])
        review_comment(Comment.objects.get(pk=response.data["id"]), make_user("product_manager"), True)
        self.client.force_authenticate(user=None)
        public = self.client.get(self.url)
        self.assertIn("application/json", public["Content-Type"])
        self.assertEqual(public.data[0]["text"], payload)
        # JSON text is escaped at the HTML rendering boundary by React, not stored
        # HTML-escaped (which would double-escape legitimate customer text).

    def test_oversized_comment_rejected_without_creating_record(self):
        from .models import Comment
        buy(self.customer, self.product)
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.url, {"text": "x" * 2001}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Comment.objects.exists())

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


class RatingApiTests(APITestCase):
    def setUp(self):
        self.customer = make_user()
        self.product = make_product()
        self.url = f"/api/products/{self.product.pk}/rating/"

    def test_guest_cannot_rate(self):
        self.assertEqual(self.client.put(self.url, {"score": 5}, format="json").status_code, 401)

    def test_customer_can_rate_after_delivery(self):
        buy(self.customer, self.product)
        self.client.force_authenticate(self.customer)
        response = self.client.put(self.url, {"score": 4}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"score": 4})
        self.assertEqual(Rating.objects.get(user=self.customer, product=self.product).score, 4)

    def test_cannot_rate_before_delivery(self):
        buy(self.customer, self.product, deliver=False)
        self.client.force_authenticate(self.customer)
        response = self.client.put(self.url, {"score": 5}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Rating.objects.exists())

    def test_score_must_be_between_1_and_5(self):
        buy(self.customer, self.product)
        self.client.force_authenticate(self.customer)
        for bad in (0, 6, "abc"):
            response = self.client.put(self.url, {"score": bad}, format="json")
            self.assertEqual(response.status_code, 400)
        self.assertFalse(Rating.objects.exists())

    def test_rating_again_updates_existing_rating(self):
        buy(self.customer, self.product)
        self.client.force_authenticate(self.customer)
        self.client.put(self.url, {"score": 2}, format="json")
        self.client.put(self.url, {"score": 5}, format="json")
        self.assertEqual(Rating.objects.filter(user=self.customer).count(), 1)
        self.assertEqual(self.client.get(self.url).data["score"], 5)

    def test_get_returns_null_when_not_rated(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get(self.url).data["score"], None)

    def test_can_review_is_false_without_an_order(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get(self.url).data,
                         {"score": None, "canReview": False, "pendingComments": []})

    def test_can_review_is_false_while_the_order_is_on_its_way(self):
        buy(self.customer, self.product, deliver=False)
        self.client.force_authenticate(self.customer)
        self.assertFalse(self.client.get(self.url).data["canReview"])

    def test_can_review_is_true_after_delivery(self):
        buy(self.customer, self.product)
        self.client.force_authenticate(self.customer)
        self.assertTrue(self.client.get(self.url).data["canReview"])

    def test_can_review_only_for_the_delivered_product(self):
        buy(self.customer, make_product())
        self.client.force_authenticate(self.customer)
        self.assertFalse(self.client.get(self.url).data["canReview"])

    def test_pending_comments_count_until_moderated(self):
        buy(self.customer, self.product)
        first = submit_comment(self.customer, self.product, "Lovely")
        submit_comment(self.customer, self.product, "Still lovely")
        self.client.force_authenticate(self.customer)
        pending = self.client.get(self.url).data["pendingComments"]
        self.assertEqual(sorted(c["text"] for c in pending), ["Lovely", "Still lovely"])
        review_comment(first, make_user("product_manager"), approve=False)
        self.assertEqual([c["text"] for c in self.client.get(self.url).data["pendingComments"]], ["Still lovely"])

    def test_rating_without_comment_is_accepted(self):
        buy(self.customer, self.product)
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.put(self.url, {"score": 5}, format="json").status_code, 200)
        from .models import Comment
        self.assertFalse(Comment.objects.exists())

    def test_staff_cannot_read_review_eligibility(self):
        self.client.force_authenticate(make_user("product_manager"))
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_product_reports_rating_count(self):
        other = make_user()
        for user, score in ((self.customer, 4), (other, 2)):
            buy(user, self.product)
            submit_rating(user, self.product, score)
        data = self.client.get(f"/api/products/{self.product.pk}/").data
        self.assertEqual(data["rating"], 3.0)
        self.assertEqual(data["ratingCount"], 2)

    def test_unrated_product_has_zero_count(self):
        data = self.client.get(f"/api/products/{self.product.pk}/").data
        self.assertIsNone(data["rating"])
        self.assertEqual(data["ratingCount"], 0)

    def test_rating_is_live_in_product_average(self):
        buy(self.customer, self.product)
        self.client.force_authenticate(self.customer)
        self.client.put(self.url, {"score": 3}, format="json")
        self.assertEqual(self.client.get(f"/api/products/{self.product.pk}/").data["rating"], 3.0)

    def test_staff_roles_cannot_rate(self):
        for role in ("sales_manager", "product_manager", "support_agent"):
            self.client.force_authenticate(make_user(role))
            self.assertEqual(self.client.put(self.url, {"score": 5}, format="json").status_code, 403)


class OwnCommentEditTests(APITestCase):
    """Req 5: the author may edit a comment only while it waits for approval."""

    def setUp(self):
        self.customer = make_user()
        self.product = make_product()
        buy(self.customer, self.product)
        self.comment = submit_comment(self.customer, self.product, "First try")
        self.url = f"/api/comments/{self.comment.pk}/"

    def patch(self, text, user=None):
        self.client.force_authenticate(user or self.customer)
        return self.client.patch(self.url, {"text": text}, format="json")

    def test_author_can_edit_a_pending_comment(self):
        response = self.patch("  Better wording  ")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["text"], "Better wording")
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.text, "Better wording")
        self.assertIsNone(self.comment.reviewed_at)  # still waits for the manager

    def test_approved_comment_cannot_be_edited(self):
        review_comment(self.comment, make_user("product_manager"), approve=True)
        self.assertEqual(self.patch("Sneaky change").status_code, 400)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.text, "First try")

    def test_rejected_comment_cannot_be_edited(self):
        review_comment(self.comment, make_user("product_manager"), approve=False)
        self.assertEqual(self.patch("Try again").status_code, 400)

    def test_someone_elses_comment_is_not_found(self):
        self.assertEqual(self.patch("Hijack", user=make_user()).status_code, 404)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.text, "First try")

    def test_empty_text_is_rejected(self):
        self.assertEqual(self.patch("   ").status_code, 400)

    def test_guest_and_staff_cannot_edit(self):
        self.assertEqual(self.client.patch(self.url, {"text": "x"}, format="json").status_code, 401)
        self.assertEqual(self.patch("x", user=make_user("product_manager")).status_code, 403)

    def test_customer_can_post_several_comments(self):
        submit_comment(self.customer, self.product, "Second thought")
        self.client.force_authenticate(self.customer)
        response = self.client.post(f"/api/products/{self.product.pk}/comments/", {"text": "Third"}, format="json")
        self.assertEqual(response.status_code, 201)
        from .models import Comment
        self.assertEqual(Comment.objects.filter(user=self.customer).count(), 3)


class CommentAuthorRatingTests(APITestCase):
    def setUp(self):
        self.product = make_product()
        self.manager = make_user("product_manager")
        self.url = f"/api/products/{self.product.pk}/comments/"

    def approved_comment(self, user, text):
        buy(user, self.product)
        review_comment(submit_comment(user, self.product, text), self.manager, approve=True)

    def test_each_comment_shows_its_authors_rating(self):
        rater, silent = make_user(name="Rater"), make_user(name="Silent")
        self.approved_comment(rater, "Five stars")
        submit_rating(rater, self.product, 5)
        self.approved_comment(silent, "No stars given")
        ratings = {c["text"]: c["rating"] for c in self.client.get(self.url).data}
        self.assertEqual(ratings, {"Five stars": 5, "No stars given": None})

    def test_changed_rating_is_reflected(self):
        user = make_user()
        self.approved_comment(user, "Changed my mind")
        submit_rating(user, self.product, 2)
        submit_rating(user, self.product, 4)
        self.assertEqual(self.client.get(self.url).data[0]["rating"], 4)

    def test_rating_on_another_product_is_not_used(self):
        user = make_user()
        other = make_product()
        self.approved_comment(user, "Only this one")  # buys self.product
        buy(make_user(), other)
        Rating.objects.create(user=user, product=other, score=1)
        self.assertIsNone(self.client.get(self.url).data[0]["rating"])
