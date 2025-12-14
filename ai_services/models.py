"""
Models for AI Services - Itinerary and Video tracking.
Integrates with FastAPI AI service while enforcing subscription limits.
"""
import uuid
from django.db import models
from django.conf import settings


class Itinerary(models.Model):
    """
    Track user itineraries created via AI service.
    Used for enforcing plan limits and usage tracking.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='itineraries'
    )
    
    # FastAPI reference
    fastapi_itinerary_id = models.CharField(max_length=255, unique=True)
    
    # Itinerary details
    destination = models.CharField(max_length=255)
    destination_country = models.CharField(max_length=255, blank=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField()  # Days
    travelers = models.IntegerField()
    activity_preference = models.CharField(max_length=50)  # relaxed, moderate, high
    include_flights = models.BooleanField(default=False)
    include_hotels = models.BooleanField(default=False)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Store the full itinerary data as JSON
    itinerary_data = models.JSONField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'itineraries'
        ordering = ['-created_at']
        verbose_name_plural = 'Itineraries'

    def __str__(self):
        return f"{self.user.email} - {self.destination} ({self.duration} days)"


class UserPhoto(models.Model):
    """
    Track uploaded user photos for video generation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    
    # FastAPI reference
    fastapi_filename = models.CharField(max_length=255)
    fastapi_url = models.CharField(max_length=500)
    
    # Original filename
    original_filename = models.CharField(max_length=255)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_photos'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.original_filename}"


class VideoGeneration(models.Model):
    """
    Track video generation requests.
    Used for enforcing plan limits and tracking video usage.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    QUALITY_CHOICES = [
        ('standard', 'Standard'),
        ('high', 'High'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='video_generations'
    )
    itinerary = models.ForeignKey(
        Itinerary,
        on_delete=models.CASCADE,
        related_name='videos'
    )
    
    # FastAPI reference
    fastapi_video_id = models.CharField(max_length=255, unique=True)
    
    # Video details
    quality = models.CharField(max_length=20, choices=QUALITY_CHOICES, default='standard')
    user_photo = models.ForeignKey(
        UserPhoto,
        on_delete=models.SET_NULL,
        null=True,
        related_name='videos'
    )
    
    # Status and progress
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.IntegerField(default=0)  # 0-100
    current_day = models.IntegerField(default=0)
    total_days = models.IntegerField(default=0)
    current_stage = models.CharField(max_length=255, blank=True)
    
    # Result
    video_url = models.URLField(max_length=500, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Payment tracking (for Basic plan users)
    is_paid = models.BooleanField(default=False)
    is_free_quota = models.BooleanField(default=False)  # Used free monthly quota
    payment = models.ForeignKey(
        'payments.Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='video_generations'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'video_generations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.itinerary.destination} video"


class ChatMessage(models.Model):
    """
    Track chat messages for itinerary modifications.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    itinerary = models.ForeignKey(
        Itinerary,
        on_delete=models.CASCADE,
        related_name='chat_messages'
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    message = models.TextField()
    
    # If modifications were made
    modifications_made = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.message[:50]}..."
