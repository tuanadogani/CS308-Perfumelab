"""Cart API for logged-in customers (req 4, 7).

Guests keep their cart in the browser (localStorage); right after login the frontend
sends it once to POST /api/cart/merge/, so nothing they added is lost.
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCustomer
from catalog.models import Product

from .serializers import AddItemSerializer, MergeSerializer, SetQuantitySerializer, cart_payload
from .services import add_to_cart, cart_lines, clear_cart, get_cart, remove_from_cart, set_quantity


class CartApiView(APIView):
    permission_classes = [IsCustomer]

    def cart_response(self, cart, code=status.HTTP_200_OK, **extra):
        data = cart_payload(list(cart_lines(cart)), {"request": self.request})
        data.update(extra)
        return Response(data, status=code)

    def bad_request(self, exc):
        return Response({"message": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)


class CartView(CartApiView):
    """GET /api/cart/ shows the cart, DELETE /api/cart/ empties it."""

    def get(self, request):
        return self.cart_response(get_cart(request.user))

    def delete(self, request):
        cart = get_cart(request.user)
        clear_cart(cart)
        return self.cart_response(cart)


class CartItemListView(CartApiView):
    """POST /api/cart/items/ {productId, quantity} adds to the cart (capped at stock)."""

    def post(self, request):
        serializer = AddItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = get_object_or_404(Product, pk=serializer.validated_data["productId"])
        cart = get_cart(request.user)
        try:
            add_to_cart(cart, product, serializer.validated_data["quantity"])
        except ValidationError as exc:
            return self.bad_request(exc)
        return self.cart_response(cart, status.HTTP_201_CREATED)


class CartItemDetailView(CartApiView):
    """PATCH /api/cart/items/<product_id>/ {quantity} sets the amount (0 removes); DELETE removes."""

    def patch(self, request, product_id):
        serializer = SetQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = get_object_or_404(Product, pk=product_id)
        cart = get_cart(request.user)
        try:
            set_quantity(cart, product, serializer.validated_data["quantity"])
        except ValidationError as exc:
            return self.bad_request(exc)
        return self.cart_response(cart)

    def delete(self, request, product_id):
        cart = get_cart(request.user)
        remove_from_cart(cart, get_object_or_404(Product, pk=product_id))
        return self.cart_response(cart)


class CartMergeView(CartApiView):
    """POST /api/cart/merge/ {items: [{productId, quantity}]} after login.

    Quantities are added to what the account's cart already holds, capped at stock.
    Products that are gone or sold out are skipped and listed in `skipped`.
    """

    def post(self, request):
        serializer = MergeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = get_cart(request.user)
        wanted = serializer.validated_data["items"]
        products = Product.objects.in_bulk([line["productId"] for line in wanted])
        skipped = []
        with transaction.atomic():
            for line in wanted:
                product = products.get(line["productId"])
                try:
                    if product is None:
                        raise ValidationError("Unknown product.")
                    add_to_cart(cart, product, line["quantity"])
                except ValidationError:
                    skipped.append(line["productId"])
        return self.cart_response(cart, skipped=skipped)
