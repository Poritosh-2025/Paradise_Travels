"""
Usage Service

Handles subscription plan limits and usage tracking.
Integrates with payments app to enforce plan restrictions.

Plan Details:
    Basic (Free):
        - 1 itinerary per month
        - 0 free videos (€5.99 per video, UNLIMITED paid videos allowed)
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
import logging
from typing import Dict, Any, Tuple
from django.utils import timezone
from django.db.models import Count

logger = logging.getLogger(__name__)


class UsageService:
    """
    Service for checking and tracking usage against subscription plans.
    """
    
    # Plan configuration
    PLAN_LIMITS = {
        'basic': {
            'itineraries_per_month': 1,
            'videos_per_month': 0,  # 0 free videos, but unlimited PAID videos
            'video_quality': 'standard',
        },
        'premium': {
            'itineraries_per_month': float('inf'),  # Unlimited
            'videos_per_month': 3,
            'video_quality': 'standard',
        },
        'pro': {
            'itineraries_per_month': float('inf'),  # Unlimited
            'videos_per_month': 5,
            'video_quality': 'high',
        }
    }
    
    VIDEO_PRICE = 5.99  # EUR per video when payment required
    
    def get_user_plan(self, user) -> str:
        """
        Get user's current subscription plan.
        
        Args:
            user: User model instance
            
        Returns:
            Plan type: 'basic', 'premium', or 'pro'
        """
        try:
            subscription = user.subscription    # from payments app
            if subscription and subscription.plan and subscription.status == 'active':
                return subscription.plan.plan_id
        except Exception:
            pass
        
        return 'basic'
    
    def get_billing_period(self, user) -> Tuple[timezone.datetime, timezone.datetime]:
        """
        Get user's current billing period.
        
        For basic users, use calendar month.
        For subscribers, use subscription period.
        
        Args:
            user: User model instance
            
        Returns:
            Tuple of (period_start, period_end)
        """
        try:
            subscription = user.subscription
            if subscription and subscription.current_period_start and subscription.current_period_end:
                return subscription.current_period_start, subscription.current_period_end
        except Exception:
            pass
        
        # Fallback: Use calendar month
        now = timezone.now()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get first day of next month
        if now.month == 12:
            period_end = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            period_end = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return period_start, period_end
    
    def get_itinerary_usage(self, user) -> Dict[str, Any]:
        """
        Get user's itinerary usage for current billing period.
        
        Args:
            user: User model instance
            
        Returns:
            Dict with usage info
        """
        from .models import Itinerary
        
        plan = self.get_user_plan(user)
        plan_limits = self.PLAN_LIMITS.get(plan, self.PLAN_LIMITS['basic'])
        period_start, period_end = self.get_billing_period(user)
        
        # Count itineraries in current period
        itineraries_count = Itinerary.objects.filter(
            user=user,
            created_at__gte=period_start,
            created_at__lt=period_end,
            status='completed'
        ).count()
        
        limit = plan_limits['itineraries_per_month']
        
        return {
            'used': itineraries_count,
            'limit': limit if limit != float('inf') else 'unlimited',
            'remaining': (limit - itineraries_count) if limit != float('inf') else 'unlimited',
            'can_create': limit == float('inf') or itineraries_count < limit,
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat(),
            'plan': plan
        }
    
    def get_video_usage(self, user) -> Dict[str, Any]:
        """
        Get user's video usage for current billing period.
        
        Args:
            user: User model instance
            
        Returns:
            Dict with usage info
        """
        from .models import VideoGeneration
        
        plan = self.get_user_plan(user)
        plan_limits = self.PLAN_LIMITS.get(plan, self.PLAN_LIMITS['basic'])
        period_start, period_end = self.get_billing_period(user)
        
        # Count free videos used (is_free_quota=True)
        free_videos_used = VideoGeneration.objects.filter(
            user=user,
            created_at__gte=period_start,
            created_at__lt=period_end,
            is_free_quota=True,
            status__in=['completed', 'processing', 'pending', 'generating']
        ).count()
        
        # Count paid videos
        paid_videos = VideoGeneration.objects.filter(
            user=user,
            created_at__gte=period_start,
            created_at__lt=period_end,
            is_paid=True
        ).count()
        
        # Total videos (all time for this user)
        total_videos_all_time = VideoGeneration.objects.filter(
            user=user,
            status__in=['completed', 'processing', 'pending', 'generating']
        ).count()
        
        free_limit = plan_limits['videos_per_month']
        free_remaining = max(0, free_limit - free_videos_used)
        
        return {
            'free_used': free_videos_used,
            'free_limit': free_limit,
            'free_remaining': free_remaining,
            'paid_videos': paid_videos,
            'total_videos_this_period': free_videos_used + paid_videos,
            'total_videos_all_time': total_videos_all_time,
            'can_use_free': free_remaining > 0,
            'requires_payment': free_remaining <= 0,
            'video_price': self.VIDEO_PRICE,
            'video_quality': plan_limits['video_quality'],
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat(),
            'plan': plan
        }
    
    def can_create_itinerary(self, user) -> Tuple[bool, str]:
        """
        Check if user can create a new itinerary.
        
        Args:
            user: User model instance
            
        Returns:
            Tuple of (can_create, message)
        """
        usage = self.get_itinerary_usage(user)
        
        if usage['can_create']:
            return True, "OK"
        else:
            return False, f"Monthly itinerary limit reached ({usage['used']}/{usage['limit']}). Upgrade to Premium for unlimited itineraries."
    
    def can_generate_video(self, user) -> Tuple[bool, bool, str]:
        """
        Check if user can generate a video.
        
        Basic Plan Logic:
        - 0 free videos
        - UNLIMITED paid videos (€5.99 each)
        - Always returns (True, True, message) for basic users
        
        Premium Plan Logic:
        - 3 free videos per month
        - After quota exhausted: €5.99 per video (UNLIMITED)
        
        Pro Plan Logic:
        - 5 free videos per month
        - High quality video access
        - After quota exhausted: €5.99 per video (UNLIMITED)
        
        Args:
            user: User model instance
            
        Returns:
            Tuple of (can_generate, requires_payment, message)
        """
        usage = self.get_video_usage(user)
        plan = usage['plan']


        if usage['can_use_free']:
            # Has free quota remaining
            return True, False, f"Using free video quota ({usage['free_used']}/{usage['free_limit']})"
        else:
            # No free quota - requires payment
            # ALL plans can generate UNLIMITED paid videos
            if plan == 'basic':
                return True, True, f"Video generation costs €{self.VIDEO_PRICE}. You can generate unlimited videos with payment."
            else:
                return True, True, f"Free video quota exhausted ({usage['free_used']}/{usage['free_limit']}). Additional videos cost €{self.VIDEO_PRICE} each (unlimited)."
    
    def record_itinerary_usage(self, user, itinerary) -> None:
        """
        Record itinerary creation in usage tracking.
        
        Args:
            user: User model instance
            itinerary: Itinerary model instance
        """
        # Update UsageTracking if exists
        try:
            from payments.models import UsageTracking
            
            usage_record = UsageTracking.objects.filter(user=user).order_by('-created_at').first()
            if usage_record:
                usage_record.itineraries_generated += 1
                usage_record.save()
                logger.info(f"📊 Updated usage: {user.email} itineraries={usage_record.itineraries_generated}")
        except Exception as e:
            logger.warning(f"⚠️ Could not update usage tracking: {e}")
    
    def record_video_usage(self, user, video, is_free: bool = False) -> None:
        """
        Record video generation in usage tracking.
        
        Args:
            user: User model instance
            video: VideoGeneration model instance
            is_free: Whether this used free quota
        """
        # Update UsageTracking if exists
        try:
            from payments.models import UsageTracking
            
            usage_record = UsageTracking.objects.filter(user=user).order_by('-created_at').first()
            if usage_record:
                usage_record.videos_generated += 1
                if is_free and usage_record.videos_remaining > 0:
                    usage_record.videos_remaining -= 1
                usage_record.save()
                logger.info(f"📊 Updated usage: {user.email} videos={usage_record.videos_generated}")
        except Exception as e:
            logger.warning(f"⚠️ Could not update usage tracking: {e}")
    
    def get_full_usage_summary(self, user) -> Dict[str, Any]:
        """
        Get complete usage summary for user dashboard.
        
        Args:
            user: User model instance
            
        Returns:
            Dict with complete usage information
        """
        itinerary_usage = self.get_itinerary_usage(user)
        video_usage = self.get_video_usage(user)
        plan = self.get_user_plan(user)
        
        return {
            'plan': plan,
            'itineraries': itinerary_usage,
            'videos': video_usage,
            'features': {
                # FREE for ALL plans (including Basic)
                'chatbot_access': True,
                'customization': True,
                'social_sharing': True,
                # Pro plan exclusive features
                'exclusive_deals': plan == 'pro',
                'priority_support': plan == 'pro',
                'high_quality_video': plan == 'pro'
            }
        }


# Singleton instance
usage_service = UsageService()