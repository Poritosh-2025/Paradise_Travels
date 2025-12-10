"""
URL patterns for administrators endpoints.
"""
from django.urls import path
from .views import (
    AdminListView, CreateStaffAdminView, UpdateAdminView,
    DisableAdminView, EnableAdminView, DeleteAdminView
)

urlpatterns = [
    path('admins/', AdminListView.as_view(), name='admin-list'),
    path('admins/create/', CreateStaffAdminView.as_view(), name='create-staff-admin'),
    path('admins/<uuid:admin_id>/', UpdateAdminView.as_view(), name='update-admin'),
    path('admins/<uuid:admin_id>/disable/', DisableAdminView.as_view(), name='disable-admin'),
    path('admins/<uuid:admin_id>/enable/', EnableAdminView.as_view(), name='enable-admin'),
    path('admins/<uuid:admin_id>/delete/', DeleteAdminView.as_view(), name='delete-admin'),

]
