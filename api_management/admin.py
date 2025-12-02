"""
Admin configuration for API management.
"""
from django.contrib import admin
from .models import APIKey


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ['key_name', 'key_prefix', 'is_active', 'created_by', 'last_used', 'created_at']
    list_filter = ['is_active']
    search_fields = ['key_name']
    ordering = ['-created_at']
