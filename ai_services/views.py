"""
Views for AI Services

Handles authenticated requests, enforces subscription limits,
and proxies to FastAPI AI service.

Integration Points:
1. JWT Authentication (from authentication app)
2. Subscription/Plan checks (from payments app)
3. Usage tracking (from payments app)
4. FastAPI proxy (to AI service on port 8001)
5. Celery tasks for async processing

Plan Details:
    Basic (Free):
        - 1 itinerary per month
        - 0 free videos (€5.99 per video, UNLIMITED paid videos)
        - AI Chatbot: FREE
        - Itinerary Customization: FREE
        - Social Sharing: FREE
        
    Premium (€19.99/month):
        - Unlimited itineraries
        - 3 free videos per month
        - After 3 free videos: €5.99 per video (UNLIMITED)
        
    Pro (€39.99/month):
        - Unlimited itineraries
        - 5 free videos per month
        - High quality video
        - After 5 free videos: €5.99 per video (UNLIMITED)
"""
from rest_framework.parsers import JSONParser
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
from .tasks import create_itinerary_task, generate_video_task, chat_task
from .fastapi_client import fastapi_client
from .usage_service import usage_service

logger = logging.getLogger(__name__)


# ==============================================================================
# ITINERARY VIEWS
# ==============================================================================

