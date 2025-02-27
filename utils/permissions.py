from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to allow only owners or admins to access an object.
    """

    def has_object_permission(self, request, view, obj):
        # Allow admins to perform any action
        if request.user.is_staff:
            return True

        # Check if the object has a user attribute that matches the request user
        if hasattr(obj, "user"):
            return obj.user == request.user

        # Check if the object has a user_id attribute that matches the request user id
        if hasattr(obj, "user_id"):
            return obj.user_id == request.user.id

        # Handle special cases for different models

        # For Order related models
        if hasattr(obj, "order") and hasattr(obj.order, "user"):
            return obj.order.user == request.user

        # For Profile models
        if hasattr(obj, "profile") and hasattr(obj.profile, "user"):
            return obj.profile.user == request.user

        return False


class ReadOnly(permissions.BasePermission):
    """
    Permission to allow read-only access.
    """

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission to allow anyone to read, but only admins to write.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user and request.user.is_staff
