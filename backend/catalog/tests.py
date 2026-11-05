from decimal import Decimal
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from .factories import make_product
from .models import NoteFamily, Product
from .selectors import search_products


class ProductModelTests(TestCase):
    def test_discount_sets_new_price_and_keeps_base(self):
        p = make_product(price="1000.00")
        p.apply_discount(25)
        p.refresh_from_db()
        self.assertEqual(p.price, Decimal("750.00"))
        self.assertEqual(p.base_price, Decimal("1000.00"))

    def test_clear_discount_restores_price(self):
        p = make_product(price="800.00")
        p.apply_discount(50)
        p.clear_discount()
        p.refresh_from_db()
        self.assertEqual(p.price, Decimal("800.00"))

    def test_discount_out_of_range_rejected(self):
        with self.assertRaises(ValidationError):
            make_product().apply_discount(120)

    def test_cost_defaults_to_half_of_price(self):
        self.assertEqual(make_product(price="900.00").effective_cost, Decimal("450.00"))

    def test_explicit_cost_wins(self):
        self.assertEqual(make_product(price="900.00", cost=Decimal("300.00")).effective_cost, Decimal("300.00"))

    def test_stock_cannot_go_negative_in_database(self):
        p = make_product(stock=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.filter(pk=p.pk).update(stock=-1)

    def test_serial_number_is_unique(self):
        make_product(serial_number="DUP")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_product(serial_number="DUP")

    def test_negative_price_rejected_in_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_product(price="-1.00")


class SearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rose = make_product(name="Rose Velours", description="Turkish rose and oud", price="500", popularity=10)
        cls.cedar = make_product(name="Cedar Noir", description="Woody leather", price="300", popularity=90, stock=0)
        cls.citrus = make_product(name="Citrus Day", description="Lemon and rose water", price="700", popularity=50)

    def names(self, **kw):
        return [p.name for p in search_products(Product.objects.all(), **kw)]

    def test_search_matches_name(self):
        self.assertEqual(self.names(q="cedar"), ["Cedar Noir"])

    def test_search_matches_description(self):
        self.assertCountEqual(self.names(q="rose"), ["Rose Velours", "Citrus Day"])

    def test_out_of_stock_still_searchable(self):
        self.assertIn("Cedar Noir", self.names(q="cedar"))

    def test_sort_price_ascending_and_descending(self):
        self.assertEqual(self.names(sort="price_asc"), ["Cedar Noir", "Rose Velours", "Citrus Day"])
        self.assertEqual(self.names(sort="price_desc"), ["Citrus Day", "Rose Velours", "Cedar Noir"])

    def test_sort_by_popularity_is_default(self):
        self.assertEqual(self.names(), ["Cedar Noir", "Citrus Day", "Rose Velours"])

    def test_single_family_filter(self):
        self.tag(woody=[self.cedar, self.rose], floral=[self.rose, self.citrus])
        self.assertCountEqual(self.names(family="Woody"), ["Cedar Noir", "Rose Velours"])

    def test_multiple_families_require_all(self):
        self.tag(woody=[self.cedar, self.rose], floral=[self.rose, self.citrus])
        self.assertEqual(self.names(family=["Woody", "Floral"]), ["Rose Velours"])

    def tag(self, woody, floral):
        NoteFamily.objects.create(name="Woody").products.set(woody)
        NoteFamily.objects.create(name="Floral").products.set(floral)


class ProductApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_products", stdout=StringIO())

    def test_seed_is_idempotent(self):
        before = Product.objects.count()
        call_command("seed_products", stdout=StringIO())
        self.assertEqual(Product.objects.count(), before)
        self.assertGreaterEqual(before, 25)

    def test_list_is_public_and_has_contract_fields(self):
        data = self.client.get("/api/products/").json()
        first = data[0]
        for key in ("id", "name", "brand", "serialNumber", "stock", "price", "warrantyStatus",
                    "distributor", "volumeMl", "notes", "families"):
            self.assertIn(key, first)
        self.assertEqual(set(first["notes"]), {"top", "heart", "base"})

    def test_filter_by_category_and_sort(self):
        data = self.client.get("/api/products/?category=cologne&sort=price_asc").json()
        self.assertTrue(data)
        self.assertTrue(all(p["category"] == "cologne" for p in data))
        prices = [p["price"] for p in data]
        self.assertEqual(prices, sorted(prices))

    def test_out_of_stock_product_is_listed(self):
        data = self.client.get("/api/products/?q=Baccarat").json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["stock"], 0)
        self.assertFalse(data[0]["inStock"])

    def test_detail_and_categories(self):
        pid = Product.objects.first().pk
        self.assertEqual(self.client.get(f"/api/products/{pid}/").status_code, 200)
        self.assertEqual(self.client.get("/api/products/999999/").status_code, 404)
        self.assertEqual(len(self.client.get("/api/categories/").json()), 4)

    def test_filter_by_brand(self):
        data = self.client.get("/api/products/?brand=Dior").json()
        self.assertEqual(len(data), 3)
        self.assertTrue(all(p["brand"] == "Dior" for p in data))

    def test_multiple_families_are_combined_with_and(self):
        data = self.client.get("/api/products/?family=Woody&family=Spicy").json()
        self.assertTrue(data)
        self.assertTrue(all({"Woody", "Spicy"} <= set(p["families"]) for p in data))
        single = self.client.get("/api/products/?family=Woody").json()
        self.assertLess(len(data), len(single))


