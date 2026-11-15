"""A model field that stores its value encrypted (req 17: sensitive data protected).

Used for User.tax_id. In Python the value looks normal ("12345678901"), but the
database only ever holds "enc:" + a Fernet token (AES encryption + a signature),
so someone who reads the database or a backup cannot see the tax ID.

Why encryption and not hashing (like passwords)? A hash can't be turned back,
but we still need the real tax ID for the profile page and invoices. Encryption
can be reversed, but only with the key.

The key comes from FIELD_ENCRYPTION_KEY in .env. If that is not set, a key is
derived from DJANGO_SECRET_KEY, so every teammate's setup keeps working. Either
way: if the key changes, old values can no longer be read.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

PREFIX = "enc:"  # marks encrypted values, so old plain-text rows can still be recognised


def _fernet():
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", "")
    if not key:
        # Fernet needs 32 random-looking bytes; SHA-256 of the secret key gives exactly that.
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


def encrypt(value):
    if not value:
        return value  # keep blank tax IDs blank; nothing to hide
    return PREFIX + _fernet().encrypt(value.encode()).decode()


def decrypt(stored):
    if not stored or not stored.startswith(PREFIX):
        return stored  # blank, or a plain value saved before encryption existed
    try:
        return _fernet().decrypt(stored[len(PREFIX):].encode()).decode()
    except InvalidToken:
        raise ImproperlyConfigured(
            "Cannot decrypt a stored value: FIELD_ENCRYPTION_KEY / DJANGO_SECRET_KEY changed."
        )


class EncryptedTextField(models.TextField):
    """Text that is encrypted on the way into the database and decrypted on the way out.

    Encrypting the same value twice gives different results (Fernet adds a random
    part), so this field cannot be searched or used in filters - only read.
    """

    def from_db_value(self, value, expression, connection):
        return decrypt(value)

    def to_python(self, value):
        return decrypt(value) if isinstance(value, str) else value

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt(decrypt(value)) if isinstance(value, str) else value
