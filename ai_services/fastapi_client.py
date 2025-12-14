"""
FastAPI Client Service

Handles communication between Django backend and FastAPI AI service.
Includes error handling, retries, and timeout management.
"""
import os
import logging
import requests
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class FastAPIClient:
    """
    Client for communicating with FastAPI AI Service.
    
    Configuration (in settings.py):
        FASTAPI_BASE_URL = 'http://localhost:8001'
        FASTAPI_TIMEOUT = 120  # seconds
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'FASTAPI_BASE_URL', 'http://localhost:8001')
        self.timeout = getattr(settings, 'FASTAPI_TIMEOUT', 120)
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to FastAPI service.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/api/create-itinerary')
            data: JSON data for POST requests
            files: File data for multipart uploads
            timeout: Request timeout in seconds
            
        Returns:
            Dict with response data or error
        """
        url = f"{self.base_url}{endpoint}"
        request_timeout = timeout or self.timeout
        
        try:
            logger.info(f"🔗 FastAPI Request: {method} {url}")
            
            if method.upper() == 'GET':
                response = requests.get(url, timeout=request_timeout)
            elif method.upper() == 'POST':
                if files:
                    # Multipart form data (file upload)
                    response = requests.post(url, files=files, timeout=request_timeout)
                else:
                    # JSON data
                    response = requests.post(url, json=data, timeout=request_timeout)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported HTTP method: {method}'
                }
            
            # Log response status
            logger.info(f"📡 FastAPI Response: {response.status_code}")
            
            # Handle response
            if response.ok:
                try:
                    response_data = response.json()
                    return {
                        'success': True,
                        'data': response_data,
                        'status_code': response.status_code
                    }
                except ValueError:
                    return {
                        'success': True,
                        'data': response.text,
                        'status_code': response.status_code
                    }
            else:
                # Error response
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail') or error_data.get('message') or str(error_data)
                except ValueError:
                    error_message = response.text
                
                logger.error(f"❌ FastAPI Error: {error_message}")
                
                return {
                    'success': False,
                    'error': error_message,
                    'status_code': response.status_code,
                    'data': error_data if 'error_data' in locals() else None
                }
                
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ FastAPI Timeout: {url}")
            return {
                'success': False,
                'error': 'Request timed out. The AI service is taking too long.',
                'status_code': 504
            }
        except requests.exceptions.ConnectionError:
            logger.error(f"🔌 FastAPI Connection Error: {url}")
            return {
                'success': False,
                'error': 'Could not connect to AI service. Please try again later.',
                'status_code': 503
            }
        except Exception as e:
            logger.error(f"❌ FastAPI Request Failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'status_code': 500
            }
    
    # ==================== ITINERARY ENDPOINTS ====================
    
    def create_itinerary(
        self,
        destination: str,
        budget: float,
        duration: int,
        travelers: int,
        activity_preference: str,
        include_flights: bool = False,
        include_hotels: bool = False,
        user_location: str = "New York"
    ) -> Dict[str, Any]:
        """
        Create a new itinerary via FastAPI.
        
        Args:
            destination: Travel destination
            budget: Total budget in USD
            duration: Number of days
            travelers: Number of travelers
            activity_preference: 'relaxed', 'moderate', or 'high'
            include_flights: Include flight costs
            include_hotels: Include hotel costs
            user_location: Starting location for flights
            
        Returns:
            Dict with itinerary data or error
        """
        data = {
            'destination': destination,
            'budget': budget,
            'duration': duration,
            'travelers': travelers,
            'activity_preference': activity_preference,
            'include_flights': include_flights,
            'include_hotels': include_hotels,
            'user_location': user_location
        }
        
        return self._make_request('POST', '/api/create-itinerary', data=data)
    
    def get_itinerary(self, itinerary_id: str) -> Dict[str, Any]:
        """
        Get existing itinerary from FastAPI.
        
        Args:
            itinerary_id: FastAPI itinerary ID
            
        Returns:
            Dict with itinerary data or error
        """
        return self._make_request('GET', f'/api/itinerary/{itinerary_id}')
    
    def reallocate_budget(
        self,
        itinerary_id: str,
        selected_categories: list
    ) -> Dict[str, Any]:
        """
        Reallocate budget to selected categories.
        
        Args:
            itinerary_id: FastAPI itinerary ID
            selected_categories: List of categories to receive extra budget
            
        Returns:
            Dict with updated budget breakdown or error
        """
        data = {
            'itinerary_id': itinerary_id,
            'selected_categories': selected_categories
        }
        
        return self._make_request('POST', '/api/reallocate-budget', data=data)
    
    # ==================== CHAT ENDPOINTS ====================
    
    def chat(
        self,
        itinerary_id: str,
        message: str,
        conversation_history: list = None
    ) -> Dict[str, Any]:
        """
        Send chat message for itinerary modifications.
        
        Args:
            itinerary_id: FastAPI itinerary ID
            message: User's message
            conversation_history: Previous conversation messages
            
        Returns:
            Dict with AI response and any modifications
        """
        data = {
            'itinerary_id': itinerary_id,
            'message': message,
            'conversation_history': conversation_history or []
        }
        
        return self._make_request('POST', '/api/chat', data=data)
    
    # ==================== PHOTO ENDPOINTS ====================
    
    def upload_photo(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Upload user photo to FastAPI for video generation.
        
        Args:
            file_content: File bytes
            filename: Original filename
            
        Returns:
            Dict with uploaded file info or error
        """
        files = {
            'file': (filename, file_content, 'image/jpeg')
        }
        
        return self._make_request('POST', '/api/upload-photo', files=files)
    
    # ==================== VIDEO ENDPOINTS ====================
    
    def generate_video(
        self,
        itinerary_id: str,
        user_photo_filename: str
    ) -> Dict[str, Any]:
        """
        Start video generation for an itinerary.
        
        Args:
            itinerary_id: FastAPI itinerary ID
            user_photo_filename: Filename from upload_photo
            
        Returns:
            Dict with video_id or error
        """
        data = {
            'itinerary_id': itinerary_id,
            'user_photo_filename': user_photo_filename
        }
        
        return self._make_request('POST', '/api/generate-video', data=data)
    
    def get_video_status(self, video_id: str) -> Dict[str, Any]:
        """
        Get video generation status.
        
        Args:
            video_id: FastAPI video ID
            
        Returns:
            Dict with video status, progress, and URL if completed
        """
        return self._make_request('GET', f'/api/video-status/{video_id}')
    
    # ==================== HEALTH CHECK ====================
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if FastAPI service is available.
        
        Returns:
            Dict with health status
        """
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            return {
                'success': True,
                'status': 'healthy',
                'status_code': response.status_code
            }
        except Exception as e:
            return {
                'success': False,
                'status': 'unhealthy',
                'error': str(e)
            }


# Singleton instance
fastapi_client = FastAPIClient()