class ProductImageTests(APITestCase):
    """Photos live in catalog/product_images/<serial>.jpg; a temp folder stands in for it here."""

    def setUp(self):
        import tempfile
        from pathlib import Path
        from unittest import mock

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        patcher = mock.patch("catalog.images.IMAGE_DIR", self.dir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _photo(self, name):
        (self.dir / name).write_bytes(b"\xff\xd8fake-jpeg")

    def test_image_path_finds_existing_photo(self):
        from .images import image_path
        self._photo("A.jpg")
        self.assertEqual(image_path("A.jpg"), self.dir / "A.jpg")

    def test_image_path_blocks_folder_tricks(self):
        from .images import image_path
        self._photo("A.jpg")
        # "../" is thrown away, so only a file directly inside the photo folder can match.
        self.assertEqual(image_path("../../A.jpg"), self.dir / "A.jpg")
        self.assertIsNone(image_path("../../config/settings.py"))

    def test_image_path_rejects_wrong_type_missing_or_blank(self):
        from .images import image_path
        self._photo("notes.txt")
        self.assertIsNone(image_path("notes.txt"))
        self.assertIsNone(image_path("missing.jpg"))
        self.assertIsNone(image_path(""))

    def test_link_command_links_only_products_with_a_file(self):
        with_photo = make_product(serial_number="HAS-PHOTO")
        without = make_product(serial_number="NO-PHOTO")
        self._photo("HAS-PHOTO.jpg")
        out = StringIO()
        call_command("link_product_images", stdout=out)
        with_photo.refresh_from_db()
        without.refresh_from_db()
        self.assertEqual(with_photo.image, "HAS-PHOTO.jpg")
        self.assertEqual(without.image, "")
        self.assertIn("no photo yet", out.getvalue())

    def test_link_clears_name_when_photo_file_is_gone(self):
        from .images import link_images
        stale = make_product(serial_number="DELETED", image="DELETED.png")  # no file on disk
        self.assertEqual(link_images(Product.objects.filter(pk=stale.pk)), 1)  # counted as a change
        stale.refresh_from_db()
        self.assertEqual(stale.image, "")

    def test_missing_file_gives_null_image_url(self):
        # Even before anyone re-runs the link command, the API must not hand out a broken link.
        p = make_product(serial_number="VANISHED", image="VANISHED.jpg")
        self.assertIsNone(self.client.get(f"/api/products/{p.pk}/").json()["imageUrl"])

    def test_link_is_safe_to_rerun(self):
        from .images import link_images
        make_product(serial_number="TWICE")
        self._photo("TWICE.jpg")
        self.assertEqual(link_images(Product.objects.all()), 1)
        self.assertEqual(link_images(Product.objects.all()), 0)

    def test_link_prefers_transparent_png_over_jpg(self):
        both = make_product(serial_number="BOTH")
        only_jpg = make_product(serial_number="JPG-ONLY")
        for name in ("BOTH.jpg", "BOTH.png", "JPG-ONLY.jpg"):
            self._photo(name)
        call_command("link_product_images", stdout=StringIO())
        both.refresh_from_db()
        only_jpg.refresh_from_db()
        self.assertEqual(both.image, "BOTH.png")
        self.assertEqual(only_jpg.image, "JPG-ONLY.jpg")

    def test_image_url_changes_when_the_photo_changes(self):
        # Browsers cache the photo for a day; a new file name must give a new address.
        p = make_product(serial_number="SWAP", image="SWAP.jpg")
        self._photo("SWAP.jpg")
        before = self.client.get(f"/api/products/{p.pk}/").json()["imageUrl"]
        self._photo("SWAP.png")
        p.image = "SWAP.png"
        p.save(update_fields=["image"])
        after = self.client.get(f"/api/products/{p.pk}/").json()["imageUrl"]
        self.assertNotEqual(before, after)

    def test_png_is_served_as_png(self):
        p = make_product(serial_number="CUT", image="CUT.png")
        self._photo("CUT.png")
        response = self.client.get(f"/api/products/{p.pk}/image/")
        response.close()  # release the file, or Windows can't delete the temp folder
        self.assertEqual(response["Content-Type"], "image/png")

    def test_api_gives_image_url_and_serves_the_file(self):
        p = make_product(serial_number="SERVE", image="SERVE.jpg")
        self._photo("SERVE.jpg")
        data = self.client.get(f"/api/products/{p.pk}/").json()
        self.assertTrue(data["imageUrl"].endswith(f"/api/products/{p.pk}/image/?v=SERVE.jpg"))
        response = self.client.get(f"/api/products/{p.pk}/image/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"\xff\xd8fake-jpeg")

    def test_no_photo_means_null_url_and_404(self):
        p = make_product()
        self.assertIsNone(self.client.get(f"/api/products/{p.pk}/").json()["imageUrl"])
        self.assertEqual(self.client.get(f"/api/products/{p.pk}/image/").status_code, 404)

    def test_inactive_product_image_is_hidden(self):
        p = make_product(serial_number="GONE", image="GONE.jpg", active=False)
        self._photo("GONE.jpg")
        self.assertEqual(self.client.get(f"/api/products/{p.pk}/image/").status_code, 404)


class FilterOptionsTests(TestCase):
    def test_lists_brands_and_families_with_counts(self):
        from .models import NoteFamily
        from .selectors import filter_options
        woody, _ = NoteFamily.objects.get_or_create(name="Woody")
        a = make_product(brand="Dior")
        make_product(brand="Dior")
        make_product(brand="Chanel")
        a.families.add(woody)
        opts = filter_options()
        self.assertEqual(opts["brands"], [{"name": "Chanel", "count": 1}, {"name": "Dior", "count": 2}])
        self.assertEqual(opts["families"], [{"name": "Woody", "count": 1}])
        self.assertEqual(opts["categories"][0]["slug"], "eau-de-parfum")

    def test_hides_brands_with_only_inactive_products(self):
        from .selectors import filter_options
        make_product(brand="Gone", active=False)
        make_product(brand="Here")
        self.assertEqual([b["name"] for b in filter_options()["brands"]], ["Here"])


class FilterOptionsApiTests(APITestCase):
    def test_filters_endpoint_is_public_and_lists_db_brands(self):
        make_product(brand="Brand From Database")
        response = self.client.get("/api/filters/")
        self.assertEqual(response.status_code, 200)
        self.assertIn({"name": "Brand From Database", "count": 1}, response.json()["brands"])
        self.assertEqual(set(response.json()), {"brands", "families", "categories"})
