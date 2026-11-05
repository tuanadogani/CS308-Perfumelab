"""Point every product at its photo in catalog/product_images/.

    python manage.py link_product_images

Run it after adding new photo files, or on a fresh database. Safe to re-run.
"""
from django.core.management.base import BaseCommand

from catalog.images import link_images
from catalog.models import Product


class Command(BaseCommand):
    help = "Link products to their photo files (<serial_number>.jpg)."

    def handle(self, *args, **options):
        products = Product.objects.order_by("id")
        changed = link_images(products)
        missing = [p.name for p in products if not p.image]
        self.stdout.write(self.style.SUCCESS(f"Linked {changed} photo(s)."))
        for name in missing:
            self.stdout.write(self.style.WARNING(f"no photo yet: {name}"))
