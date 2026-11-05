from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsSalesManager
from catalog.models import Product
from catalog.serializers import ProductSerializer
from catalog.views import _products
from .models import Notification, WishlistItem
from .serializers import NotificationSerializer, SetDiscountSerializer
from .services import set_discount


class WishlistView(APIView):
    def get(self, request):
        products = _products().filter(wishlisted_by__user=request.user).order_by("-wishlisted_by__added_at", "pk")
        return Response(ProductSerializer(products, many=True).data)


class WishlistProductView(APIView):
    def put(self, request, pk):
        product = get_object_or_404(_products(), pk=pk)
        WishlistItem.objects.get_or_create(user=request.user, product=product)
        return Response(ProductSerializer(product).data)

    def delete(self, request, pk):
        WishlistItem.objects.filter(user=request.user, product_id=pk).delete()
        return Response(status=204)


class SetDiscountView(APIView):
    permission_classes = [IsSalesManager]

    def post(self, request):
        serializer = SetDiscountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_ids = serializer.validated_data["resolved_product_ids"]
        rate = serializer.validated_data["resolved_discount_rate"]

        products = list(Product.objects.filter(id__in=product_ids, active=True))
        if not products:
            return Response(
                {"message": "No matching active products found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        notifications_sent = set_discount(request.user, products, rate)
        # Refresh product instances from database to reflect updated price and discount_rate
        for p in products:
            p.refresh_from_db()

        return Response(
            {
                "products": ProductSerializer(products, many=True).data,
                "notificationsSent": notifications_sent,
                "discountRate": float(rate),
            },
            status=status.HTTP_200_OK,
        )


class NotificationListView(APIView):
    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        return Response(NotificationSerializer(notifications, many=True).data)


class NotificationReadView(APIView):
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.read = True
        notification.save(update_fields=["read"])
        return Response(NotificationSerializer(notification).data)

    def patch(self, request, pk):
        return self.post(request, pk)


class NotificationReadAllView(APIView):
    def post(self, request):
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        return Response({"message": "All notifications marked as read."})
