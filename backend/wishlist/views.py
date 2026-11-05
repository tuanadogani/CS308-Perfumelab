from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.serializers import ProductSerializer
from catalog.views import _products
from .models import WishlistItem


class WishlistView(APIView):
    def get(self, request):
        products = _products().filter(wishlisted_by__user=request.user).order_by("-wishlisted_by__added_at", "pk")
        return Response(ProductSerializer(products, many=True).data)


class WishlistProductView(APIView):
    def put(self, request, pk):
        product = get_object_or_404(_products(), pk=pk)
        WishlistItem.objects.get_or_create(user=request.user, product=product)
        return Response(ProductSerializer(product).data)

    def delete(self, request, pk):
        WishlistItem.objects.filter(user=request.user, product_id=pk).delete()
        return Response(status=204)
