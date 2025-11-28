from rest_framework.permissions import BasePermission
from .models import UserRole


class IsVerifier1(BasePermission):
    """
    Custom permission to only allow users with verifier1 role
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has verifier1 role
        return UserRole.objects.filter(
            user=request.user,
            role='verifier1'
        ).exists()


class IsVerifier2(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', '') == 'verifier2'


class IsVerifier3(BasePermission):
    """
    Custom permission to only allow users with verifier3 role
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return UserRole.objects.filter(
            user=request.user,
            role='verifier3'
        ).exists()


class IsAdmin(BasePermission):
    """
    Custom permission to only allow admin users
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return UserRole.objects.filter(
            user=request.user,
            role='admin'
        ).exists() or request.user.is_staff
