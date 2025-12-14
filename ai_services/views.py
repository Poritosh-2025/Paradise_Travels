"""
Views for AI Services

Handles authenticated requests, enforces subscription limits,
and proxies to FastAPI AI service.

Integration Points:
1. JWT Authentication (from authentication app)
2. Subscription/Plan checks (from payments app)
3. Usage tracking (from payments app)
4. FastAPI proxy (to AI service on port 8001)
"""
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import Itinerary, UserPhoto, VideoGeneration, ChatMessage
from .serializers import (
    CreateItinerarySerializer,
    ItinerarySerializer,
    ItineraryListSerializer,
    ReallocateBudgetSerializer,
    ChatMessageSerializer,
    ChatMessageModelSerializer,
    UserPhotoSerializer,
    GenerateVideoSerializer,
    VideoGenerationSerializer,
    VideoGenerationListSerializer,
    UsageSerializer,
)
from .fastapi_client import fastapi_client
from .usage_service import usage_service

logger = logging.getLogger(__name__)


# ==============================================================================
# ITINERARY VIEWS
# ==============================================================================

class CreateItineraryView(APIView):
    """
    Create a new travel itinerary.
    
    POST /api/ai/itineraries/create/
    
    Integration:
    - Requires JWT authentication
    - Checks plan limits (Basic: 1/month, Premium/Pro: unlimited)
    - Proxies to FastAPI /api/create-itinerary
    - Tracks usage in payments app
    
    Request Body:
    {
        "destination": "Paris",
        "budget": 3000,
        "duration": 7,
        "travelers": 2,
        "activity_preference": "moderate",
        "include_flights": true,
        "include_hotels": true,
        "user_location": "New York"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Validate request data
        serializer = CreateItinerarySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'status': 'error',
                'message': 'Invalid request data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check plan limits
        can_create, message = usage_service.can_create_itinerary(request.user)
        if not can_create:
            return Response({
                'status': 'error',
                'message': message,
                'error_code': 'limit_exceeded',
                'upgrade_url': '/pricing/'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Proxy to FastAPI
        logger.info(f"🌍 Creating itinerary for {request.user.email}: {serializer.validated_data['destination']}")
        
        result = fastapi_client.create_itinerary(
            destination=serializer.validated_data['destination'],
            budget=float(serializer.validated_data['budget']),
            duration=serializer.validated_data['duration'],
            travelers=serializer.validated_data['travelers'],
            activity_preference=serializer.validated_data['activity_preference'],
            include_flights=serializer.validated_data.get('include_flights', False),
            include_hotels=serializer.validated_data.get('include_hotels', False),
            user_location=serializer.validated_data.get('user_location', 'New York')
        )
        
        if not result['success']:
            # Check for insufficient budget error from FastAPI
            if result.get('data') and result['data'].get('error') == 'insufficient_budget':
                return Response({
                    'status': 'error',
                    'message': result['data'].get('message', 'Insufficient budget'),
                    'error_code': 'insufficient_budget',
                    'minimum_budget': result['data'].get('minimum_budget'),
                    'current_budget': result['data'].get('current_budget')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'status': 'error',
                'message': result.get('error', 'Failed to create itinerary'),
                'error_code': 'fastapi_error'
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        # Extract data from FastAPI response
        fastapi_data = result['data']
        fastapi_itinerary_id = fastapi_data.get('itinerary_id')
        itinerary_data = fastapi_data.get('itinerary', {})
        
        # Get destination info
        destination_info = itinerary_data.get('destination', {})
        
        # Create local itinerary record
        itinerary = Itinerary.objects.create(
            user=request.user,
            fastapi_itinerary_id=fastapi_itinerary_id,
            destination=destination_info.get('name', serializer.validated_data['destination']),
            destination_country=destination_info.get('country', ''),
            budget=serializer.validated_data['budget'],
            duration=serializer.validated_data['duration'],
            travelers=serializer.validated_data['travelers'],
            activity_preference=serializer.validated_data['activity_preference'],
            include_flights=serializer.validated_data.get('include_flights', False),
            include_hotels=serializer.validated_data.get('include_hotels', False),
            status='completed',
            itinerary_data=itinerary_data
        )
        
        # Track usage
        usage_service.record_itinerary_usage(request.user, itinerary)
        
        logger.info(f"✅ Itinerary created: {itinerary.id} for {request.user.email}")
        
        return Response({
            'status': 'success',
            'message': 'Itinerary created successfully',
            'data': {
                'itinerary_id': str(itinerary.id),
                'fastapi_itinerary_id': fastapi_itinerary_id,
                'itinerary': itinerary_data
            }
        }, status=status.HTTP_201_CREATED)


class ItineraryListView(APIView):
    """
    List user's itineraries.
    
    GET /api/ai/itineraries/
    
    Query Parameters:
    - status: Filter by status (pending, completed, failed)
    - limit: Number of results (default 10)
    - offset: Pagination offset
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get query parameters
        status_filter = request.query_params.get('status')
        limit = int(request.query_params.get('limit', 10))
        offset = int(request.query_params.get('offset', 0))
        
        # Build queryset
        queryset = Itinerary.objects.filter(user=request.user)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Paginate
        total = queryset.count()
        itineraries = queryset[offset:offset + limit]
        
        serializer = ItineraryListSerializer(itineraries, many=True)
        
        return Response({
            'status': 'success',
            'data': {
                'itineraries': serializer.data,
                'total': total,
                'limit': limit,
                'offset': offset
            }
        })


