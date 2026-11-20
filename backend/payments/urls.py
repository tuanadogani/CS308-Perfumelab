from django.urls import path

from .views import CheckoutView, SavedCardListView

urlpatterns = [
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("cards/", SavedCardListView.as_view(), name="saved-cards"),
]
