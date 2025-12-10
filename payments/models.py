"""
Payment and Subscription models.
"""
import uuid
from django.db import models
from django.conf import settings


class Subscription(models.Model):
    """
    User subscription management.
    """
    PLAN_CHOICES = [
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('pro', 'Pro'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('past_due', 'Past Due'),
        ('unpaid', 'Unpaid'),
        ('trialing', 'Trialing'),
    ]
    
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    stripe_price_id = models.CharField(max_length=255, blank=True)
    
    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES, default='basic')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly')
    
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    
    cancel_at_period_end = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscriptions'

    def __str__(self):
        return f"{self.user.email} - {self.plan_type}"


class Payment(models.Model):
    """
    Payment transaction records.
    """
    PAYMENT_TYPE_CHOICES = [
        ('subscription', 'Subscription'),
        ('video_generation', 'Video Generation'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, unique=True, null=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='subscription')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='EUR')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    receipt_url = models.URLField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.amount} {self.currency}"


class UsageTracking(models.Model):
    """
    Track user feature usage per billing period.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='usage_records'
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='usage_records'
    )
    
    billing_period_start = models.DateTimeField()
    billing_period_end = models.DateTimeField()
    
    itineraries_generated = models.IntegerField(default=0)
    videos_generated = models.IntegerField(default=0)
    videos_remaining = models.IntegerField(default=0)
    chatbot_queries = models.IntegerField(default=0)
    
    last_reset_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'usage_tracking'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.billing_period_start}"


class WebhookEvent(models.Model):
    """
    Store Stripe webhook events for audit.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
        ('ignored', 'Ignored'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=255, db_index=True)
    event_data = models.JSONField()
    
    processing_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.IntegerField(default=0)
    
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webhook_events'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} - {self.stripe_event_id}"


class VideoPurchase(models.Model):
    """
    Track individual video purchases.
    """
    QUALITY_CHOICES = [
        ('standard', 'Standard'),
        ('high', 'High'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='video_purchases'
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        related_name='video_purchases'
    )
    
    video_quality = models.CharField(max_length=20, choices=QUALITY_CHOICES, default='standard')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    generation_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    video_url = models.URLField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'video_purchases'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.video_quality}"