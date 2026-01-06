"""
Serializers for AI Services

Handles validation and serialization for itinerary and video endpoints.
"""
from rest_framework import serializers
from .models import Itinerary, UserPhoto, VideoGeneration, ChatMessage


class CreateItinerarySerializer(serializers.Serializer):
    """Serializer for creating a new itinerary"""
    
    ACTIVITY_CHOICES = [
        ('relaxed', 'Relaxed'),
        ('moderate', 'Moderate'),
        ('high', 'High'),
    ]
    
    destination = serializers.CharField(
        max_length=255,
        help_text="Destination city, country, or any location description"
    )
    budget = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=100,
        help_text="Total budget in USD (minimum $100)"
    )
    duration = serializers.IntegerField(
        min_value=1,
        max_value=30,
        help_text="Trip duration in days (1-30)"
    )
    travelers = serializers.IntegerField(
        min_value=1,
        max_value=20,
        help_text="Number of travelers (1-20)"
    )
    activity_preference = serializers.ChoiceField(
        choices=ACTIVITY_CHOICES,
        help_text="Activity level: relaxed, moderate, or high"
    )
    include_flights = serializers.BooleanField(
        default=False,
        help_text="Include flight costs in budget"
    )
    include_hotels = serializers.BooleanField(
        default=False,
        help_text="Include hotel costs in budget"
    )
    user_location = serializers.CharField(
        max_length=255,
        required=False,
        default="New York",
        help_text="Starting location for flight calculations"
    )


class ItinerarySerializer(serializers.ModelSerializer):
    """Serializer for Itinerary model"""
    
    class Meta:
        model = Itinerary
        fields = [
            'id',
            'fastapi_itinerary_id',
            'destination',
            'destination_country',
            'budget',
            'duration',
            'travelers',
            'activity_preference',
            'include_flights',
            'include_hotels',
            'status',
            'itinerary_data',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'fastapi_itinerary_id', 'status', 'created_at', 'updated_at']


class ItineraryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing itineraries"""
    
    class Meta:
        model = Itinerary
        fields = [
            'id',
            'fastapi_itinerary_id',
            'destination',
            'destination_country',
            'budget',
            'duration',
            'travelers',
            'status',
            'created_at',
        ]


class ReallocateBudgetSerializer(serializers.Serializer):
    """Serializer for budget reallocation"""
    
    CATEGORY_CHOICES = [
        ('flights', 'Flights'),
        ('hotels', 'Hotels'),
        ('food', 'Food'),
        ('travel', 'Travel'),
        ('activities', 'Activities'),
    ]
    
    itinerary_id = serializers.UUIDField(
        help_text="ID of the itinerary"
    )
    selected_categories = serializers.ListField(
        child=serializers.ChoiceField(choices=CATEGORY_CHOICES),
        min_length=1,
        help_text="Categories to receive extra budget"
    )


class ChatMessageSerializer(serializers.Serializer):
    """Serializer for chat messages"""
    
    itinerary_id = serializers.UUIDField(
        help_text="ID of the itinerary"
    )
    message = serializers.CharField(
        max_length=2000,
        help_text="User's message"
    )


class ChatMessageModelSerializer(serializers.ModelSerializer):
    """Serializer for ChatMessage model"""
    
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'message', 'modifications_made', 'created_at']


class ChatHistorySerializer(serializers.Serializer):
    """Serializer for chat history"""
    
    role = serializers.ChoiceField(choices=['user', 'assistant'])
    content = serializers.CharField()


class UserPhotoSerializer(serializers.ModelSerializer):
    """Serializer for UserPhoto model"""
    
    class Meta:
        model = UserPhoto
        fields = [
            'id',
            'fastapi_filename',
            'fastapi_url',
            'original_filename',
            'created_at',
        ]
        read_only_fields = ['id', 'fastapi_filename', 'fastapi_url', 'created_at']


class GenerateVideoSerializer(serializers.Serializer):
    """
    Serializer for video generation request.
    
    IMPORTANT: itinerary_id is REQUIRED for video generation.
    
    Flow:
    1. Create an itinerary first
    2. Upload a photo
    3. Generate video with itinerary_id + photo_id
    4. For Basic plan users: payment_session_id is required
    """
    
    QUALITY_CHOICES = [
        ('standard', 'Standard'),
        ('high', 'High'),
    ]
    
    # itinerary_id is REQUIRED
    itinerary_id = serializers.UUIDField(
        required=True,
        help_text="ID of the itinerary (REQUIRED)"
    )
    photo_id = serializers.UUIDField(
        required=True,
        help_text="ID of the uploaded user photo (REQUIRED)"
    )
    quality = serializers.ChoiceField(
        choices=QUALITY_CHOICES,
        required=False,
        default='standard',
        help_text="Video quality (high only available for Pro plan)"
    )
    # Payment session ID for paid video generation
    payment_session_id = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Stripe payment session ID (required for Basic plan users or when free quota exhausted)"
    )


class VideoGenerationSerializer(serializers.ModelSerializer):
    """Serializer for VideoGeneration model"""
    
    itinerary_destination = serializers.CharField(
        source='itinerary.destination',
        read_only=True
    )
    
    class Meta:
        model = VideoGeneration
        fields = [
            'id',
            'fastapi_video_id',
            'itinerary',
            'itinerary_destination',
            'quality',
            'status',
            'progress',
            'current_day',
            'total_days',
            'current_stage',
            'video_url',
            'error_message',
            'is_paid',
            'is_free_quota',
            'created_at',
            'updated_at',
            'completed_at',
        ]
        read_only_fields = [
            'id', 'fastapi_video_id', 'status', 'progress',
            'current_day', 'total_days', 'current_stage',
            'video_url', 'error_message', 'created_at', 'updated_at', 'completed_at'
        ]


class VideoGenerationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing video generations"""
    
    itinerary_destination = serializers.CharField(
        source='itinerary.destination',
        read_only=True
    )
    
    class Meta:
        model = VideoGeneration
        fields = [
            'id',
            'fastapi_video_id',
            'itinerary_destination',
            'quality',
            'status',
            'progress',
            'video_url',
            'is_paid',
            'is_free_quota',
            'created_at',
        ]
    
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['video_url'] = f"https://paradiseai.dsrt321.online{instance.video_url}" if instance.video_url else None
        return ret


class UsageSerializer(serializers.Serializer):
    """Serializer for usage information"""
    
    plan = serializers.CharField()
    itineraries = serializers.DictField()
    videos = serializers.DictField()
    features = serializers.DictField()