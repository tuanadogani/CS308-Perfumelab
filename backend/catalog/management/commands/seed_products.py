"""Load the demo catalog from catalog/seed_data.py. Safe to re-run (updates in place)."""
import re
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Brand, Category, NoteFamily, Product, ProductNote
from catalog.seed_data import CATEGORIES, FAMILIES, PERFUMES

DISTRIBUTORS = ["PerfumeLab Distribution A.Ş.", "Istanbul Fragrance Trading Ltd.", "Bosphorus Parfums Import"]


def _code(text):
    return re.sub(r"[^A-Z0-9]", "", text.upper())[:6]


class Command(BaseCommand):
    help = "Seed categories, brands, note families and real demo perfumes."

    @transaction.atomic
    def handle(self, *args, **options):
        categories = {
            slug: Category.objects.update_or_create(slug=slug, defaults={"name": name})[0]
            for slug, name in CATEGORIES
        }
        for name in FAMILIES:
            NoteFamily.objects.get_or_create(name=name)

        for i, row in enumerate(PERFUMES, start=1):
            brand_name, name, cat, gender, volume, top, heart, base, families, price, stock, pop = row
            brand, _ = Brand.objects.get_or_create(name=brand_name)
            price = Decimal(price)
            product, _ = Product.objects.update_or_create(
                serial_number=f"{_code(brand_name)}-{_code(name)}-{volume}-{i:04d}",
                defaults=dict(
                    name=name, brand=brand, category=categories[cat], gender=gender,
                    volume_ml=volume, model=f"{_code(name)}-{volume}",
                    description=(
                        f"{name} by {brand_name}: {', '.join(top[:2])} on top, "
                        f"{', '.join(heart[:2])} at the heart, resting on {', '.join(base[:2])}."
                    ),
                    price=price, base_price=price, discount_rate=0, stock=stock, popularity=pop,
                    warranty_status="Authenticity guaranteed – 2 years",
                    distributor=DISTRIBUTORS[i % len(DISTRIBUTORS)],
                ),
            )
            product.families.set(NoteFamily.objects.filter(name__in=families))
            product.notes.all().delete()
            ProductNote.objects.bulk_create(
                ProductNote(product=product, tier=tier, name=n)
                for tier, notes in (("top", top), ("heart", heart), ("base", base)) for n in notes
            )
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(PERFUMES)} products."))
