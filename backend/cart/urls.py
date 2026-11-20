from django.urls import path

from .views import CartItemDetailView, CartItemListView, CartMergeView, CartView

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/", CartItemListView.as_view(), name="cart-items"),
    path("cart/items/<int:product_id>/", CartItemDetailView.as_view(), name="cart-item"),
    path("cart/merge/", CartMergeView.as_view(), name="cart-merge"),
]
