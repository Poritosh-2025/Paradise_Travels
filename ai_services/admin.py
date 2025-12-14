"""
Django Admin Configuration for AI Services
"""
from django.contrib import admin
from .models import Itinerary, UserPhoto, VideoGeneration, ChatMessage


@admin.register(Itinerary)
class ItineraryAdmin(admin.ModelAdmin):
    """Admin for Itinerary model"""
    
    list_display = [
        'id',
        'user_email',
        'destination',
        'destination_country',
        'budget',
        'duration',
        'travelers',
        'status',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'activity_preference',
        'include_flights',
        'include_hotels',
        'created_at',
    ]
    
    search_fields = [
        'user__email',
        'user__name',
        'destination',
        'destination_country',
        'fastapi_itinerary_id',
    ]
    
    readonly_fields = [
        'id',
        'fastapi_itinerary_id',
        'created_at',
        'updated_at',
    ]
    
    ordering = ['-created_at']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'


@admin.register(UserPhoto)
class UserPhotoAdmin(admin.ModelAdmin):
    """Admin for UserPhoto model"""
    
    list_display = [
        'id',
        'user_email',
        'original_filename',
        'fastapi_filename',
        'created_at',
    ]
    
    search_fields = [
        'user__email',
        'user__name',
        'original_filename',
        'fastapi_filename',
    ]
    
    readonly_fields = [
        'id',
        'fastapi_filename',
        'fastapi_url',
        'created_at',
    ]
    
    ordering = ['-created_at']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'


@admin.register(VideoGeneration)
class VideoGenerationAdmin(admin.ModelAdmin):
    """Admin for VideoGeneration model"""
    
    list_display = [
        'id',
        'user_email',
        'itinerary_destination',
        'quality',
        'status',
        'progress',
        'is_free_quota',
        'is_paid',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'quality',
        'is_free_quota',
        'is_paid',
        'created_at',
    ]
    
    search_fields = [
        'user__email',
        'user__name',
        'itinerary__destination',
        'fastapi_video_id',
    ]
    
    readonly_fields = [
        'id',
        'fastapi_video_id',
        'progress',
        'current_day',
        'total_days',
        'current_stage',
        'video_url',
        'error_message',
        'created_at',
        'updated_at',
        'completed_at',
    ]
    
    ordering = ['-created_at']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def itinerary_destination(self, obj):
        return obj.itinerary.destination
    itinerary_destination.short_description = 'Destination'
    itinerary_destination.admin_order_field = 'itinerary__destination'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Admin for ChatMessage model"""
    
    list_display = [
        'id',
        'itinerary_destination',
        'role',
        'message_preview',
        'modifications_made',
        'created_at',
    ]
    
    list_filter = [
        'role',
        'modifications_made',
        'created_at',
    ]
    
    search_fields = [
        'itinerary__destination',
        'itinerary__user__email',
        'message',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
    ]
    
    ordering = ['-created_at']
    
    def itinerary_destination(self, obj):
        return f"{obj.itinerary.destination} ({obj.itinerary.user.email})"
    itinerary_destination.short_description = 'Itinerary'
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'
