"""
Views for user management endpoints.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from core.responses import success_response, error_response, not_found_response
from core.permissions import IsAdminUser
from core.pagination import StandardPagination
from core.utils import get_admin_info, generate_uuid
from authentication.models import User
from .models import UserDeletionRequest
from .serializers import UserListSerializer, DeleteConfirmSerializer, DeleteCancelSerializer


class UserListView(APIView):
    """
    Get paginated list of all users.
    GET /api/user-management/users/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        admin_user = request.user
        
        # Filter parameters
        search = request.query_params.get('search', '')
        subscription = request.query_params.get('subscription', '')
        
        # Base queryset - only regular users
        queryset = User.objects.filter(role='user')
        
        # Apply filters
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(email__icontains=search)
            )
        if subscription:
            queryset = queryset.filter(subscription_status=subscription)
        
        queryset = queryset.order_by('-created_at')
        
        # Paginate
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        # Add serial numbers
        start_index = (paginator.page.number - 1) * paginator.get_page_size(request) + 1
        users_data = []
        for index, user in enumerate(page):
            user_data = UserListSerializer(user).data
            user_data['user_sl_no'] = start_index + index
            users_data.append(user_data)
        
        return success_response(
            "Users retrieved",
            {
                'admin_info': get_admin_info(admin_user),
                'pagination': {
                    'current_page': paginator.page.number,
                    'total_pages': paginator.page.paginator.num_pages,
                    'total_users': paginator.page.paginator.count,
                    'page_size': paginator.get_page_size(request),
                    'has_previous': paginator.page.has_previous(),
                    'has_next': paginator.page.has_next(),
                    'previous_page': paginator.page.previous_page_number() if paginator.page.has_previous() else None,
                    'next_page': paginator.page.next_page_number() if paginator.page.has_next() else None,
                },
                'users': users_data
            }
        )


class DisableUserView(APIView):
    """
    Disable user account.
    POST /api/user-management/users/{user_id}/disable/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, role='user')
        except User.DoesNotExist:
            return not_found_response("User not found")
        
        user.is_active = False
        user.save()
        
        return success_response(
            "User access disabled successfully",
            {
                'user_id': str(user.id),
                'user_email': user.email,
                'is_active': False
            }
        )


class EnableUserView(APIView):
    """
    Enable user account.
    POST /api/user-management/users/{user_id}/enable/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, role='user')
        except User.DoesNotExist:
            return not_found_response("User not found")
        
        user.is_active = True
        user.save()
        
        return success_response(
            "User access enabled successfully",
            {
                'user_id': str(user.id),
                'user_email': user.email,
                'is_active': True
            }
        )


class DeleteUserRequestView(APIView):
    """
    Request user account deletion.
    POST /api/user-management/users/{user_id}/delete-request/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, role='user')
        except User.DoesNotExist:
            return not_found_response("User not found")
        
        # Create deletion request
        deletion_request = UserDeletionRequest.objects.create(
            user=user,
            requested_by=request.user,
            deletion_token=generate_uuid()
        )
        
        return success_response(
            "Deletion request initiated. Please confirm to proceed.",
            {
                'user_id': str(user.id),
                'user_email': user.email,
                'deletion_token': deletion_request.deletion_token
            }
        )


class ConfirmDeleteUserView(APIView):
    """
    Confirm and delete user account.
    POST /api/user-management/users/{user_id}/delete-confirm/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, user_id):
        serializer = DeleteConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        deletion_token = serializer.validated_data['deletion_token']
        confirm = serializer.validated_data['confirm']
        
        if not confirm:
            return error_response("Confirmation required")
        
        try:
            deletion_request = UserDeletionRequest.objects.get(
                user_id=user_id,
                deletion_token=deletion_token
            )
        except UserDeletionRequest.DoesNotExist:
            return error_response("Invalid deletion token")
        
        if not deletion_request.is_valid():
            return error_response("Deletion request expired or already processed")
        
        # Mark as confirmed and delete user
        deletion_request.is_confirmed = True
        deletion_request.save()
        
        user = deletion_request.user
        user.delete()
        
        return success_response("User account deleted successfully")


class CancelDeleteUserView(APIView):
    """
    Cancel user deletion request.
    POST /api/user-management/users/{user_id}/delete-cancel/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, user_id):
        serializer = DeleteCancelSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        deletion_token = serializer.validated_data['deletion_token']
        
        try:
            deletion_request = UserDeletionRequest.objects.get(
                user_id=user_id,
                deletion_token=deletion_token
            )
        except UserDeletionRequest.DoesNotExist:
            return error_response("Invalid deletion token")
        
        if deletion_request.is_confirmed:
            return error_response("Deletion already confirmed")
        
        deletion_request.is_cancelled = True
        deletion_request.save()
        
        return success_response("User deletion request cancelled")
