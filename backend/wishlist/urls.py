from django.urls import path
from .views import WishlistView, WishlistProductView

urlpatterns = [
    path("wishlist/", WishlistView.as_view(), name="wishlist-list"),
    path("wishlist/<int:pk>/", WishlistProductView.as_view(), name="wishlist-product"),
]
