"""
Admin configuration for payments.
"""
from django.contrib import admin
from .models import Plan, Subscription, Payment, UsageTracking, WebhookEvent, VideoPurchase


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['plan_id', 'name', 'price', 'currency', 'videos_per_month', 'is_active', 'created_at']
    list_filter = ['is_active', 'billing_cycle']
    search_fields = ['plan_id', 'name']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'current_period_end', 'cancel_at_period_end', 'created_at']
    list_filter = ['status', 'cancel_at_period_end']
    search_fields = ['user__email', 'stripe_subscription_id']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'payment_type', 'amount', 'currency', 'status', 'payment_date', 'created_at']
    list_filter = ['payment_type', 'status', 'currency']
    search_fields = ['user__email', 'stripe_payment_intent_id']


@admin.register(UsageTracking)
class UsageTrackingAdmin(admin.ModelAdmin):
    list_display = ['user', 'itineraries_generated', 'videos_generated', 'videos_remaining', 'billing_period_end']
    search_fields = ['user__email']


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ['stripe_event_id', 'event_type', 'processing_status', 'created_at', 'processed_at']
    list_filter = ['event_type', 'processing_status']
    search_fields = ['stripe_event_id']


@admin.register(VideoPurchase)
class VideoPurchaseAdmin(admin.ModelAdmin):
    list_display = ['user', 'video_quality', 'amount_paid', 'generation_status', 'created_at']
    list_filter = ['video_quality', 'generation_status']
    search_fields = ['user__email']
    # update 15/01
    raw_id_fields = ['video_generation']
    
    def video_generation_id(self, obj):
        if obj.video_generation:
            return str(obj.video_generation.id)[:8] + '...'
        return '-'
    video_generation_id.short_description = 'Video Gen ID'
    # end of update 15/01