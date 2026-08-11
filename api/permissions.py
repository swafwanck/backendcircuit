from rest_framework import permissions

SAFE_METHODS = permissions.SAFE_METHODS


class IsAdminOrReadOnly(permissions.BasePermission):
    """Public read; writes require staff user."""
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class PublicCreateReadAdminWrite(permissions.BasePermission):
    """Anyone may GET or POST (public form); update/delete require staff."""
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS or request.method == "POST":
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
