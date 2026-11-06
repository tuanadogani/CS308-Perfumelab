from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsSalesManager

from .invoices import render_invoice_pdf
from .models import Invoice, Order, OrderItem, OrderStatus
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


class SalesRevenueReportView(APIView):
    """Calculates revenue, product costs, profit/loss, and chart time-series (req 11)."""

    permission_classes = [IsSalesManager]

    def get(self, request):
        start_raw = request.query_params.get("start_date") or request.query_params.get("startDate")
        end_raw = request.query_params.get("end_date") or request.query_params.get("endDate")

        try:
            start_date = parse_date_param(start_raw, "start_date")
            end_date = parse_date_param(end_raw, "end_date")
        except ValueError as err:
            return Response({"message": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        if start_date and end_date and start_date > end_date:
            return Response(
                {"message": "start_date cannot be after end_date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        orders = Order.objects.exclude(status=OrderStatus.CANCELLED)
        if start_date:
            orders = orders.filter(created_at__date__gte=start_date)
        if end_date:
            orders = orders.filter(created_at__date__lte=end_date)

        day_stats = defaultdict(lambda: {"revenue": Decimal("0"), "cost": Decimal("0"), "orders": set()})
        items = (
            OrderItem.objects.filter(order__in=orders)
            .select_related("order")
            .only("order_id", "quantity", "unit_price", "unit_cost", "order__created_at")
        )

        total_revenue = Decimal("0")
        total_cost = Decimal("0")

        for item in items:
            rev = item.unit_price * item.quantity
            cst = item.unit_cost * item.quantity
            total_revenue += rev
            total_cost += cst
            dt = item.order.created_at.date()
            day_stats[dt]["revenue"] += rev
            day_stats[dt]["cost"] += cst
            day_stats[dt]["orders"].add(item.order_id)

        chart_data = []
        if start_date and end_date and (end_date - start_date).days <= 366:
            curr = start_date
            while curr <= end_date:
                stats = day_stats.get(curr, {"revenue": Decimal("0"), "cost": Decimal("0"), "orders": set()})
                r = float(stats["revenue"])
                c = float(stats["cost"])
                chart_data.append(
                    {
                        "date": curr.isoformat(),
                        "revenue": round(r, 2),
                        "cost": round(c, 2),
                        "profit": round(r - c, 2),
                        "orderCount": len(stats["orders"]),
                    }
                )
                curr += timedelta(days=1)
        else:
            for dt in sorted(day_stats.keys()):
                stats = day_stats[dt]
                r = float(stats["revenue"])
                c = float(stats["cost"])
                chart_data.append(
                    {
                        "date": dt.isoformat(),
                        "revenue": round(r, 2),
                        "cost": round(c, 2),
                        "profit": round(r - c, 2),
                        "orderCount": len(stats["orders"]),
                    }
                )

        profit = total_revenue - total_cost
        margin = float(profit / total_revenue * 100) if total_revenue > 0 else 0.0

        return Response(
            {
                "startDate": start_date.isoformat() if start_date else None,
                "endDate": end_date.isoformat() if end_date else None,
                "totalOrders": orders.count(),
                "totalRevenue": round(float(total_revenue), 2),
                "totalCost": round(float(total_cost), 2),
                "profit": round(float(profit), 2),
                "isProfit": profit >= 0,
                "profitMargin": round(margin, 2),
                "chartData": chart_data,
            },
            status=status.HTTP_200_OK,
        )
