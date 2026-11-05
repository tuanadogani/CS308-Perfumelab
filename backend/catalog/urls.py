from django.urls import path

from .views import BrandList, CategoryList, FamilyList, ProductDetail, ProductList

urlpatterns = [
    path("products/", ProductList.as_view(), name="product-list"),
    path("products/<int:pk>/", ProductDetail.as_view(), name="product-detail"),
    path("categories/", CategoryList.as_view(), name="category-list"),
    path("brands/", BrandList.as_view(), name="brand-list"),
    path("families/", FamilyList.as_view(), name="family-list"),
]
