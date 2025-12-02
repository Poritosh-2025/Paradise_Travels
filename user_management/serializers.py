"""
Serializers for user management endpoints.
"""
from rest_framework import serializers
from authentication.models import User


class UserListSerializer(serializers.ModelSerializer):
    """
    Serializer for user list.
    """
    user_id = serializers.UUIDField(source='id')
    user_full_name = serializers.CharField(source='name')
    user_email = serializers.EmailField(source='email')
    user_subscription = serializers.CharField(source='subscription_status')

    class Meta:
        model = User
        fields = [
            'user_id', 'user_full_name', 'user_email',
            'user_subscription', 'is_active', 'created_at'
        ]


class DeleteConfirmSerializer(serializers.Serializer):
    """
    Serializer for deletion confirmation.
    """
    deletion_token = serializers.CharField()
    confirm = serializers.BooleanField()


class DeleteCancelSerializer(serializers.Serializer):
    """
    Serializer for deletion cancellation.
    """
    deletion_token = serializers.CharField()
