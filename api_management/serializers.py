"""
Serializers for API management endpoints.
"""
from rest_framework import serializers
from .models import APIKey


class APIKeySerializer(serializers.ModelSerializer):
    """
    Serializer for API key display.
    """
    key_id = serializers.UUIDField(source='id')

    class Meta:
        model = APIKey
        fields = ['key_id', 'key_name', 'key_prefix', 'created_at', 'last_used', 'is_active']


class UpdateAPIKeySerializer(serializers.Serializer):
    """
    Serializer for updating/creating API key.
    """
    new_api_key = serializers.CharField(max_length=255)
    key_name = serializers.CharField(max_length=255)
