"""
Admin configuration for payments.
"""
from django.contrib import admin
from .models import Subscription, Payment, UsageTracking, WebhookEvent, VideoPurchase


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan_type', 'status', 'current_period_end', 'cancel_at_period_end', 'created_at']
    list_filter = ['plan_type', 'status', 'cancel_at_period_end']
    search_fields = ['user__email', 'stripe_subscription_id']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'payment_type', 'amount', 'currency', 'status', 'created_at']
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