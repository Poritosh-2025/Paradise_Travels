"""
URL patterns for payment endpoints.
"""
from django.urls import path
from .views import (
    PaymentListView, CreatePaymentIntentView,
    ConfirmPaymentView, StripeWebhookView
)

urlpatterns = [
    path('transactions/', PaymentListView.as_view(), name='payment-list'),
    path('create-intent/', CreatePaymentIntentView.as_view(), name='create-payment-intent'),
    path('confirm/', ConfirmPaymentView.as_view(), name='confirm-payment'),
    path('webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
]
