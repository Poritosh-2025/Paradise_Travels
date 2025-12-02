"""
Serializers for payment endpoints.
"""
from rest_framework import serializers
from .models import Payment


class PaymentListSerializer(serializers.ModelSerializer):
    """
    Serializer for payment list.
    """
    user_name = serializers.CharField(source='user.name')
    user_email = serializers.EmailField(source='user.email')
    pay_amount = serializers.SerializerMethodField()
    stripe_payment_id = serializers.CharField(source='stripe_payment_intent_id')

    class Meta:
        model = Payment
        fields = [
            'user_name', 'user_email', 'pay_amount',
            'payment_date', 'payment_status', 'stripe_payment_id'
        ]

    def get_pay_amount(self, obj):
        return {
            'amount': float(obj.amount),
            'currency': obj.currency
        }


class CreatePaymentIntentSerializer(serializers.Serializer):
    """
    Serializer for creating payment intent.
    """
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3, default='USD')
    subscription_plan = serializers.ChoiceField(choices=[
        'premium_monthly', 'premium_yearly', 'pro_monthly', 'pro_yearly'
    ])


class ConfirmPaymentSerializer(serializers.Serializer):
    """
    Serializer for confirming payment.
    """
    payment_intent_id = serializers.CharField()
    payment_method_id = serializers.CharField()
