"""
URL patterns for API management endpoints.
"""
from django.urls import path
from .views import ViewAPIKeyView, UpdateAPIKeyView, DeleteAPIKeyView

urlpatterns = [
    path('key/', ViewAPIKeyView.as_view(), name='view-api-key'),
    path('key/update/', UpdateAPIKeyView.as_view(), name='update-api-key'),
    path('key/<uuid:key_id>/', DeleteAPIKeyView.as_view(), name='delete-api-key'),
]
