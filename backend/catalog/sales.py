"""Sales manager pricing (req 11). Product managers add products at 0 TL; sales managers price them."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsSalesManager

from .models import Product
from .serializers import ProductSerializer


def _all_products():
    # Inactive products are included too: a sales manager may price a product before it goes live.
    return Product.objects.select_related("brand", "category").prefetch_related("families", "notes")


class SetPriceSerializer(serializers.Serializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))


class SalesProductList(APIView):
    """GET /api/sales/products/?unpriced=true lists the products still waiting for a price."""

    permission_classes = [IsSalesManager]

    def get(self, request):
        products = _all_products().order_by("name", "id")
        if request.query_params.get("unpriced") == "true":
            products = products.filter(base_price=0)
        return Response(ProductSerializer(products, many=True).data)


class SalesProductPrice(APIView):
    """PATCH /api/sales/products/<id>/price/ with {"price": "1250.00"} sets the list price."""

    permission_classes = [IsSalesManager]

    def patch(self, request, pk):
        serializer = SetPriceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            product = get_object_or_404(Product.objects.select_for_update(), pk=pk)
            try:
                product.set_base_price(serializer.validated_data["price"])
            except ValidationError as exc:
                return Response({"message": " ".join(exc.messages)}, status=400)
        return Response(ProductSerializer(_all_products().get(pk=pk)).data)
