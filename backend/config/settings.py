import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise ImproperlyConfigured(".env dosyasında DJANGO_SECRET_KEY tanımlayın.")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [host.strip() for host in os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"
).split(",") if host.strip()]

INSTALLED_APPS = [
    "accounts",
    "catalog",
    "cart",
    "orders",
    "reviews",
    "wishlist",
    "refunds",
    "payments",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "perfume"),
        "USER": os.environ.get("POSTGRES_USER", "perfume_app"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        # Supabase needs SSL: set POSTGRES_SSLMODE=require (local Postgres: leave it as prefer).
        "OPTIONS": {"connect_timeout": 5, "sslmode": os.environ.get("POSTGRES_SSLMODE", "prefer")},
        "CONN_MAX_AGE": int(os.environ.get("POSTGRES_CONN_MAX_AGE", "0")),
        # Supabase's transaction pooler (port 6543) cannot keep server-side cursors open.
        "DISABLE_SERVER_SIDE_CURSORS": os.environ.get("POSTGRES_PORT", "5432") == "6543",
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "tr-tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173"
).split(",") if origin.strip()]
# The guest cart id travels in this header (see cart/views.py); browsers need it allowed.
from corsheaders.defaults import default_headers  # noqa: E402
CORS_ALLOW_HEADERS = (*default_headers, "x-cart-key")

# Key for encrypted fields such as User.tax_id (blank = derived from DJANGO_SECRET_KEY).
FIELD_ENCRYPTION_KEY = os.environ.get("FIELD_ENCRYPTION_KEY", "")

# Email (invoice PDFs, refund notices). Default prints emails in the runserver console.
# For real delivery set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend plus the
# EMAIL_HOST* values (Gmail: smtp.gmail.com, port 587, TLS, a Google "app password").
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "10"))
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "PerfumeLab <no-reply@perfumelab.local>")
