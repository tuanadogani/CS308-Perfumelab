from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class LoginTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("Customer@Example.com", "TestPassword!2026")

    def setUp(self):
        cache.clear()

    def login(self, **overrides):
        data = {"email": "customer@example.com", "password": "TestPassword!2026"}
        data.update(overrides)
        return self.client.post("/api/auth/login/", data, format="json")

    def test_login_and_profile(self):
        response = self.login(email="CUSTOMER@EXAMPLE.COM")
        self.assertEqual(response.status_code, 200)
        self.assertIn("refresh", response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        profile = self.client.get("/api/auth/me/")
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.data["email"], "customer@example.com")
        self.assertNotIn("password", profile.data)
        self.assertNotEqual(self.user.password, "TestPassword!2026")
        self.assertTrue(self.user.check_password("TestPassword!2026"))

    def test_bad_credentials_have_same_response(self):
        wrong = self.login(password="wrong")
        missing = self.login(email="missing@example.com")
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(wrong.data, missing.data)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.login().status_code, 401)

    def test_required_fields_and_email_validation(self):
        self.assertEqual(self.client.post("/api/auth/login/", {}, format="json").status_code, 400)
        self.assertEqual(self.login(email="invalid").status_code, 400)

    def test_profile_requires_valid_access_token(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)
        token = AccessToken.for_user(self.user)
        token.set_exp(lifetime=timedelta(seconds=-1))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_refresh_rotation_rejects_reuse(self):
        refresh = self.login().data["refresh"]
        response = self.client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertNotEqual(response.data["refresh"], refresh)
        reused = self.client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(reused.status_code, 401)
        invalid = self.client.post("/api/auth/refresh/", {"refresh": "invalid"}, format="json")
        self.assertEqual(invalid.status_code, 401)

    def test_duplicate_email_is_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("CUSTOMER@example.com", "AnotherPassword!2026")

    def test_login_is_throttled(self):
        for _ in range(10):
            self.assertEqual(self.login(email="invalid").status_code, 400)
        self.assertEqual(self.login().status_code, 429)


class RegistrationTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.payload = {"name": "New Customer", "email": "NEW@example.com",
                        "password": "TestPassword!2026", "taxId": "12345678901",
                        "homeAddress": "Kadikoy, Istanbul", "role": "product_manager"}

    def test_register_profile_and_logout(self):
        response = self.client.post("/api/auth/register/", self.payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["user"]["role"], "customer")
        self.assertNotIn("password", response.data["user"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        profile = self.client.get("/api/auth/me/").data
        self.assertEqual(profile["name"], self.payload["name"])
        self.assertEqual(profile["taxId"], self.payload["taxId"])
        self.assertEqual(profile["homeAddress"], self.payload["homeAddress"])
        logout = self.client.post("/api/auth/logout/", {"refresh": response.data["refresh"]}, format="json")
        self.assertEqual(logout.status_code, 204)
        self.client.credentials()
        refreshed = self.client.post("/api/auth/refresh/", {"refresh": response.data["refresh"]}, format="json")
        self.assertEqual(refreshed.status_code, 401)

    def test_duplicate_email_and_weak_password(self):
        User.objects.create_user("new@example.com", "TestPassword!2026")
        self.assertEqual(self.client.post("/api/auth/register/", self.payload, format="json").status_code, 400)
        self.payload.update(email="other@example.com", password="123")
        self.assertEqual(self.client.post("/api/auth/register/", self.payload, format="json").status_code, 400)
