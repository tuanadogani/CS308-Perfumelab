from rest_framework import serializers

from catalog.serializers import ProductSerializer


class CartLineSerializer(serializers.Serializer):
    productId = serializers.IntegerField(source="product_id")
    name = serializers.CharField(source="product.name")
    brand = serializers.CharField(source="product.brand.name")
    volumeMl = serializers.IntegerField(source="product.volume_ml")
    unitPrice = serializers.DecimalField(source="product.price", max_digits=10, decimal_places=2)
    quantity = serializers.IntegerField()
    stock = serializers.IntegerField(source="product.stock")
    lineTotal = serializers.SerializerMethodField()
    imageUrl = serializers.SerializerMethodField()

    def get_lineTotal(self, line):
        return f"{line.product.price * line.quantity:.2f}"

    def get_imageUrl(self, line):
        # same absolute photo URL the shop pages use
        return ProductSerializer(context=self.context).get_imageUrl(line.product)


def cart_payload(lines, context):
    """{items, itemCount, total} for the cart and checkout pages (req 4)."""
    items = CartLineSerializer(lines, many=True, context=context).data
    total = sum(line.product.price * line.quantity for line in lines)
    return {"items": items, "itemCount": sum(l.quantity for l in lines), "total": f"{total:.2f}"}


class AddItemSerializer(serializers.Serializer):
    productId = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class SetQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0)


class MergeSerializer(serializers.Serializer):
    """The guest's localStorage cart, sent once right after login."""

    items = AddItemSerializer(many=True, allow_empty=True)
