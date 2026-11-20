from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCustomer
from cart.services import get_cart
from orders.models import Order

from . import bank
from .models import CreditCard
from .serializers import CheckoutResultSerializer, CheckoutSerializer, SavedCardSerializer
from .services import checkout


def card_for(user, data):
    """Reuse the saved card with this number, or save a new one (hash + last 4 only)."""
    number = data["cardNumber"]
    for card in user.cards.filter(last4=number[-4:]):
        if card.matches(number):
            return card
    return CreditCard.from_number(
        user, number, data["holderName"], data["expiryMonth"], data["expiryYear"]
    )


class CheckoutView(APIView):
    """POST /api/checkout/ - pay for the cart and place the order (req 4).

    All or nothing: if the cart is empty, a product ran out or the bank declines, no order,
    no stock change, no new saved card, and the cart stays as it was.
    """

    permission_classes = [IsCustomer]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            with transaction.atomic():
                card = card_for(request.user, data)
                order = checkout(
                    request.user, get_cart(request.user), card, data["cardNumber"],
                    shipping_address=data.get("shippingAddress") or None,
                )
        except bank.PaymentDeclined as exc:
            return Response({"message": str(exc)}, status=status.HTTP_402_PAYMENT_REQUIRED)
        except ValidationError as exc:
            return Response({"message": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        order = (
            Order.objects.select_related("invoice", "payment")
            .prefetch_related("items__product", "items__refund__payment_refund")
            .get(pk=order.pk)
        )
        return Response(CheckoutResultSerializer(order).data, status=status.HTTP_201_CREATED)


class SavedCardListView(APIView):
    """GET /api/cards/ - the customer's saved cards for the checkout page (last 4 digits only)."""

    permission_classes = [IsCustomer]

    def get(self, request):
        cards = request.user.cards.order_by("-created_at")
        return Response(SavedCardSerializer(cards, many=True).data)