class ItineraryDetailView(APIView):
    """
    Get itinerary details.
    
    GET /api/ai/itineraries/<itinerary_id>/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, itinerary_id):
        itinerary = get_object_or_404(
            Itinerary,
            id=itinerary_id,
            user=request.user
        )
        
        serializer = ItinerarySerializer(itinerary)
        
        return Response({
            'status': 'success',
            'data': serializer.data
        })


class ReallocateBudgetView(APIView):
    """
    Reallocate remaining budget to selected categories.
    
    POST /api/ai/itineraries/reallocate-budget/
    
    Request Body:
    {
        "itinerary_id": "uuid",
        "selected_categories": ["food", "activities"]
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ReallocateBudgetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'status': 'error',
                'message': 'Invalid request data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get itinerary
        itinerary = get_object_or_404(
            Itinerary,
            id=serializer.validated_data['itinerary_id'],
            user=request.user
        )
        
        # Proxy to FastAPI
        result = fastapi_client.reallocate_budget(
            itinerary_id=itinerary.fastapi_itinerary_id,
            selected_categories=serializer.validated_data['selected_categories']
        )
        
        if not result['success']:
            return Response({
                'status': 'error',
                'message': result.get('error', 'Failed to reallocate budget')
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        # Update local itinerary data
        fastapi_data = result['data']
        if itinerary.itinerary_data:
            itinerary.itinerary_data['budget_breakdown'] = fastapi_data.get('budget_breakdown')
            itinerary.save()
        
        return Response({
            'status': 'success',
            'message': 'Budget reallocated successfully',
            'data': fastapi_data
        })


# ==============================================================================
# CHAT VIEWS
# ==============================================================================

class ChatView(APIView):
    """
    Chat with AI to modify itinerary.
    
    POST /api/ai/chat/
    
    Request Body:
    {
        "itinerary_id": "uuid",
        "message": "Change destination to Tokyo"
    }
    
    The chat supports:
    - Questions about the itinerary
    - Modification requests (destination, budget, duration, etc.)
    - Confirmation of proposed changes
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'status': 'error',
                'message': 'Invalid request data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get itinerary
        itinerary = get_object_or_404(
            Itinerary,
            id=serializer.validated_data['itinerary_id'],
            user=request.user
        )
        
        # Get conversation history
        chat_history = ChatMessage.objects.filter(
            itinerary=itinerary
        ).order_by('created_at')[:20]  # Last 20 messages
        
        conversation_history = [
            {'role': msg.role, 'content': msg.message}
            for msg in chat_history
        ]
        
        # Save user message
        user_message = ChatMessage.objects.create(
            itinerary=itinerary,
            role='user',
            message=serializer.validated_data['message']
        )
        
        # Proxy to FastAPI
        result = fastapi_client.chat(
            itinerary_id=itinerary.fastapi_itinerary_id,
            message=serializer.validated_data['message'],
            conversation_history=conversation_history
        )
        
        if not result['success']:
            return Response({
                'status': 'error',
                'message': result.get('error', 'Failed to process chat message')
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        fastapi_data = result['data']
        
        # Save assistant response
        assistant_message = ChatMessage.objects.create(
            itinerary=itinerary,
            role='assistant',
            message=fastapi_data.get('response', ''),
            modifications_made=fastapi_data.get('modifications_made', False)
        )
        
        # If modifications were made, update local itinerary
        if fastapi_data.get('modifications_made') and fastapi_data.get('updated_itinerary'):
            updated_itinerary = fastapi_data['updated_itinerary']
            destination_info = updated_itinerary.get('destination', {})
            
            itinerary.destination = destination_info.get('name', itinerary.destination)
            itinerary.destination_country = destination_info.get('country', '')
            itinerary.budget = updated_itinerary.get('total_budget', itinerary.budget)
            itinerary.duration = updated_itinerary.get('duration', itinerary.duration)
            itinerary.travelers = updated_itinerary.get('travelers', itinerary.travelers)
            itinerary.itinerary_data = updated_itinerary
            itinerary.save()
            
            logger.info(f"📝 Itinerary updated via chat: {itinerary.id}")
        
        return Response({
            'status': 'success',
            'data': {
                'response': fastapi_data.get('response'),
                'modifications_made': fastapi_data.get('modifications_made', False),
                'requires_confirmation': fastapi_data.get('requires_confirmation', False),
                'proposed_changes': fastapi_data.get('proposed_changes', {}),
                'updated_itinerary': fastapi_data.get('updated_itinerary')
            }
        })


class ChatHistoryView(APIView):
    """
    Get chat history for an itinerary.
    
    GET /api/ai/chat/<itinerary_id>/history/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, itinerary_id):
        itinerary = get_object_or_404(
            Itinerary,
            id=itinerary_id,
            user=request.user
        )
        
        messages = ChatMessage.objects.filter(itinerary=itinerary).order_by('created_at')
        serializer = ChatMessageModelSerializer(messages, many=True)
        
        return Response({
            'status': 'success',
            'data': {
                'messages': serializer.data,
                'itinerary_id': str(itinerary_id)
            }
        })


# ==============================================================================
# PHOTO VIEWS
# ==============================================================================

class UploadPhotoView(APIView):
    """
    Upload user photo for video generation.
    
    POST /api/ai/photos/upload/
    
    Content-Type: multipart/form-data
    Body: file (image file)
    
    Supported formats: JPEG, PNG, GIF, WebP
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        if 'file' not in request.FILES:
            return Response({
                'status': 'error',
                'message': 'No file provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        uploaded_file = request.FILES['file']
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if uploaded_file.content_type not in allowed_types:
            return Response({
                'status': 'error',
                'message': 'Invalid file type. Allowed: JPEG, PNG, GIF, WebP'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file size (max 10MB)
        if uploaded_file.size > 10 * 1024 * 1024:
            return Response({
                'status': 'error',
                'message': 'File too large. Maximum size: 10MB'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Read file content
        file_content = uploaded_file.read()
        
        # Upload to FastAPI
        result = fastapi_client.upload_photo(
            file_content=file_content,
            filename=uploaded_file.name
        )
        
        if not result['success']:
            return Response({
                'status': 'error',
                'message': result.get('error', 'Failed to upload photo')
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        fastapi_data = result['data']
        
        # Create local photo record
        photo = UserPhoto.objects.create(
            user=request.user,
            fastapi_filename=fastapi_data.get('filename'),
            fastapi_url=fastapi_data.get('url'),
            original_filename=uploaded_file.name
        )
        
        logger.info(f"📸 Photo uploaded: {photo.id} for {request.user.email}")
        
        serializer = UserPhotoSerializer(photo)
        
        return Response({
            'status': 'success',
            'message': 'Photo uploaded successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)


class UserPhotosView(APIView):
    """
    List user's uploaded photos.
    
    GET /api/ai/photos/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        photos = UserPhoto.objects.filter(user=request.user)
        serializer = UserPhotoSerializer(photos, many=True)
        
        return Response({
            'status': 'success',
            'data': {
                'photos': serializer.data
            }
        })


# ==============================================================================
# VIDEO VIEWS
# ==============================================================================

class GenerateVideoView(APIView):
    """
    Start video generation for an itinerary.
    
    POST /api/ai/videos/generate/
    
    Integration:
    - Requires JWT authentication
    - Checks video quota (Basic: 0 free, Premium: 3/month, Pro: 5/month)
    - Basic users must pay €5.99 per video
    - Pro users get high quality videos
    - Proxies to FastAPI /api/generate-video
    
    Request Body:
    {
        "itinerary_id": "uuid",
        "photo_id": "uuid",
        "quality": "standard"  // or "high" for Pro users
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = GenerateVideoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'status': 'error',
                'message': 'Invalid request data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get itinerary and photo
        itinerary = get_object_or_404(
            Itinerary,
            id=serializer.validated_data['itinerary_id'],
            user=request.user
        )
        
        photo = get_object_or_404(
            UserPhoto,
            id=serializer.validated_data['photo_id'],
            user=request.user
        )
        
        # Check video quota
        can_generate, requires_payment, message = usage_service.can_generate_video(request.user)
        
        # Get user's plan for quality check
        user_plan = usage_service.get_user_plan(request.user)
        requested_quality = serializer.validated_data.get('quality', 'standard')
        
        # Only Pro users can use high quality
        if requested_quality == 'high' and user_plan != 'pro':
            return Response({
                'status': 'error',
                'message': 'High quality videos are only available for Pro plan subscribers',
                'error_code': 'upgrade_required',
                'upgrade_url': '/pricing/'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if payment is required
        is_free_quota = False
        payment = None
        
        if requires_payment:
            # Check if user has a pending video purchase payment
            # This would be set by CreateVideoCheckoutSessionView
            pending_video_purchase = request.data.get('payment_session_verified', False)
            
            if not pending_video_purchase:
                return Response({
                    'status': 'error',
                    'message': message,
                    'error_code': 'payment_required',
                    'video_price': usage_service.VIDEO_PRICE,
                    'checkout_url': '/api/payments/checkout/video/'
                }, status=status.HTTP_402_PAYMENT_REQUIRED)
        else:
            is_free_quota = True
        
        # Proxy to FastAPI
        logger.info(f"🎬 Starting video generation for {request.user.email}: {itinerary.destination}")
        
        result = fastapi_client.generate_video(
            itinerary_id=itinerary.fastapi_itinerary_id,
            user_photo_filename=photo.fastapi_filename
        )
        
        if not result['success']:
            return Response({
                'status': 'error',
                'message': result.get('error', 'Failed to start video generation')
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        fastapi_data = result['data']
        fastapi_video_id = fastapi_data.get('video_id')
        
        # Create local video generation record
        video = VideoGeneration.objects.create(
            user=request.user,
            itinerary=itinerary,
            fastapi_video_id=fastapi_video_id,
            quality=requested_quality,
            user_photo=photo,
            status='pending',
            total_days=itinerary.duration,
            is_free_quota=is_free_quota,
            is_paid=requires_payment,
            payment=payment
        )
        
        # Track usage
        usage_service.record_video_usage(request.user, video, is_free=is_free_quota)
        
        logger.info(f"✅ Video generation started: {video.id}")
        
        return Response({
            'status': 'success',
            'message': 'Video generation started',
            'data': {
                'video_id': str(video.id),
                'fastapi_video_id': fastapi_video_id,
                'status': 'pending',
                'is_free_quota': is_free_quota
            }
        }, status=status.HTTP_201_CREATED)


class VideoStatusView(APIView):
    """
    Get video generation status.
    
    GET /api/ai/videos/<video_id>/status/
    
    Returns current status, progress, and video URL when completed.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, video_id):
        video = get_object_or_404(
            VideoGeneration,
            id=video_id,
            user=request.user
        )
        
        # If already completed or failed, return local data
        if video.status in ['completed', 'failed']:
            serializer = VideoGenerationSerializer(video)
            return Response({
                'status': 'success',
                'data': serializer.data
            })
        
        # Otherwise, check FastAPI for updates
        result = fastapi_client.get_video_status(video.fastapi_video_id)
        
        if result['success']:
            fastapi_data = result['data']
            
            # Update local record
            video.status = fastapi_data.get('status', video.status)
            video.progress = fastapi_data.get('progress', video.progress)
            video.current_day = fastapi_data.get('current_day', video.current_day)
            video.current_stage = fastapi_data.get('message', video.current_stage)
            
            if fastapi_data.get('status') == 'completed':
                video.video_url = fastapi_data.get('video_url')
                video.completed_at = timezone.now()
            elif fastapi_data.get('status') == 'failed':
                video.error_message = fastapi_data.get('error')
            
            video.save()
        
        serializer = VideoGenerationSerializer(video)
        
        return Response({
            'status': 'success',
            'data': serializer.data
        })


class VideoListView(APIView):
    """
    List user's video generations.
    
    GET /api/ai/videos/
    
    Query Parameters:
    - status: Filter by status (pending, processing, completed, failed)
    - itinerary_id: Filter by itinerary
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        queryset = VideoGeneration.objects.filter(user=request.user)
        
        # Filters
        status_filter = request.query_params.get('status')
        itinerary_id = request.query_params.get('itinerary_id')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if itinerary_id:
            queryset = queryset.filter(itinerary_id=itinerary_id)
        
        serializer = VideoGenerationListSerializer(queryset, many=True)
        
        return Response({
            'status': 'success',
            'data': {
                'videos': serializer.data
            }
        })


# ==============================================================================
# USAGE VIEWS
# ==============================================================================

class UsageView(APIView):
    """
    Get user's usage summary.
    
    GET /api/ai/usage/
    
    Returns:
    - Current plan
    - Itinerary usage (used/limit)
    - Video usage (free used/free limit/paid)
    - Available features
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        usage = usage_service.get_full_usage_summary(request.user)
        
        return Response({
            'status': 'success',
            'data': usage
        })


# ==============================================================================
# HEALTH CHECK
# ==============================================================================

class FastAPIHealthCheckView(APIView):
    """
    Check FastAPI AI service health.
    
    GET /api/ai/health/
    
    No authentication required.
    """
    permission_classes = []  # Public
    
    def get(self, request):
        result = fastapi_client.health_check()
        
        return Response({
            'status': 'success' if result['success'] else 'error',
            'fastapi_status': result.get('status'),
            'message': 'AI service is healthy' if result['success'] else result.get('error')
        }, status=status.HTTP_200_OK if result['success'] else status.HTTP_503_SERVICE_UNAVAILABLE)
