from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.urls import include, path
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "error", "database": "unavailable"}, status=503)
    return JsonResponse({"status": "ok", "database": "connected"})


urlpatterns = [
    path("api/health/", health),
    path("api/product-manager/", include("catalog.manager_urls")),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("catalog.urls")),
    path("api/", include("wishlist.urls")),
    path("api/", include("orders.urls")),
    path("api/", include("refunds.urls")),
]
