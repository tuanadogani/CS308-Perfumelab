from django.db.models import Avg
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Brand, Category, NoteFamily, Product
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
    """GET /api/products/?q=&category=&brand=&family=&family=&sort=price_asc|price_desc|popularity

    Repeat `family` to require several scent families at once (AND).
    """

    permission_classes = [AllowAny]
    serializer_class = ProductSerializer
    pagination_class = None

    def get_queryset(self):
        p = self.request.query_params
        return search_products(
            _products(), p.get("q", ""), p.get("category", ""), p.get("brand", ""),
            p.getlist("family"), p.get("sort", "popularity"),
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


class BrandList(APIView):
    """GET /api/brands/?q=&category=&family=&family=

    Names of brands that have at least one active product matching the given
    filters, so the shop only offers brands that return results.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        p = request.query_params
        matching = search_products(
            Product.objects.filter(active=True), p.get("q", ""), p.get("category", ""), "",
            p.getlist("family"),
        )
        names = (
            Brand.objects.filter(products__in=matching.order_by().values("pk"))
            .distinct().values_list("name", flat=True)
        )
        return Response(sorted(names))


class FamilyList(APIView):
    """GET /api/families/ - scent families used by at least one active product."""

    permission_classes = [AllowAny]

    def get(self, request):
        names = NoteFamily.objects.filter(products__active=True).distinct().values_list("name", flat=True)
        return Response(sorted(names))
