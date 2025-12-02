"""
Payment models.
"""
import uuid
from django.db import models
from django.conf import settings


class Payment(models.Model):
    """
    Payment transaction model.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    SUBSCRIPTION_PLAN_CHOICES = [
        ('premium_monthly', 'Premium Monthly'),
        ('premium_yearly', 'Premium Yearly'),
        ('pro_monthly', 'Pro Monthly'),
        ('pro_yearly', 'Pro Yearly'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    subscription_plan = models.CharField(max_length=50, choices=SUBSCRIPTION_PLAN_CHOICES)
    
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    stripe_payment_method_id = models.CharField(max_length=255, blank=True)
    
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.amount} {self.currency}"
