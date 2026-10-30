from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

User = get_user_model()


class SeedDemoUsersTests(TestCase):
    def run_seed(self):
        call_command("seed_demo_users", stdout=StringIO())

    def test_creates_one_user_per_role(self):
        self.run_seed()
        roles = set(User.objects.filter(email__endswith="@demo.com").values_list("role", flat=True))
        self.assertEqual(roles, {"customer", "sales_manager", "product_manager", "support_agent"})

    def test_password_works_and_is_hashed(self):
        self.run_seed()
        user = User.objects.get(email="sales@demo.com")
        self.assertTrue(user.check_password("Demo1234"))
        self.assertNotEqual(user.password, "Demo1234")

    def test_is_idempotent(self):
        self.run_seed()
        self.run_seed()
        self.assertEqual(User.objects.filter(email__endswith="@demo.com").count(), 4)
        self.assertEqual(User.objects.get(email="customer@demo.com").cards.count(), 1)

    def test_customer_has_address_for_checkout(self):
        self.run_seed()
        self.assertTrue(User.objects.get(email="customer@demo.com").home_address)
