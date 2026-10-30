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

    class Meta:
        model = Product
        fields = [
            "id", "name", "brand", "model", "serialNumber", "description", "category", "gender",
            "volumeMl", "notes", "families", "stock", "inStock", "price", "originalPrice",
            "discountRate", "warrantyStatus", "distributor", "popularity", "rating",
        ]

    def get_notes(self, obj):
        grouped = {"top": [], "heart": [], "base": []}
        for note in obj.notes.all():
            grouped[note.tier].append(note.name)
        return grouped

    def get_rating(self, obj):
        average = getattr(obj, "avg_rating", None)
        return round(float(average), 1) if average is not None else None
