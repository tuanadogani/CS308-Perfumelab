from django.urls import path

from .views import ProductCommentsView

urlpatterns = [
    path("products/<int:pk>/comments/", ProductCommentsView.as_view(), name="product-comments"),
]
