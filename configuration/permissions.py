from rest_framework.permissions import BasePermission
from configuration.models import Device


class IsDevice(BasePermission):
    """Allows access only to authenticated Device instances (kiosk endpoints)."""

    def has_permission(self, request, view):
        return isinstance(request.user, Device)
