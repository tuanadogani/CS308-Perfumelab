from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCustomer
from refunds.serializers import CreateRefundSerializer, RefundRequestSerializer
from refunds.services import request_refund

from .customer_serializers import CustomerOrderSerializer
from .models import Order, OrderItem
from .services import cancel_order


def customer_orders(user):
    return Order.objects.filter(user=user).prefetch_related("items__product", "items__refund")


class CustomerOrderListView(APIView):
    permission_classes = [IsCustomer]

    def get(self, request):
        return Response(CustomerOrderSerializer(customer_orders(request.user), many=True).data)


class CustomerOrderDetailView(APIView):
    permission_classes = [IsCustomer]

    def get(self, request, pk):
        order = get_object_or_404(customer_orders(request.user), pk=pk)
        return Response(CustomerOrderSerializer(order).data)


class CustomerOrderCancelView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        try:
            cancel_order(order)
        except ValidationError as exc:
            return Response({"message": " ".join(exc.messages)}, status=400)
        order = customer_orders(request.user).get(pk=pk)
        return Response(CustomerOrderSerializer(order).data)


class CustomerRefundRequestView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request, pk, item_pk):
        item = get_object_or_404(OrderItem, pk=item_pk, order_id=pk, order__user=request.user)
        serializer = CreateRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refund = request_refund(request.user, item, **serializer.validated_data)
        except ValidationError as exc:
            return Response({"message": " ".join(exc.messages)}, status=400)
        return Response(RefundRequestSerializer(refund).data, status=201)
