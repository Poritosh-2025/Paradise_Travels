"""
Serializers for payment and subscription endpoints.
"""
from rest_framework import serializers
from .models import Plan, Subscription, Payment, UsageTracking, VideoPurchase, WebhookEvent


class PlanSerializer(serializers.ModelSerializer):
    """
    Serializer for plan details.
    """
    features = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            'plan_id', 'name', 'price', 'currency', 'billing_cycle',
            'stripe_price_id', 'features'
        ]

    def get_features(self, obj):
        return obj.get_features()


class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Serializer for subscription details.
    """
    subscription_id = serializers.UUIDField(source='id', read_only=True)
    plan_type = serializers.CharField(source='plan.plan_id', read_only=True)

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


class AdminTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for admin transaction list.
    """
    user_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.email')
    pay_amount = serializers.SerializerMethodField()
    payment_status = serializers.CharField(source='status')
    stripe_payment_id = serializers.CharField(source='stripe_payment_intent_id')

    class Meta:
        model = Payment
        fields = [
            'user_name', 'user_email', 'pay_amount',
            'payment_date', 'payment_status', 'stripe_payment_id'
        ]

    def get_user_name(self, obj):
        return obj.user.name or obj.user.email

    def get_pay_amount(self, obj):
        return {
            'amount': float(obj.amount),
            'currency': obj.currency
        }


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