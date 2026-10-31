from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class ProfileAndRoleTests(APITestCase):
    def test_new_users_default_to_customer(self):
        user = User.objects.create_user("new@example.com", "TestPassword!2026")
        self.assertEqual(user.role, "customer")

    def test_role_values_match_frontend_constants(self):
        from accounts.models import Role
        self.assertEqual(
            sorted(Role.values),
            ["customer", "product_manager", "sales_manager", "support_agent"],
        )

    def test_invalid_role_rejected_by_validation(self):
        from django.core.exceptions import ValidationError
        user = User(email="bad@example.com", role="root")
        with self.assertRaises(ValidationError):
            user.full_clean(exclude=["password"])
