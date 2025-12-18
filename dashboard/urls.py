"""
URL patterns for dashboard endpoints.
"""
from django.urls import path
from .views import (
    DashboardStatisticsView,
    PremiumSubscribersAnalyticsView,
    FreeUsersAnalyticsView,
    CombinedAnalyticsView,
)

urlpatterns = [
    path('statistics/', DashboardStatisticsView.as_view(), name='dashboard-statistics'),
    path('analytics/premium-subscribers/', PremiumSubscribersAnalyticsView.as_view(), name='premium-subscribers'),
    path('analytics/free-users/', FreeUsersAnalyticsView.as_view(), name='free-users'),
    path('analytics/overview/', CombinedAnalyticsView.as_view(), name='analytics-overview'),
]
