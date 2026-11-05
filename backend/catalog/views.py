from django.db.models import Avg
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views import View
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .images import image_path
from .models import Category, Product
from .selectors import filter_options, search_products
from .serializers import CategorySerializer, ProductSerializer


def _products():
    return (
        Product.objects.filter(active=True)
        .select_related("brand", "category")
        .prefetch_related("families", "notes")
        .annotate(avg_rating=Avg("ratings__score"))
    )


class ProductList(ListAPIView):
    """GET /api/products/?q=&category=&brand=&family=&sort=price_asc|price_desc|popularity"""

    permission_classes = [AllowAny]
    serializer_class = ProductSerializer
    pagination_class = None

    def get_queryset(self):
        p = self.request.query_params
        return search_products(
            _products(), p.get("q", ""), p.get("category", ""), p.get("brand", ""),
            p.get("family", ""), p.get("sort", "popularity"),
        )


class ProductDetail(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer

    def get_queryset(self):
        return _products()


class CategoryList(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    pagination_class = None


class ProductImage(View):
    """GET /api/products/<id>/image/ - the perfume's photo (public, like the catalog)."""

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk, active=True)
        path = image_path(product.image)
        if path is None:
            raise Http404("No image for this product.")
        response = FileResponse(open(path, "rb"))
        response["Cache-Control"] = "public, max-age=86400"
        return response


class FilterOptions(APIView):
    """GET /api/filters/ - brands, scent families and categories (with product counts) for the shop sidebar."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(filter_options())
