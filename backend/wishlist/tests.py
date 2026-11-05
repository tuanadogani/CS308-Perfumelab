from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.test import TestCase

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


from rest_framework.test import APITestCase


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
