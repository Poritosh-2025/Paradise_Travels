"""
URL patterns for payment and subscription endpoints.
Stripe Checkout Session integration.
"""
from django.urls import path
from .views import (
    # Plans
    PlansListView,
    # Checkout Sessions
    CreateCheckoutSessionView,
    CreateVideoCheckoutSessionView,
    CheckoutSuccessView,
    # Subscription Management
    CurrentSubscriptionView,
    CancelSubscriptionView,
    ReactivateSubscriptionView,
    CreateBillingPortalView,
    # Usage & History
    CurrentUsageView,
    PaymentHistoryView,
    # Webhook
    StripeWebhookView,
    # Admin
    AdminTransactionsView,
    AdminSubscriptionsView,
)

urlpatterns = [
    # Plans
    path('subscriptions/plans/', PlansListView.as_view(), name='plans-list'),
    
    # Checkout Sessions (Stripe handles payment UI)
    path('checkout/subscription/', CreateCheckoutSessionView.as_view(), name='checkout-subscription'),
    path('checkout/video/', CreateVideoCheckoutSessionView.as_view(), name='checkout-video'),
    path('checkout/success/', CheckoutSuccessView.as_view(), name='checkout-success'),
    
    # Subscription Management
    path('subscriptions/current/', CurrentSubscriptionView.as_view(), name='current-subscription'),
    path('subscriptions/cancel/', CancelSubscriptionView.as_view(), name='cancel-subscription'),
    path('subscriptions/reactivate/', ReactivateSubscriptionView.as_view(), name='reactivate-subscription'),
    
    # Billing Portal (Stripe handles UI for managing payment methods, invoices)
    path('billing-portal/', CreateBillingPortalView.as_view(), name='billing-portal'),
    
    # Usage & History
    path('usage/current/', CurrentUsageView.as_view(), name='current-usage'),
    path('history/', PaymentHistoryView.as_view(), name='payment-history'),
    
    # Webhook
    path('webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    
    # Admin
    path('admin/transactions/', AdminTransactionsView.as_view(), name='admin-transactions'),
    path('admin/subscriptions/', AdminSubscriptionsView.as_view(), name='admin-subscriptions'),
]