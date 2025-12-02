"""
URL patterns for dashboard endpoints.
"""
from django.urls import path
from .views import DashboardStatisticsView

urlpatterns = [
    path('statistics/', DashboardStatisticsView.as_view(), name='dashboard-statistics'),
]
