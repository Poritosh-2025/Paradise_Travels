"""
URL Configuration for AI Services

All endpoints require JWT authentication unless specified.
"""
from django.urls import path
from .views import (
    # Itinerary
    CreateItineraryView,
    ItineraryStatusView,
    ItineraryListView,
    ItineraryDetailView,
    ReallocateBudgetView,
    # Chat
    ChatView,
     ChatStatusView,
    ChatHistoryView,
    # Photos
    UploadPhotoView,
    UserPhotosView,
    # Videos
    GenerateVideoView,
    VideoStatusView,
    VideoListView,
    # Usage
    UsageView,
    # Health
    FastAPIHealthCheckView,
)

app_name = 'ai_services'

urlpatterns = [
    # ==============================================================================
    # ITINERARY ENDPOINTS
    # ==============================================================================
    
    # POST - Create new itinerary
    # Checks plan limits, proxies to FastAPI
    path('itineraries/create/', CreateItineraryView.as_view(), name='create-itinerary'),

    path('itineraries/<uuid:itinerary_id>/status/', ItineraryStatusView.as_view(), name='itinerary-status'),
    
    # GET - List user's itineraries
    path('itineraries/', ItineraryListView.as_view(), name='itinerary-list'),
    
    # GET - Get itinerary details
    path('itineraries/<uuid:itinerary_id>/', ItineraryDetailView.as_view(), name='itinerary-detail'),
    
    # POST - Reallocate budget to categories
    path('itineraries/reallocate-budget/', ReallocateBudgetView.as_view(), name='reallocate-budget'),
    
    # ==============================================================================
    # CHAT ENDPOINTS
    # ==============================================================================
    
    # POST - Send chat message to modify itinerary
    path('chat/', ChatView.as_view(), name='chat'),
    path('chat/<uuid:message_id>/status/', ChatStatusView.as_view(), name='chat-status'),
    # GET - Get chat history for itinerary
    path('chat/<uuid:itinerary_id>/history/', ChatHistoryView.as_view(), name='chat-history'),
    
    # ==============================================================================
    # PHOTO ENDPOINTS
    # ==============================================================================
    
    # POST - Upload user photo for video generation
    path('photos/upload/', UploadPhotoView.as_view(), name='upload-photo'),
    
    # GET - List user's photos
    path('photos/', UserPhotosView.as_view(), name='photo-list'),
    
    # ==============================================================================
    # VIDEO ENDPOINTS
    # ==============================================================================
    
    # POST - Start video generation
    # Checks video quota, may require payment
    path('videos/generate/', GenerateVideoView.as_view(), name='generate-video'),
    
    # GET - Get video generation status
    path('videos/<uuid:video_id>/status/', VideoStatusView.as_view(), name='video-status'),
    
    # GET - List user's videos
    path('videos/', VideoListView.as_view(), name='video-list'),
    
    # ==============================================================================
    # USAGE & HEALTH ENDPOINTS
    # ==============================================================================
    
    # GET - Get user's usage summary
    path('usage/', UsageView.as_view(), name='usage'),
    
    # GET - Check FastAPI health (public)
    path('health/', FastAPIHealthCheckView.as_view(), name='health'),
]
