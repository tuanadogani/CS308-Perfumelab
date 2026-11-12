from rest_framework.permissions import BasePermission

from accounts.models import Role


class IsCustomer(BasePermission):
    """Customer order actions cannot be performed with a staff role."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == Role.CUSTOMER
        )


class IsSalesManager(BasePermission):
    """Allows access only to authenticated users with the sales_manager role."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == Role.SALES_MANAGER
        )


class IsProductManager(BasePermission):
    """Allows access only to authenticated users with the product_manager role."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == Role.PRODUCT_MANAGER
        )


class IsSupportAgent(BasePermission):
    """Allows access only to authenticated users with the support_agent role."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == Role.SUPPORT_AGENT
        )

