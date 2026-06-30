from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        return user.role == 'admin'


class IsRoleStudent(permissions.BasePermission):
    message = "Student access only."

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        return user.role == "student"


STUDENT_ACCESS = [IsAuthenticated, IsRoleStudent]
