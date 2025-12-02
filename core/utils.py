"""
Utility functions used across the project.
"""
import random
import string
import uuid
from django.utils import timezone
from datetime import timedelta


def generate_otp(length=6):
    """
    Generate a random numeric OTP.
    """
    return ''.join(random.choices(string.digits, k=length))


def get_otp_expiry(minutes=10):
    """
    Get OTP expiry datetime.
    """
    return timezone.now() + timedelta(minutes=minutes)


def generate_uuid():
    """
    Generate a unique UUID string.
    """
    return str(uuid.uuid4())


def generate_api_key(prefix='sk_live_'):
    """
    Generate an API key with prefix.
    """
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    return f"{prefix}{random_part}"


def mask_api_key(api_key, visible_chars=4):
    """
    Mask API key showing only prefix and last few characters.
    """
    if len(api_key) <= visible_chars:
        return api_key
    return api_key[:visible_chars] + '****'


def get_admin_info(user):
    """
    Get admin info dictionary for API responses.
    """
    profile_url = None
    if user.profile_picture:
        profile_url = user.profile_picture.url
    
    return {
        'name': user.name or user.email,
        'profile_picture': profile_url,
        'role': user.role,
    }
