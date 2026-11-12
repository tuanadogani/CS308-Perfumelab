from django.urls import path

from .views import (
    SalesRefundDecisionView,
    SalesRefundDetailView,
    SalesRefundListView,
    SalesRefundReceiveView,
)

urlpatterns = [
    path("sales/refunds/", SalesRefundListView.as_view(), name="sales-refund-list"),
    path("sales/refunds/<int:pk>/", SalesRefundDetailView.as_view(), name="sales-refund-detail"),
    path("sales/refunds/<int:pk>/receive/", SalesRefundReceiveView.as_view(), name="sales-refund-receive"),
    path("sales/refunds/<int:pk>/decision/", SalesRefundDecisionView.as_view(), name="sales-refund-decision"),
]
