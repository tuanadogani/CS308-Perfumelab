"""Where product photos live on disk and how a photo is found for a perfume.

Each photo is saved as catalog/product_images/<serial_number>.jpg and committed to
git, so a fresh database (local or Supabase) can get its photos back with
`python manage.py link_product_images`. Where each photo came from is listed in
catalog/product_images/SOURCES.md.
"""
import os
from pathlib import Path

IMAGE_DIR = Path(__file__).resolve().parent / "product_images"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def image_path(filename):
    """Full path of a stored photo, or None if the name is unsafe or the file is missing.

    basename() throws away any folders in the name, so a value like
    "../../config/settings.py" can never read a file outside IMAGE_DIR.
    """
    name = os.path.basename(filename or "")
    if not name or Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
        return None
    path = IMAGE_DIR / name
    return path if path.is_file() else None


def link_images(products):
    """Set product.image to "<serial>.jpg" when that file exists. Returns how many changed.

    Products without a photo file are left alone, so the frontend keeps drawing
    its placeholder bottle for them.
    """
    changed = 0
    for product in products:
        filename = f"{product.serial_number}.jpg"
        if image_path(filename) and product.image != filename:
            product.image = filename
            product.save(update_fields=["image"])
            changed += 1
    return changed
