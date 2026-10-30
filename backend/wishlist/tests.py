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
