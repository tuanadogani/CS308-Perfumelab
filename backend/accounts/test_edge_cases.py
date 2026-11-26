from datetime import timedelta

from django.core.cache import cache
import jwt
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from catalog.factories import make_user


class JwtEdgeCaseTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()

    def setUp(self):
        cache.clear()

    def test_malformed_wrong_signature_and_wrong_token_type_rejected(self):
        forged = jwt.encode(dict(AccessToken.for_user(self.user).payload),
                            "untrusted-test-signing-key-which-is-long-enough", algorithm="HS256")
        tokens = ("not-a-jwt", "a.b.c", forged, str(RefreshToken.for_user(self.user)))
        for token in tokens:
            with self.subTest(token=token):
                self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
                for url in ("/api/auth/me/", "/api/orders/", "/api/wishlist/"):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 401, url)
                    self.assertIn("application/json", response["Content-Type"])

    def test_expired_access_can_be_replaced_using_valid_refresh(self):
        expired = AccessToken.for_user(self.user)
        expired.set_exp(lifetime=timedelta(seconds=-1))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired}")
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)
        refresh = RefreshToken.for_user(self.user)
        response = self.client.post("/api/auth/refresh/", {"refresh": str(refresh)}, format="json")
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(self.client.get("/api/auth/me/").data["id"], self.user.pk)

    def test_expired_refresh_requires_new_login(self):
        refresh = RefreshToken.for_user(self.user)
        refresh.set_exp(lifetime=timedelta(seconds=-1))
        response = self.client.post("/api/auth/refresh/", {"refresh": str(refresh)}, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("access", response.data)

    def test_sql_injection_cannot_bypass_login(self):
        response = self.client.post("/api/auth/login/", {
            "email": "' OR 1=1 --", "password": "' OR 1=1 --",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("access", response.data)
