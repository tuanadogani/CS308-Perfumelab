from django.urls import path

from .views import ProductCommentsView, ProductRatingView

urlpatterns = [
    path("products/<int:pk>/comments/", ProductCommentsView.as_view(), name="product-comments"),
    path("products/<int:pk>/rating/", ProductRatingView.as_view(), name="product-rating"),
]