class CreateItineraryView(APIView):
    """
    Create a new travel itinerary (ASYNC with Celery).
    
    POST /api/ai/itineraries/create/
    
    Returns immediately with itinerary_id and status='pending'.
    Use GET /api/ai/itineraries/<id>/status/ to check progress.
    
    Integration:
    - Requires JWT authentication
    - Checks plan limits (Basic: 1/month, Premium/Pro: unlimited)
    - Queues Celery task to proxy to FastAPI /api/create-itinerary
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
    parser_classes = [JSONParser]
    
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
        
        # Create itinerary record with 'pending' status
        itinerary = Itinerary.objects.create(
            user=request.user,
            destination=serializer.validated_data['destination'],
            budget=serializer.validated_data['budget'],
            duration=serializer.validated_data['duration'],
            travelers=serializer.validated_data['travelers'],
            activity_preference=serializer.validated_data['activity_preference'],
            include_flights=serializer.validated_data.get('include_flights', False),
            include_hotels=serializer.validated_data.get('include_hotels', False),
            status='pending'
        )
        
        # Prepare request data for Celery task
        request_data = {
            'destination': serializer.validated_data['destination'],
            'budget': float(serializer.validated_data['budget']),
            'duration': serializer.validated_data['duration'],
            'travelers': serializer.validated_data['travelers'],
            'activity_preference': serializer.validated_data['activity_preference'],
            'include_flights': serializer.validated_data.get('include_flights', False),
            'include_hotels': serializer.validated_data.get('include_hotels', False),
            'user_location': serializer.validated_data.get('user_location', 'New York')
        }
        
        # Start async Celery task
        task = create_itinerary_task.delay(
            user_id=str(request.user.id),
            itinerary_db_id=str(itinerary.id),
            request_data=request_data
        )
        
        # Store task ID
        itinerary.celery_task_id = task.id
        itinerary.save()
        
        logger.info(f"🚀 Itinerary task queued: {task.id} for {request.user.email}")
        
        return Response({
            'status': 'success',
            'message': 'Itinerary creation started. Check status for progress.',
            'data': {
                'itinerary_id': str(itinerary.id),
                'task_id': task.id,
                'status': 'pending',
                'status_url': f'/api/ai/itineraries/{itinerary.id}/status/'
            }
        }, status=status.HTTP_202_ACCEPTED)


class ItineraryStatusView(APIView):
    """
    Get itinerary creation status.
    
    GET /api/ai/itineraries/<id>/status/
    
    Returns current status and itinerary data when completed.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, itinerary_id):
        itinerary = get_object_or_404(
            Itinerary,
            id=itinerary_id,
            user=request.user
        )
        
        response_data = {
            'status': 'success',
            'data': {
                'itinerary_id': str(itinerary.id),
                'task_id': itinerary.celery_task_id,
                'task_status': itinerary.status,
                'destination': itinerary.destination,
                'created_at': itinerary.created_at,
            }
        }
        
        if itinerary.status == 'completed':
            response_data['data']['itinerary'] = itinerary.itinerary_data
            response_data['data']['fastapi_itinerary_id'] = itinerary.fastapi_itinerary_id
            response_data['data']['completed_at'] = itinerary.completed_at
        
        elif itinerary.status == 'failed':
            response_data['data']['error'] = itinerary.error_message
        
        return Response(response_data)


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
        limit = int(request.query_params.get('limit', 100))
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
    Chat with AI to modify itinerary (ASYNC with Celery).
    
    POST /api/ai/chat/
    
    Returns immediately with message_id and status='pending'.
    Use GET /api/ai/chat/<message_id>/status/ to check progress.
    
    Request Body:
    {
        "itinerary_id": "uuid",
        "message": "Change destination to Tokyo"
    }
    
    The chat supports:
    - Questions about the itinerary
    - Modification requests (destination, budget, duration, etc.)
    - Confirmation of proposed changes
    
    NOTE: Chat is FREE for ALL plans (including Basic)
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    
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
        
        # Check if itinerary is completed
        if itinerary.status != 'completed':
            return Response({
                'status': 'error',
                'message': 'Cannot chat about an itinerary that is not completed yet'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get conversation history
        chat_history = ChatMessage.objects.filter(
            itinerary=itinerary,
            status='completed'
        ).order_by('created_at')[:20]  # Last 20 messages
        
        conversation_history = [
            {'role': msg.role, 'content': msg.message}
            for msg in chat_history
        ]
        
        # Save user message with 'pending' status
        user_message = ChatMessage.objects.create(
            itinerary=itinerary,
            role='user',
            message=serializer.validated_data['message'],
            status='pending'
        )
        
        # Start async Celery task
        task = chat_task.delay(
            user_id=str(request.user.id),
            chat_message_id=str(user_message.id),
            itinerary_id=str(itinerary.id),
            itinerary_fastapi_id=itinerary.fastapi_itinerary_id,
            message=serializer.validated_data['message'],
            conversation_history=conversation_history
        )
        
        # Store task ID
        user_message.celery_task_id = task.id
        user_message.save()
        
        logger.info(f"💬 Chat task queued: {task.id} for {request.user.email}")
        
        return Response({
            'status': 'success',
            'message': 'Chat message sent. Check status for response.',
            'data': {
                'message_id': str(user_message.id),
                'task_id': task.id,
                'status': 'pending',
                'status_url': f'/api/ai/chat/{user_message.id}/status/'
            }
        }, status=status.HTTP_202_ACCEPTED)


class ChatStatusView(APIView):
    """
    Get chat message status and response.
    
    GET /api/ai/chat/<message_id>/status/
    
    Returns current status and AI response when completed.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, message_id):
        user_message = get_object_or_404(
            ChatMessage,
            id=message_id,
            itinerary__user=request.user
        )
        
        response_data = {
            'status': 'success',
            'data': {
                'message_id': str(user_message.id),
                'task_id': user_message.celery_task_id,
                'task_status': user_message.status,
                'user_message': user_message.message,
            }
        }
        
        if user_message.status == 'completed':
            # Get assistant response (created after user message)
            assistant_message = ChatMessage.objects.filter(
                itinerary=user_message.itinerary,
                role='assistant',
                created_at__gt=user_message.created_at
            ).first()
            
            if assistant_message:
                response_data['data']['response'] = assistant_message.message
                response_data['data']['modifications_made'] = assistant_message.modifications_made
                
                # Include updated itinerary if modifications were made
                if assistant_message.modifications_made:
                    response_data['data']['updated_itinerary'] = user_message.itinerary.itinerary_data
        
        elif user_message.status == 'failed':
            response_data['data']['error'] = user_message.error_message
        
        return Response(response_data)


class ChatHistoryView(APIView):
    """
    Get chat history for an itinerary.
    
    GET /api/ai/chat/<itinerary_id>/history/
    
    NOTE: Chat history is FREE for ALL plans (including Basic)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, itinerary_id):
        itinerary = get_object_or_404(
            Itinerary,
            id=itinerary_id,
            user=request.user
        )
        
        messages = ChatMessage.objects.filter(
            itinerary=itinerary,
            status='completed'
        ).order_by('created_at')
        
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
    Start video generation for an itinerary (ASYNC with Celery).
    
    POST /api/ai/videos/generate/
    
    Returns immediately with video_id and status='pending'.
    Use GET /api/ai/videos/<id>/status/ to check progress.
    
    IMPORTANT BUSINESS LOGIC:
    - Basic (Free) plan: 0 free videos, €5.99 per video (UNLIMITED paid videos)
    - Premium plan: 3 free videos/month, then €5.99 each (UNLIMITED)
    - Pro plan: 5 free videos/month + high quality, then €5.99 each (UNLIMITED)
    
    REQUIRED: itinerary_id is REQUIRED for video generation.
    
    Request Body:
    {
        "itinerary_id": "uuid",        // REQUIRED
        "photo_id": "uuid",            // REQUIRED
        "quality": "standard",         // OPTIONAL - "high" only for Pro plan
        "payment_session_id": "cs_xxx" // REQUIRED for Basic plan / when quota exhausted
    }
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    
    def post(self, request):
        import stripe
        from django.conf import settings
        
        serializer = GenerateVideoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'status': 'error',
                'message': 'Invalid request data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get itinerary (REQUIRED)
        itinerary = get_object_or_404(
            Itinerary,
            id=serializer.validated_data['itinerary_id'],
            user=request.user
        )
        
        # Check if itinerary is completed
        if itinerary.status != 'completed':
            return Response({
                'status': 'error',
                'message': 'Cannot generate video for an incomplete itinerary. Please wait for itinerary to complete.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get photo (REQUIRED)
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
        
        if requires_payment:
            # Check for payment session ID
            payment_session_id = request.data.get('payment_session_id')
            
            if payment_session_id:
                # Verify payment with Stripe
                stripe.api_key = settings.STRIPE_SECRET_KEY
                
                try:
                    session = stripe.checkout.Session.retrieve(payment_session_id)
                    
                    # Check payment status
                    if session.payment_status != 'paid':
                        return Response({
                            'status': 'error',
                            'message': f'Payment not completed. Status: {session.payment_status}',
                            'error_code': 'payment_incomplete'
                        }, status=status.HTTP_402_PAYMENT_REQUIRED)
                    
                    # Verify this payment belongs to the user
                    session_user_id = session.metadata.get('user_id')
                    if session_user_id != str(request.user.id):
                        return Response({
                            'status': 'error',
                            'message': 'Payment session does not belong to this user',
                            'error_code': 'invalid_payment'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # Check if this session was already used for video generation
                    already_used = VideoGeneration.objects.filter(
                        user=request.user,
                        payment_session_id=payment_session_id
                    ).exists()
                    
                    if already_used:
                        return Response({
                            'status': 'error',
                            'message': 'This payment has already been used for video generation',
                            'error_code': 'payment_already_used'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # Payment verified - proceed
                    logger.info(f"✅ Payment verified for {request.user.email}: {payment_session_id}")
                    
                except stripe.error.StripeError as e:
                    logger.error(f"Stripe error: {e}")
                    return Response({
                        'status': 'error',
                        'message': f'Payment verification failed: {str(e)}',
                        'error_code': 'payment_verification_failed'
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                # No payment session - return payment required
                return Response({
                    'status': 'error',
                    'message': message,
                    'error_code': 'payment_required',
                    'video_price': usage_service.VIDEO_PRICE,
                    'checkout_url': '/api/payments/checkout/video/',
                    'note': 'You can generate UNLIMITED videos with payment (€5.99 each)'
                }, status=status.HTTP_402_PAYMENT_REQUIRED)
        else:
            is_free_quota = True
        
        # Create video generation record with 'pending' status
        video = VideoGeneration.objects.create(
            user=request.user,
            itinerary=itinerary,
            quality=requested_quality,
            user_photo=photo,
            status='pending',
            total_days=itinerary.duration,
            is_free_quota=is_free_quota,
            is_paid=requires_payment,
            payment_session_id=request.data.get('payment_session_id')
        )
        
        # Start async Celery task
        task = generate_video_task.delay(
            user_id=str(request.user.id),
            video_db_id=str(video.id),
            itinerary_fastapi_id=itinerary.fastapi_itinerary_id,
            photo_filename=photo.fastapi_filename
        )
        
        # Store task ID
        video.celery_task_id = task.id
        video.save()
        
        # Track usage
        usage_service.record_video_usage(request.user, video, is_free=is_free_quota)
        
        logger.info(f"🎬 Video task queued: {task.id} for {request.user.email}")
        
        return Response({
            'status': 'success',
            'message': 'Video generation started. Check status for progress.',
            'data': {
                'video_id': str(video.id),
                'task_id': task.id,
                'status': 'pending',
                'is_free_quota': is_free_quota,
                'is_paid': requires_payment,
                'itinerary_id': str(itinerary.id),
                'status_url': f'/api/ai/videos/{video.id}/status/'
            }
        }, status=status.HTTP_202_ACCEPTED)


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
    - Available features (including FREE features for Basic plan)
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