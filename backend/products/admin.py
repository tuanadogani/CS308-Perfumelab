from django.contrib import admin
from .models import Category, Product, Order, OrderItem, Comment, Rating


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'model', 'serial_number', 'category', 'stock', 'price', 'discount_rate']
    list_filter = ['category', 'brand', 'scent_family']
    search_fields = ['name', 'model', 'serial_number', 'description']
    list_editable = ['stock', 'price', 'discount_rate']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'status', 'total_price', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['customer__email', 'customer__name']
    inlines = [OrderItemInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'customer', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['customer__email', 'product__name', 'comment_text']
    list_editable = ['status']


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'customer', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['customer__email', 'product__name']
