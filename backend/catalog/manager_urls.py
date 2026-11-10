from django.urls import path
from .manager import (ManagerProducts, ManagerProduct, ManagerCategories, ManagerCategory,
                      ManagerDeliveries, ManagerOrderStatus, ManagerComments, ManagerComment)

urlpatterns = [
    path('products/', ManagerProducts.as_view()),
    path('products/<int:pk>/', ManagerProduct.as_view()),
    path('categories/', ManagerCategories.as_view()),
    path('categories/<int:pk>/', ManagerCategory.as_view()),
    path('deliveries/', ManagerDeliveries.as_view()),
    path('orders/<int:pk>/status/', ManagerOrderStatus.as_view()),
    path('comments/', ManagerComments.as_view()),
    path('comments/<int:pk>/', ManagerComment.as_view()),
]
