from urllib.parse import quote

from django.urls import reverse
from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="slug")

    class Meta:
        model = Category
        fields = ["id", "name"]


class ProductSerializer(serializers.ModelSerializer):
    """camelCase keys on purpose: this is the shape the frontend's product mock uses."""

    serialNumber = serializers.CharField(source="serial_number")
    warrantyStatus = serializers.CharField(source="warranty_status")
    volumeMl = serializers.IntegerField(source="volume_ml")
    brand = serializers.CharField(source="brand.name")
    category = serializers.CharField(source="category.slug")
    families = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    notes = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    inStock = serializers.BooleanField(source="in_stock")
    price = serializers.FloatField()
    originalPrice = serializers.FloatField(source="base_price")
    discountRate = serializers.FloatField(source="discount_rate")
    imageUrl = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "brand", "model", "serialNumber", "description", "category", "gender",
            "volumeMl", "notes", "families", "stock", "inStock", "price", "originalPrice",
            "discountRate", "warrantyStatus", "distributor", "popularity", "rating", "imageUrl",
        ]

    def get_notes(self, obj):
        grouped = {"top": [], "heart": [], "base": []}
        for note in obj.notes.all():
            grouped[note.tier].append(note.name)
        return grouped

    def get_imageUrl(self, obj):
        # Absolute URL because the React app runs on another port than Django.
        if not obj.image:
            return None
        # ?v=<file name>: a new photo gets a new address, so browsers don't keep showing
        # the old one from their cache (the image endpoint is cached for a day).
        path = f'{reverse("product-image", args=[obj.pk])}?v={quote(obj.image)}'
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path

    def get_rating(self, obj):
        average = getattr(obj, "avg_rating", None)
        return round(float(average), 1) if average is not None else None
