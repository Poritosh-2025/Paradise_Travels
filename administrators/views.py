"""
Views for administrators endpoints.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from core.responses import success_response, error_response, created_response, not_found_response
from core.permissions import IsAdminUser, IsSuperAdmin
from core.pagination import StandardPagination
from core.utils import get_admin_info
from authentication.models import User
from .serializers import AdminListSerializer, CreateStaffAdminSerializer, UpdateAdminSerializer


class AdminListView(APIView):
    """
    Get list of all administrators.
    GET /api/administrators/admins/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        admin_user = request.user
        
        # Get all admins (super_admin and staff_admin)
        queryset = User.objects.filter(
            role__in=['super_admin', 'staff_admin']
        ).order_by('-created_at')
        
        # Paginate
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        # Add serial numbers
        start_index = (paginator.page.number - 1) * paginator.get_page_size(request) + 1
        admins_data = []
        for index, admin in enumerate(page):
            admin_data = AdminListSerializer(admin).data
            admin_data['admin_sl_no'] = start_index + index
            admins_data.append(admin_data)
        
        return success_response(
            "Administrators retrieved",
            {
                'admin_info': get_admin_info(admin_user),
                'pagination': {
                    'current_page': paginator.page.number,
                    'total_pages': paginator.page.paginator.num_pages,
                    'total_admins': paginator.page.paginator.count,
                    'page_size': paginator.get_page_size(request),
                    'has_previous': paginator.page.has_previous(),
                    'has_next': paginator.page.has_next(),
                },
                'administrators': admins_data
            }
        )


class CreateStaffAdminView(APIView):
    """
    Create new staff admin.
    POST /api/administrators/admins/create/
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        serializer = CreateStaffAdminSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        admin = serializer.save()
        
        return created_response(
            "Staff admin created successfully",
            {
                'admin_id': str(admin.id),
                'email': admin.email,
                'role': admin.role,
                'created_at': admin.created_at.isoformat()
            }
        )


class UpdateAdminView(APIView):
    """
    Update administrator profile.
    PATCH /api/administrators/admins/{admin_id}/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def patch(self, request, admin_id):
        try:
            admin = User.objects.get(
                id=admin_id,
                role__in=['super_admin', 'staff_admin']
            )
        except User.DoesNotExist:
            return not_found_response("Administrator not found")
        
        # Only super admin can update other admins
        if request.user.role != 'super_admin' and request.user.id != admin.id:
            return error_response("Permission denied", status_code=403)
        
        serializer = UpdateAdminSerializer(admin, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        admin = serializer.save()
        
        profile_url = None
        if admin.profile_picture:
            profile_url = request.build_absolute_uri(admin.profile_picture.url)
        
        return success_response(
            "Administrator profile updated successfully",
            {
                'admin_id': str(admin.id),
                'name': admin.name,
                'email': admin.email,
                'phone_number': admin.phone_number,
                'role': admin.role,
                'profile_picture': profile_url,
                'updated_at': admin.updated_at.isoformat()
            }
        )


class DisableAdminView(APIView):
    """
    Disable administrator account.
    POST /api/administrators/admins/{admin_id}/disable/
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, admin_id):
        try:
            admin = User.objects.get(
                id=admin_id,
                role__in=['super_admin', 'staff_admin']
            )
        except User.DoesNotExist:
            return not_found_response("Administrator not found")
        
        # Cannot disable self
        if admin.id == request.user.id:
            return error_response("Cannot disable your own account")
        
        admin.is_active = False
        admin.save()
        
        return success_response(
            "Administrator disabled successfully",
            {
                'admin_id': str(admin.id),
                'admin_email': admin.email,
                'is_active': False
            }
        )


class EnableAdminView(APIView):
    """
    Enable administrator account.
    POST /api/administrators/admins/{admin_id}/enable/
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, admin_id):
        try:
            admin = User.objects.get(
                id=admin_id,
                role__in=['super_admin', 'staff_admin']
            )
        except User.DoesNotExist:
            return not_found_response("Administrator not found")
        
        admin.is_active = True
        admin.save()
        
        return success_response(
            "Administrator enabled successfully",
            {
                'admin_id': str(admin.id),
                'admin_email': admin.email,
                'is_active': True
            }
        )


class DeleteAdminView(APIView):
    """
    Delete administrator account permanently.
    DELETE /api/administrators/admins/{admin_id}/
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def delete(self, request, admin_id):
        try:
            admin = User.objects.get(
                id=admin_id,
                role__in=['super_admin', 'staff_admin']
            )
        except User.DoesNotExist:
            return not_found_response("Administrator not found")
        
        # Cannot delete self
        if admin.id == request.user.id:
            return error_response("Cannot delete your own account")
        
        admin.delete()
        
        return success_response("Administrator deleted successfully")
