from django.urls import path
from .customer_views import (
    CustomerOrderListView,
    CustomerOrderDetailView,
    CustomerOrderCancelView,
    CustomerRefundRequestView,
)

from .views import (
    SalesInvoiceDetailView,
    SalesInvoiceListView,
    SalesInvoicePdfView,
    SalesRevenueReportView,
)

urlpatterns = [
    path("orders/", CustomerOrderListView.as_view(), name="customer-order-list"),
    path("orders/<int:pk>/", CustomerOrderDetailView.as_view(), name="customer-order-detail"),
    path("orders/<int:pk>/cancel/", CustomerOrderCancelView.as_view(), name="customer-order-cancel"),
    path("orders/<int:pk>/items/<int:item_pk>/refund/", CustomerRefundRequestView.as_view(), name="customer-refund-request"),
    path("sales/invoices/", SalesInvoiceListView.as_view(), name="sales-invoice-list"),
    path("sales/invoices/<int:pk>/", SalesInvoiceDetailView.as_view(), name="sales-invoice-detail"),
    path("sales/invoices/<int:pk>/pdf/", SalesInvoicePdfView.as_view(), name="sales-invoice-pdf"),
    path("sales/analytics/", SalesRevenueReportView.as_view(), name="sales-analytics"),
    path("sales/revenue/", SalesRevenueReportView.as_view(), name="sales-revenue"),
]
