"""User.tax_id is stored encrypted (accounts/fields.py, req 17)."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import connection
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from accounts.fields import PREFIX, decrypt, encrypt

User = get_user_model()
TAX_ID = "12345678901"


def stored_tax_id(user):
    """What is really in the database column, skipping the field's decryption."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT tax_id FROM accounts_user WHERE id = %s", [user.pk])
        return cursor.fetchone()[0]


def make(email="tax@example.com", tax_id=TAX_ID):
    return User.objects.create_user(email, "TestPassword!2026", tax_id=tax_id)


class TaxIdEncryptionTests(TestCase):
    def test_database_holds_only_ciphertext(self):
        raw = stored_tax_id(make())
        self.assertTrue(raw.startswith(PREFIX))
        self.assertNotIn(TAX_ID, raw)

    def test_python_reads_the_real_value(self):
        user = make()
        self.assertEqual(User.objects.get(pk=user.pk).tax_id, TAX_ID)

    def test_blank_tax_id_stays_blank(self):
        self.assertEqual(stored_tax_id(make(tax_id="")), "")

    def test_same_value_encrypts_differently_each_time(self):
        # Random part in every token: two users with one tax ID can't be matched up in the DB.
        a, b = make("a@example.com"), make("b@example.com")
        self.assertNotEqual(stored_tax_id(a), stored_tax_id(b))

    def test_resaving_does_not_encrypt_twice(self):
        user = make()
        user.name = "Changed"
        user.save()
        self.assertEqual(User.objects.get(pk=user.pk).tax_id, TAX_ID)

    def test_old_plain_text_rows_are_still_readable(self):
        user = make()
        with connection.cursor() as cursor:
            cursor.execute("UPDATE accounts_user SET tax_id = %s WHERE id = %s", ["98765432109", user.pk])
        self.assertEqual(User.objects.get(pk=user.pk).tax_id, "98765432109")

    def test_wrong_key_refuses_to_read(self):
        token = encrypt(TAX_ID)
        with override_settings(SECRET_KEY="a-completely-different-secret-key"):
            with self.assertRaises(ImproperlyConfigured):
                decrypt(token)

    def test_explicit_key_setting_is_used(self):
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        with override_settings(FIELD_ENCRYPTION_KEY=key):
            token = encrypt(TAX_ID)
            self.assertEqual(Fernet(key).decrypt(token[len(PREFIX):].encode()).decode(), TAX_ID)

    def test_max_length_20_still_enforced(self):
        user = User(email="long@example.com", tax_id="1" * 21)
        user.set_password("TestPassword!2026")
        with self.assertRaises(ValidationError):
            user.full_clean()


class TaxIdApiTests(APITestCase):
    def test_register_stores_tax_id_encrypted(self):
        response = self.client.post("/api/auth/register/", {
            "name": "Ada Lovelace", "email": "ada@example.com", "password": "TestPassword!2026",
            "taxId": TAX_ID, "homeAddress": "Orta Mahalle, Tuzla, Istanbul",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        user = User.objects.get(email="ada@example.com")
        self.assertNotIn(TAX_ID, stored_tax_id(user))
        self.assertEqual(user.tax_id, TAX_ID)

    def test_profile_still_shows_tax_id(self):
        user = make()
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get("/api/auth/me/").json()["taxId"], TAX_ID)
