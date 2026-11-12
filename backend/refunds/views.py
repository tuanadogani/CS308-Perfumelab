from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsSalesManager
from payments.bank import RefundDeclined
from .models import RefundRequest
from .serializers import RefundDecisionSerializer, RefundFilterSerializer, SalesRefundSerializer
from .services import decide_refund, receive_return


def sales_refunds():
    return RefundRequest.objects.select_related(
        "order_item__order__user", "order_item__product", "payment_refund"
    ).order_by("-requested_at", "-pk")


class SalesRefundListView(APIView):
    permission_classes = [IsSalesManager]

    def get(self, request):
        serializer = RefundFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        refunds = sales_refunds().filter(**serializer.validated_data)
        return Response(SalesRefundSerializer(refunds, many=True).data)


class SalesRefundDetailView(APIView):
    permission_classes = [IsSalesManager]

    def get(self, request, pk):
        refund = get_object_or_404(sales_refunds(), pk=pk)
        return Response(SalesRefundSerializer(refund).data)


class SalesRefundReceiveView(APIView):
    permission_classes = [IsSalesManager]

    def post(self, request, pk):
        refund = get_object_or_404(RefundRequest, pk=pk)
        try:
            receive_return(refund, request.user)
        except ValidationError as exc:
            return Response({"message": " ".join(exc.messages)}, status=400)
        return Response(SalesRefundSerializer(sales_refunds().get(pk=pk)).data)


class SalesRefundDecisionView(APIView):
    permission_classes = [IsSalesManager]

    def post(self, request, pk):
        refund = get_object_or_404(RefundRequest, pk=pk)
        serializer = RefundDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            decide_refund(refund, request.user, **serializer.validated_data)
        except RefundDeclined:
            return Response({"message": "The bank could not process the refund. Please retry."}, status=502)
        except ValidationError as exc:
            return Response({"message": " ".join(exc.messages)}, status=400)
        return Response(SalesRefundSerializer(sales_refunds().get(pk=pk)).data)
