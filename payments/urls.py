"""
URL patterns for payment and subscription endpoints.
"""
from django.urls import path
from .views import (
    # Subscription
    PlansListView, CreateSubscriptionView, CurrentSubscriptionView,
    UpgradeSubscriptionView, DowngradeSubscriptionView,
    CancelSubscriptionView, ReactivateSubscriptionView,
    # Payment
    SetupIntentView, PaymentMethodsView, AddPaymentMethodView,
    DeletePaymentMethodView, VideoPurchaseView, PaymentHistoryView,
    # Usage
    CurrentUsageView, UsageHistoryView,
    # Webhook
    StripeWebhookView,
    # Admin
    AdminTransactionsView, AdminSubscriptionsView, AdminWebhookEventsView
)

urlpatterns = [
    # Subscription endpoints
    path('subscriptions/plans/', PlansListView.as_view(), name='plans-list'),
    path('subscriptions/create/', CreateSubscriptionView.as_view(), name='create-subscription'),
    path('subscriptions/current/', CurrentSubscriptionView.as_view(), name='current-subscription'),
    path('subscriptions/upgrade/', UpgradeSubscriptionView.as_view(), name='upgrade-subscription'),
    path('subscriptions/downgrade/', DowngradeSubscriptionView.as_view(), name='downgrade-subscription'),
    path('subscriptions/cancel/', CancelSubscriptionView.as_view(), name='cancel-subscription'),
    path('subscriptions/reactivate/', ReactivateSubscriptionView.as_view(), name='reactivate-subscription'),
    
    # Payment endpoints
    path('setup-intent/', SetupIntentView.as_view(), name='setup-intent'),
    path('methods/', PaymentMethodsView.as_view(), name='payment-methods'),
    path('methods/add/', AddPaymentMethodView.as_view(), name='add-payment-method'),
    path('methods/<str:payment_method_id>/', DeletePaymentMethodView.as_view(), name='delete-payment-method'),
    path('video-purchase/', VideoPurchaseView.as_view(), name='video-purchase'),
    path('history/', PaymentHistoryView.as_view(), name='payment-history'),
    
    # Usage endpoints
    path('usage/current/', CurrentUsageView.as_view(), name='current-usage'),
    path('usage/history/', UsageHistoryView.as_view(), name='usage-history'),
    
    # Webhook
    path('webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    
    # Admin endpoints
    path('admin/transactions/', AdminTransactionsView.as_view(), name='admin-transactions'),
    path('admin/subscriptions/', AdminSubscriptionsView.as_view(), name='admin-subscriptions'),
    path('admin/webhooks/events/', AdminWebhookEventsView.as_view(), name='admin-webhook-events'),
]