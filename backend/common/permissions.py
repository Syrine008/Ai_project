from django.conf import settings
from rest_framework.permissions import BasePermission

class WorkspaceAccess(BasePermission):
    """Local research access; authenticated staff only on hosted deployments."""
    def has_permission(self, request, view):
        return settings.DEBUG or bool(request.user and request.user.is_authenticated and request.user.is_staff)
