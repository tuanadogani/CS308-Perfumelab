from decimal import Decimal
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from catalog.factories import make_product, make_user

from .models import Notification, WishlistItem
from .services import set_discount


class WishlistDiscountTests(TestCase):
    def setUp(self):
        self.fan = make_user()
        self.other = make_user()
        self.manager = make_user("sales_manager")
        self.product = make_product(price="1000.00")
        WishlistItem.objects.create(user=self.fan, product=self.product)

    def test_discount_updates_price_and_notifies_wishlist_owner(self):
        sent = set_discount(self.manager, [self.product], 20)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 800)
        self.assertEqual(sent, 1)
        self.assertEqual(Notification.objects.get().user, self.fan)

    def test_users_without_the_product_are_not_notified(self):
        set_discount(self.manager, [self.product], 20)
        self.assertFalse(Notification.objects.filter(user=self.other).exists())

    def test_removing_discount_sends_no_notification(self):
        set_discount(self.manager, [self.product], 0)
        self.assertEqual(Notification.objects.count(), 0)

    def test_only_sales_manager_can_discount(self):
        with self.assertRaises(PermissionDenied):
            set_discount(make_user("product_manager"), [self.product], 10)

    def test_wishlist_row_is_unique(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            WishlistItem.objects.create(user=self.fan, product=self.product)


class WishlistApiTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user()
        self.product = make_product(stock=0)
        self.url = f"/api/wishlist/{self.product.pk}/"

    def test_endpoints_require_login(self):
        self.assertEqual(self.client.get('/api/wishlist/').status_code, 401)
        self.assertEqual(self.client.put(self.url).status_code, 401)
        self.assertEqual(self.client.delete(self.url).status_code, 401)

    def test_add_list_and_remove_are_persistent_and_idempotent(self):
        self.client.force_authenticate(self.user)
        for _ in range(2):
            self.assertEqual(self.client.put(self.url).status_code, 200)
        self.assertEqual(WishlistItem.objects.filter(user=self.user).count(), 1)
        response = self.client.get('/api/wishlist/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['id'], self.product.pk)
        self.assertIn('notes', response.data[0])
        self.assertIn('volumeMl', response.data[0])
        for _ in range(2):
            self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertEqual(self.client.get('/api/wishlist/').data, [])

    def test_users_cannot_see_or_remove_another_users_favorites(self):
        WishlistItem.objects.create(user=self.other, product=self.product)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get('/api/wishlist/').data, [])
        self.client.delete(self.url)
        self.assertTrue(WishlistItem.objects.filter(user=self.other).exists())

    def test_missing_or_inactive_product_cannot_be_added(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.put('/api/wishlist/999999/').status_code, 404)
        self.product.active = False
        self.product.save()
        self.assertEqual(self.client.put(self.url).status_code, 404)
        self.assertFalse(WishlistItem.objects.filter(user=self.user).exists())


class SalesDiscountApiTests(APITestCase):
    def setUp(self):
        self.sales_manager = make_user("sales_manager")
        self.customer = make_user("customer")
        self.product_manager = make_user("product_manager")
        self.product = make_product(price="1000.00")
        WishlistItem.objects.create(user=self.customer, product=self.product)
        self.url = "/api/sales/discounts/"

    def test_requires_authentication(self):
        response = self.client.post(self.url, {"product_ids": [self.product.id], "discount_rate": 20})
        self.assertEqual(response.status_code, 401)

    def test_forbidden_for_customers(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.url, {"product_ids": [self.product.id], "discount_rate": 20})
        self.assertEqual(response.status_code, 403)

    def test_forbidden_for_product_managers(self):
        self.client.force_authenticate(self.product_manager)
        response = self.client.post(self.url, {"product_ids": [self.product.id], "discount_rate": 20})
        self.assertEqual(response.status_code, 403)

    def test_sales_manager_can_apply_discount_and_notifies_wishlist_users(self):
        self.client.force_authenticate(self.sales_manager)
        response = self.client.post(self.url, {
            "product_ids": [self.product.id],
            "discount_rate": 20,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["notificationsSent"], 1)
        self.assertEqual(response.data["discountRate"], 20.0)

        # Check DB updates
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("800.00"))
        self.assertEqual(self.product.discount_rate, Decimal("20.00"))

        # Check Notification was created for wishlist user
        note = Notification.objects.get(user=self.customer)
        self.assertEqual(note.product, self.product)
        self.assertIn("20", note.message)

    def test_sales_manager_can_clear_discount(self):
        self.product.apply_discount(20)
        self.client.force_authenticate(self.sales_manager)
        response = self.client.post(self.url, {
            "product_ids": [self.product.id],
            "discount_rate": 0,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["notificationsSent"], 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("1000.00"))
        self.assertEqual(self.product.discount_rate, Decimal("0.00"))

    def test_camel_case_parameters_supported(self):
        self.client.force_authenticate(self.sales_manager)
        response = self.client.post(self.url, {
            "productIds": [self.product.id],
            "discountRate": 15,
        })
        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("850.00"))

    def test_validation_invalid_rate(self):
        self.client.force_authenticate(self.sales_manager)
        response = self.client.post(self.url, {
            "product_ids": [self.product.id],
            "discount_rate": 150,
        })
        self.assertEqual(response.status_code, 400)

    def test_validation_empty_products(self):
        self.client.force_authenticate(self.sales_manager)
        response = self.client.post(self.url, {
            "product_ids": [],
            "discount_rate": 10,
        })
        self.assertEqual(response.status_code, 400)


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.user = make_user("customer")
        self.other = make_user("customer")
        self.product = make_product()
        self.notification = Notification.objects.create(
            user=self.user,
            product=self.product,
            message=f"{self.product.name} is on sale!",
        )

    def test_user_can_view_own_notifications(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/notifications/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.notification.id)
        self.assertEqual(response.data[0]["message"], self.notification.message)
        self.assertFalse(response.data[0]["read"])

    def test_user_cannot_view_others_notifications(self):
        self.client.force_authenticate(self.other)
        response = self.client.get("/api/notifications/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_mark_notification_as_read(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(f"/api/notifications/{self.notification.id}/read/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["read"])
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.read)

    def test_mark_all_notifications_as_read(self):
        Notification.objects.create(user=self.user, message="Another alert")
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/notifications/read-all/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Notification.objects.filter(user=self.user, read=False).count(), 0)
