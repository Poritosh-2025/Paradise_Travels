"""
Serializers for payment and subscription endpoints.
"""
from rest_framework import serializers
from .models import Subscription, Payment, UsageTracking, VideoPurchase, WebhookEvent


class PlanSerializer(serializers.Serializer):
    """
    Serializer for subscription plans.
    """
    plan_id = serializers.CharField()
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    billing_cycle = serializers.CharField()
    stripe_price_id = serializers.CharField(required=False)
    features = serializers.DictField()


class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Serializer for subscription details.
    """
    subscription_id = serializers.UUIDField(source='id', read_only=True)

    class Meta:
        model = Subscription
        fields = [
            'subscription_id', 'stripe_subscription_id', 'plan_type',
            'status', 'current_period_start', 'current_period_end',
            'cancel_at_period_end', 'cancelled_at'
        ]


class CreateSubscriptionSerializer(serializers.Serializer):
    """
    Serializer for creating subscription.
    """
    plan_type = serializers.ChoiceField(choices=['premium', 'pro'])
    payment_method_id = serializers.CharField()


class UpgradeSubscriptionSerializer(serializers.Serializer):
    """
    Serializer for upgrading subscription.
    """
    new_plan_type = serializers.ChoiceField(choices=['pro'])


class DowngradeSubscriptionSerializer(serializers.Serializer):
    """
    Serializer for downgrading subscription.
    """
    new_plan_type = serializers.ChoiceField(choices=['basic', 'premium'])


class CancelSubscriptionSerializer(serializers.Serializer):
    """
    Serializer for cancelling subscription.
    """
    cancellation_reason = serializers.CharField(required=False, allow_blank=True)
    feedback = serializers.CharField(required=False, allow_blank=True)


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for payment records.
    """
    payment_id = serializers.UUIDField(source='id', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'payment_id', 'payment_type', 'amount', 'currency',
            'status', 'description', 'receipt_url', 'created_at'
        ]


class AddPaymentMethodSerializer(serializers.Serializer):
    """
    Serializer for adding payment method.
    """
    payment_method_id = serializers.CharField()
    set_as_default = serializers.BooleanField(default=True)


class VideoPurchaseSerializer(serializers.Serializer):
    """
    Serializer for video purchase.
    """
    payment_method_id = serializers.CharField()
    video_quality = serializers.ChoiceField(choices=['standard', 'high'], default='standard')


class UsageSerializer(serializers.ModelSerializer):
    """
    Serializer for usage tracking.
    """
    class Meta:
        model = UsageTracking
        fields = [
            'billing_period_start', 'billing_period_end',
            'itineraries_generated', 'videos_generated',
            'videos_remaining', 'chatbot_queries'
        ]


class WebhookEventSerializer(serializers.ModelSerializer):
    """
    Serializer for webhook events (admin).
    """
    event_id = serializers.UUIDField(source='id', read_only=True)

    class Meta:
        model = WebhookEvent
        fields = [
            'event_id', 'stripe_event_id', 'event_type',
            'processing_status', 'created_at', 'processed_at'
        ]