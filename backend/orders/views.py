from datetime import datetime
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsSalesManager

from .invoices import render_invoice_pdf
from .models import Invoice
from .serializers import InvoiceSerializer


def parse_date_param(param_value, field_name):
    if not param_value:
        return None
    val_str = str(param_value).strip()[:10]
    try:
        return datetime.strptime(val_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format for '{field_name}'. Expected YYYY-MM-DD.")


class SalesInvoiceListView(APIView):
    permission_classes = [IsSalesManager]

    def get(self, request):
        start_raw = request.query_params.get("start_date") or request.query_params.get("startDate")
        end_raw = request.query_params.get("end_date") or request.query_params.get("endDate")

        try:
            start_date = parse_date_param(start_raw, "start_date")
            end_date = parse_date_param(end_raw, "end_date")
        except ValueError as err:
            return Response({"message": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        queryset = (
            Invoice.objects.select_related("order__user")
            .prefetch_related("order__items__product__brand")
            .order_by("-issued_at")
        )

        if start_date:
            queryset = queryset.filter(issued_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(issued_at__date__lte=end_date)

        serializer = InvoiceSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SalesInvoiceDetailView(APIView):
    permission_classes = [IsSalesManager]

    def get(self, request, pk):
        invoice = get_object_or_404(
            Invoice.objects.select_related("order__user").prefetch_related("order__items__product__brand"),
            pk=pk,
        )
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_200_OK)


class SalesInvoicePdfView(APIView):
    permission_classes = [IsSalesManager]

    def get(self, request, pk):
        invoice = get_object_or_404(
            Invoice.objects.select_related("order__user").prefetch_related("order__items__product__brand"),
            pk=pk,
        )
        pdf_bytes = render_invoice_pdf(invoice)

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        should_download = request.query_params.get("download", "").lower() in ("true", "1")
        disposition = "attachment" if should_download else "inline"
        response["Content-Disposition"] = f'{disposition}; filename="{invoice.number}.pdf"'
        return response

