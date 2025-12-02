"""
URL patterns for user management endpoints.
"""
from django.urls import path
from .views import (
    UserListView, DisableUserView, EnableUserView,
    DeleteUserRequestView, ConfirmDeleteUserView, CancelDeleteUserView
)

urlpatterns = [
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<uuid:user_id>/disable/', DisableUserView.as_view(), name='disable-user'),
    path('users/<uuid:user_id>/enable/', EnableUserView.as_view(), name='enable-user'),
    path('users/<uuid:user_id>/delete-request/', DeleteUserRequestView.as_view(), name='delete-user-request'),
    path('users/<uuid:user_id>/delete-confirm/', ConfirmDeleteUserView.as_view(), name='confirm-delete-user'),
    path('users/<uuid:user_id>/delete-cancel/', CancelDeleteUserView.as_view(), name='cancel-delete-user'),
]
