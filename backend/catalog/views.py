from django.db.models import Avg
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from .models import Category, Product
from .selectors import search_products
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
