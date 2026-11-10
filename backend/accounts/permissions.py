from rest_framework.permissions import BasePermission

from accounts.models import Role


class IsProductManager(BasePermission):
    """Restrict product management endpoints to authenticated product managers."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == Role.PRODUCT_MANAGER
        )
