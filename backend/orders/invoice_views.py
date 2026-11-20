"""The customer's own invoice: shown on screen after paying, and as a PDF (req 4)."""
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCustomer

from .invoices import render_invoice_pdf
from .models import Invoice


class InvoiceLineSerializer(serializers.Serializer):
    productId = serializers.IntegerField(source="product_id")
    name = serializers.CharField(source="product.name")
    brand = serializers.CharField(source="product.brand.name")
    volumeMl = serializers.IntegerField(source="product.volume_ml")
    quantity = serializers.IntegerField()
    unitPrice = serializers.DecimalField(source="unit_price", max_digits=10, decimal_places=2)
    lineTotal = serializers.DecimalField(source="line_total", max_digits=12, decimal_places=2)


class CustomerInvoiceSerializer(serializers.Serializer):
    number = serializers.CharField()
    issuedAt = serializers.DateTimeField(source="issued_at")
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    orderId = serializers.IntegerField(source="order_id")
    customerName = serializers.SerializerMethodField()
    customerEmail = serializers.EmailField(source="order.user.email")
    shippingAddress = serializers.CharField(source="order.shipping_address")
    cardLast4 = serializers.CharField(source="order.card_last4")
    items = InvoiceLineSerializer(source="order.items.all", many=True)
    pdfUrl = serializers.SerializerMethodField()

    def get_customerName(self, invoice):
        return invoice.order.user.name or invoice.order.user.email

    def get_pdfUrl(self, invoice):
        request = self.context.get("request")
        path = reverse("customer-invoice-pdf", args=[invoice.order_id])
        return request.build_absolute_uri(path) if request else path


def own_invoice(request, order_id):
    """Another customer's invoice is a 404, not a 403: we don't reveal that it exists."""
    return get_object_or_404(
        Invoice.objects.select_related("order__user").prefetch_related("order__items__product__brand"),
        order_id=order_id, order__user=request.user,
    )


class CustomerInvoiceView(APIView):
    """GET /api/orders/<id>/invoice/ - the invoice as data for the on-screen invoice."""

    permission_classes = [IsCustomer]

    def get(self, request, pk):
        invoice = own_invoice(request, pk)
        return Response(CustomerInvoiceSerializer(invoice, context={"request": request}).data)


class CustomerInvoicePdfView(APIView):
    """GET /api/orders/<id>/invoice/pdf/ - the same PDF that was emailed (?download=1 to save)."""

    permission_classes = [IsCustomer]

    def get(self, request, pk):
        invoice = own_invoice(request, pk)
        response = HttpResponse(render_invoice_pdf(invoice), content_type="application/pdf")
        download = request.query_params.get("download", "").lower() in ("1", "true")
        response["Content-Disposition"] = (
            f'{"attachment" if download else "inline"}; filename="{invoice.number}.pdf"'
        )
        return response
