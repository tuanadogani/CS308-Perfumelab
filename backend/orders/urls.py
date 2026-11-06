from django.urls import path

from .views import SalesInvoiceDetailView, SalesInvoiceListView, SalesInvoicePdfView

urlpatterns = [
    path("sales/invoices/", SalesInvoiceListView.as_view(), name="sales-invoice-list"),
    path("sales/invoices/<int:pk>/", SalesInvoiceDetailView.as_view(), name="sales-invoice-detail"),
    path("sales/invoices/<int:pk>/pdf/", SalesInvoicePdfView.as_view(), name="sales-invoice-pdf"),
]

