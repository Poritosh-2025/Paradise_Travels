"""
API Key management models.
"""
import uuid
from django.db import models
from django.conf import settings


class APIKey(models.Model):
    """
    API Key model for external integrations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key_name = models.CharField(max_length=255)
    api_key = models.CharField(max_length=255, unique=True)
    key_prefix = models.CharField(max_length=50)  # For display (masked version)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='api_keys_created'
    )
    
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'api_keys'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.key_name} - {self.key_prefix}"
