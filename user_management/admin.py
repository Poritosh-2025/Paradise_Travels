"""
Admin configuration for user management.
"""
from django.contrib import admin
from .models import UserDeletionRequest


@admin.register(UserDeletionRequest)
class UserDeletionRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'requested_by', 'is_confirmed', 'is_cancelled', 'expires_at', 'created_at']
    list_filter = ['is_confirmed', 'is_cancelled']
    search_fields = ['user__email', 'requested_by__email']
