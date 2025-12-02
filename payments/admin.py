"""
Admin configuration for payments.
"""
from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'currency', 'subscription_plan', 'payment_status', 'payment_date', 'created_at']
    list_filter = ['payment_status', 'subscription_plan', 'currency']
    search_fields = ['user__email', 'stripe_payment_intent_id']
    ordering = ['-created_at']
