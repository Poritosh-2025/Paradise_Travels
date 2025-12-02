"""
Views for API management endpoints.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from core.responses import success_response, error_response, not_found_response
from core.permissions import IsAdminUser, IsSuperAdmin
from core.utils import get_admin_info, mask_api_key
from .models import APIKey
from .serializers import APIKeySerializer, UpdateAPIKeySerializer


class ViewAPIKeyView(APIView):
    """
    View current API key details.
    GET /api/api-management/key/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        admin_user = request.user
        
        # Get the most recent active API key
        api_key = APIKey.objects.filter(is_active=True).first()
        
        if not api_key:
            return success_response(
                "No active API key found",
                {
                    'admin_info': get_admin_info(admin_user),
                    'api_key_info': None
                }
            )
        
        return success_response(
            "API key retrieved",
            {
                'admin_info': get_admin_info(admin_user),
                'api_key_info': APIKeySerializer(api_key).data
            }
        )


class UpdateAPIKeyView(APIView):
    """
    Update/rotate API key.
    POST /api/api-management/key/update/
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        serializer = UpdateAPIKeySerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        new_api_key = serializer.validated_data['new_api_key']
        key_name = serializer.validated_data['key_name']
        
        # Deactivate old keys
        APIKey.objects.filter(is_active=True).update(is_active=False)
        
        # Create new key
        api_key = APIKey.objects.create(
            key_name=key_name,
            api_key=new_api_key,
            key_prefix=mask_api_key(new_api_key),
            created_by=request.user,
            is_active=True
        )
        
        return success_response(
            "API key updated successfully",
            {
                'key_id': str(api_key.id),
                'key_name': api_key.key_name,
                'key_prefix': api_key.key_prefix,
                'created_at': api_key.created_at.isoformat(),
                'is_active': api_key.is_active
            }
        )


class DeleteAPIKeyView(APIView):
    """
    Delete API key.
    DELETE /api/api-management/key/{key_id}/
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def delete(self, request, key_id):
        try:
            api_key = APIKey.objects.get(id=key_id)
        except APIKey.DoesNotExist:
            return not_found_response("API key not found")
        
        api_key.delete()
        
        return success_response("API key deleted successfully")
