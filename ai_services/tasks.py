"""
Celery tasks for AI Services

Handles long-running AI operations asynchronously.
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, soft_time_limit=600, time_limit=660)
def create_itinerary_task(self, user_id, itinerary_db_id, request_data):
    """
    Async task to create itinerary via FastAPI.
    
    Args:
        user_id: User ID
        itinerary_db_id: Local Itinerary model ID
        request_data: Dict with destination, budget, duration, etc.
    """
    from ai_services.models import Itinerary
    from ai_services.fastapi_client import fastapi_client
    from ai_services.usage_service import usage_service
    from authentication.models import User
    
    logger.info(f"🚀 Starting itinerary task for user {user_id}: {request_data.get('destination')}")
    
    try:
        # Get itinerary record
        itinerary = Itinerary.objects.get(id=itinerary_db_id)
        itinerary.status = 'processing'
        itinerary.save()
        
        # Call FastAPI
        result = fastapi_client.create_itinerary(
            destination=request_data['destination'],
            budget=float(request_data['budget']),
            duration=request_data['duration'],
            travelers=request_data['travelers'],
            activity_preference=request_data['activity_preference'],
            include_flights=request_data.get('include_flights', False),
            include_hotels=request_data.get('include_hotels', False),
            user_location=request_data.get('user_location', 'New York')
        )
        
        if not result['success']:
            # Handle error
            itinerary.status = 'failed'
            itinerary.error_message = result.get('error', 'Failed to create itinerary')
            itinerary.save()
            logger.error(f"❌ Itinerary creation failed: {result.get('error')}")
            return {'success': False, 'error': result.get('error')}
        
        # Extract data from FastAPI response
        fastapi_data = result['data']
        fastapi_itinerary_id = fastapi_data.get('itinerary_id')
        itinerary_data = fastapi_data.get('itinerary', {})
        destination_info = itinerary_data.get('destination', {})
        
        # Update local itinerary record
        itinerary.fastapi_itinerary_id = fastapi_itinerary_id
        itinerary.destination = destination_info.get('name', request_data['destination'])
        itinerary.destination_country = destination_info.get('country', '')
        itinerary.status = 'completed'
        itinerary.itinerary_data = itinerary_data
        itinerary.completed_at = timezone.now()
        itinerary.save()
        
        # Track usage
        user = User.objects.get(id=user_id)
        usage_service.record_itinerary_usage(user, itinerary)
        
        logger.info(f"✅ Itinerary created successfully: {itinerary.id}")
        
        return {
            'success': True,
            'itinerary_id': str(itinerary.id),
            'fastapi_itinerary_id': fastapi_itinerary_id
        }
        
    except Exception as e:
        logger.error(f"❌ Itinerary task error: {e}")
        
        # Update status to failed
        try:
            itinerary = Itinerary.objects.get(id=itinerary_db_id)
            itinerary.status = 'failed'
            itinerary.error_message = str(e)
            itinerary.save()
        except:
            pass
        
        # Retry on failure
        raise self.retry(exc=e, countdown=30)


@shared_task(bind=True, max_retries=2, soft_time_limit=900, time_limit=960)
def generate_video_task(self, user_id, video_db_id, itinerary_fastapi_id, photo_filename):
    """
    Async task to generate video via FastAPI.
    
    Args:
        user_id: User ID
        video_db_id: Local VideoGeneration model ID
        itinerary_fastapi_id: FastAPI itinerary ID
        photo_filename: User photo filename
    """
    from ai_services.models import VideoGeneration
    from ai_services.fastapi_client import fastapi_client
    from ai_services.usage_service import usage_service
    from authentication.models import User
    
    logger.info(f"🎬 Starting video generation task for user {user_id}")
    
    try:
        # Get video record
        video = VideoGeneration.objects.get(id=video_db_id)
        video.status = 'processing'
        video.save()
        
        # Call FastAPI to start video generation
        result = fastapi_client.generate_video(
            itinerary_id=itinerary_fastapi_id,
            user_photo_filename=photo_filename
        )
        
        if not result['success']:
            video.status = 'failed'
            video.error_message = result.get('error', 'Failed to start video generation')
            video.save()
            logger.error(f"❌ Video generation failed: {result.get('error')}")
            return {'success': False, 'error': result.get('error')}
        
        fastapi_data = result['data']
        fastapi_video_id = fastapi_data.get('video_id')
        
        video.fastapi_video_id = fastapi_video_id
        video.status = 'generating'
        video.save()
        
        # Poll for completion (check every 30 seconds, max 20 minutes)
        import time
        max_attempts = 40
        
        for attempt in range(max_attempts):
            time.sleep(30)  # Wait 30 seconds between checks
            
            status_result = fastapi_client.get_video_status(fastapi_video_id)
            
            if status_result['success']:
                status_data = status_result['data']
                video.progress = status_data.get('progress', 0)
                video.current_day = status_data.get('current_day', 0)
                video.current_stage = status_data.get('message', '')
                
                if status_data.get('status') == 'completed':
                    video.status = 'completed'
                    video.video_url = status_data.get('video_url')
                    video.completed_at = timezone.now()
                    video.save()
                    
                    logger.info(f"✅ Video generation completed: {video.id}")
                    return {
                        'success': True,
                        'video_id': str(video.id),
                        'video_url': video.video_url
                    }
                
                elif status_data.get('status') == 'failed':
                    video.status = 'failed'
                    video.error_message = status_data.get('error', 'Video generation failed')
                    video.save()
                    return {'success': False, 'error': video.error_message}
                
                video.save()
        
        # Timeout after max attempts
        video.status = 'failed'
        video.error_message = 'Video generation timed out'
        video.save()
        return {'success': False, 'error': 'Video generation timed out'}
        
    except Exception as e:
        logger.error(f"❌ Video task error: {e}")
        
        try:
            video = VideoGeneration.objects.get(id=video_db_id)
            video.status = 'failed'
            video.error_message = str(e)
            video.save()
        except:
            pass
        
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=2, soft_time_limit=300, time_limit=360)
def chat_task(self, user_id, chat_message_id, itinerary_id, itinerary_fastapi_id, message, conversation_history):
    """
    Async task to process chat message via FastAPI.
    
    Args:
        user_id: User ID
        chat_message_id: Local ChatMessage model ID
        itinerary_id: Local Itinerary ID
        itinerary_fastapi_id: FastAPI itinerary ID
        message: User's message
        conversation_history: Previous conversation
    """
    from ai_services.models import Itinerary, ChatMessage
    from ai_services.fastapi_client import fastapi_client
    
    logger.info(f"💬 Starting chat task for user {user_id}")
    
    try:
        # Get chat message record
        user_message = ChatMessage.objects.get(id=chat_message_id)
        user_message.status = 'processing'
        user_message.save()
        
        # Call FastAPI
        result = fastapi_client.chat(
            itinerary_id=itinerary_fastapi_id,
            message=message,
            conversation_history=conversation_history
        )
        
        if not result['success']:
            user_message.status = 'failed'
            user_message.error_message = result.get('error', 'Chat request failed')
            user_message.save()
            logger.error(f"❌ Chat failed: {result.get('error')}")
            return {'success': False, 'error': result.get('error')}
        
        fastapi_data = result['data']
        
        # Create assistant response message
        assistant_message = ChatMessage.objects.create(
            itinerary_id=itinerary_id,
            role='assistant',
            message=fastapi_data.get('response', ''),
            modifications_made=fastapi_data.get('modifications_made', False),
            status='completed'
        )
        
        # Update user message status
        user_message.status = 'completed'
        user_message.save()
        
        # Update itinerary if modifications were made
        if fastapi_data.get('modifications_made') and fastapi_data.get('updated_itinerary'):
            itinerary = Itinerary.objects.get(id=itinerary_id)
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
        
        logger.info(f"✅ Chat completed: {assistant_message.id}")
        
        return {
            'success': True,
            'response': fastapi_data.get('response'),
            'modifications_made': fastapi_data.get('modifications_made', False),
            'assistant_message_id': str(assistant_message.id)
        }
        
    except Exception as e:
        logger.error(f"❌ Chat task error: {e}")
        
        try:
            user_message = ChatMessage.objects.get(id=chat_message_id)
            user_message.status = 'failed'
            user_message.error_message = str(e)
            user_message.save()
        except:
            pass
        
        raise self.retry(exc=e, countdown=30)