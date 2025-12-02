"""
User Management models.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class UserDeletionRequest(models.Model):
    """
    Model to track user deletion requests.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='deletion_requests_made'
    )
    deletion_token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    is_confirmed = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_deletion_requests'

    def is_valid(self):
        return (
            not self.is_confirmed and 
            not self.is_cancelled and 
            self.expires_at > timezone.now()
        )

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
