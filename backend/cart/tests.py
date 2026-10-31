from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from catalog.factories import make_product, make_user

from .models import Cart
from .services import add_to_cart, merge_guest_cart


class CartTests(TestCase):
    def test_add_item(self):
        cart = Cart.objects.create(user=make_user())
        item = add_to_cart(cart, make_product(stock=5), 2)
        self.assertEqual(item.quantity, 2)

    def test_out_of_stock_cannot_be_added(self):
        cart = Cart.objects.create(user=make_user())
        with self.assertRaises(ValidationError):
            add_to_cart(cart, make_product(stock=0))

    def test_quantity_is_capped_at_stock(self):
        cart = Cart.objects.create(user=make_user())
        product = make_product(stock=3)
        add_to_cart(cart, product, 2)
        self.assertEqual(add_to_cart(cart, product, 5).quantity, 3)

    def test_cart_needs_exactly_one_owner(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cart.objects.create()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cart.objects.create(user=make_user(), session_key="abc")

    def test_guest_cart_is_kept_after_login(self):
        product = make_product(stock=10)
        guest = Cart.objects.create(session_key="guest-1")
        add_to_cart(guest, product, 2)
        user_cart = merge_guest_cart(guest, make_user())
        self.assertEqual(user_cart.items.get().quantity, 2)
        self.assertFalse(Cart.objects.filter(session_key="guest-1").exists())

    def test_merge_sums_quantities_with_existing_user_cart(self):
        product = make_product(stock=10)
        user = make_user()
        add_to_cart(Cart.objects.create(user=user), product, 3)
        guest = Cart.objects.create(session_key="guest-2")
        add_to_cart(guest, product, 4)
        self.assertEqual(merge_guest_cart(guest, user).items.get().quantity, 7)

    def test_cart_total(self):
        cart = Cart.objects.create(user=make_user())
        add_to_cart(cart, make_product(price="100.00"), 2)
        add_to_cart(cart, make_product(price="50.00"), 1)
        self.assertEqual(cart.total, 250)
