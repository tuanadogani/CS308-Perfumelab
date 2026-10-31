"""Tiny helpers shared by the test suites of every app."""
from decimal import Decimal
from itertools import count

from django.contrib.auth import get_user_model

from .models import Brand, Category, Product

_n = count(1)


def make_user(role="customer", **extra):
    n = next(_n)
    extra.setdefault("home_address", "Tuzla, Istanbul")
    return get_user_model().objects.create_user(f"user{n}@example.com", "TestPassword!2026", role=role, **extra)


def make_product(price="1000.00", stock=10, **extra):
    n = next(_n)
    brand, _ = Brand.objects.get_or_create(name=extra.pop("brand", "Test Brand"))
    category, _ = Category.objects.get_or_create(slug="eau-de-parfum", defaults={"name": "Eau de Parfum"})
    defaults = dict(
        name=f"Perfume {n}", model=f"M{n}", serial_number=f"SN-{n}", description="A test scent.",
        price=Decimal(price), base_price=Decimal(price), stock=stock, warranty_status="2 years",
        distributor="Test Distributor", brand=brand, category=category, volume_ml=100,
    )
    defaults.update(extra)
    return Product.objects.create(**defaults)
