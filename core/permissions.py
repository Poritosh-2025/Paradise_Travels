"""
Custom permissions for role-based access control.
"""
from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """
    Allow access only to super admins.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'super_admin'
        )


class IsStaffAdmin(BasePermission):
    """
    Allow access only to staff admins.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'staff_admin'
        )


class IsAdminUser(BasePermission):
    """
    Allow access to both super admin and staff admin.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['super_admin', 'staff_admin']
        )


class IsVerifiedUser(BasePermission):
    """
    Allow access only to verified users.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_verified
        )
