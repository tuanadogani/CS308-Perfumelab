from django.urls import path

from .views import (
    NotificationListView,
    NotificationReadAllView,
    NotificationReadView,
    SetDiscountView,
    WishlistProductView,
    WishlistView,
)

urlpatterns = [
    path("wishlist/", WishlistView.as_view(), name="wishlist-list"),
    path("wishlist/<int:pk>/", WishlistProductView.as_view(), name="wishlist-product"),
    path("sales/discounts/", SetDiscountView.as_view(), name="sales-set-discount"),
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path("notifications/<int:pk>/read/", NotificationReadView.as_view(), name="notification-read"),
    path("notifications/read-all/", NotificationReadAllView.as_view(), name="notification-read-all"),
]
