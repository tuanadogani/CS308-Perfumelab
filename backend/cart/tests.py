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


class CartEditTests(TestCase):
    """Changing, removing and emptying cart lines, plus finding the right cart."""

    def setUp(self):
        from .services import get_cart
        self.user = make_user()
        self.cart = get_cart(user=self.user)

    def test_get_cart_creates_once_per_user(self):
        from .services import get_cart
        self.assertEqual(get_cart(user=self.user).pk, self.cart.pk)
        self.assertEqual(Cart.objects.filter(user=self.user).count(), 1)

    def test_get_cart_for_guest_uses_session_key(self):
        from django.contrib.auth.models import AnonymousUser
        from .services import get_cart
        guest = get_cart(user=AnonymousUser(), session_key="abc123")
        self.assertEqual(guest.session_key, "abc123")
        self.assertEqual(get_cart(session_key="abc123").pk, guest.pk)

    def test_guest_without_session_key_is_rejected(self):
        from .services import get_cart
        with self.assertRaises(ValidationError):
            get_cart()

    def test_set_quantity_changes_line(self):
        from .services import set_quantity
        p = make_product(stock=5)
        add_to_cart(self.cart, p, 1)
        self.assertEqual(set_quantity(self.cart, p, 4).quantity, 4)

    def test_set_quantity_capped_at_stock(self):
        from .services import set_quantity
        p = make_product(stock=3)
        self.assertEqual(set_quantity(self.cart, p, 10).quantity, 3)

    def test_set_quantity_zero_removes_line(self):
        from .services import set_quantity
        p = make_product(stock=3)
        add_to_cart(self.cart, p, 2)
        self.assertIsNone(set_quantity(self.cart, p, 0))
        self.assertFalse(self.cart.items.exists())

    def test_set_quantity_rejects_negative_and_sold_out(self):
        from .services import set_quantity
        with self.assertRaises(ValidationError):
            set_quantity(self.cart, make_product(stock=3), -1)
        with self.assertRaises(ValidationError):
            set_quantity(self.cart, make_product(stock=0), 1)

    def test_remove_and_clear(self):
        from .services import clear_cart, remove_from_cart
        a, b = make_product(), make_product()
        add_to_cart(self.cart, a)
        add_to_cart(self.cart, b)
        remove_from_cart(self.cart, a)
        self.assertEqual(list(self.cart.items.values_list("product_id", flat=True)), [b.pk])
        clear_cart(self.cart)
        self.assertFalse(self.cart.items.exists())

    def test_cart_lines_loads_products_in_one_query(self):
        from .services import cart_lines
        for _ in range(3):
            add_to_cart(self.cart, make_product())
        with self.assertNumQueries(1):
            names = [line.product.brand.name for line in cart_lines(self.cart)]
        self.assertEqual(len(names), 3)
