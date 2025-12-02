"""
Views for dashboard endpoints.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum

from core.responses import success_response, forbidden_response
from core.permissions import IsAdminUser
from core.utils import get_admin_info
from authentication.models import User
from payments.models import Payment


class DashboardStatisticsView(APIView):
    """
    Get dashboard statistics.
    GET /api/dashboard/statistics/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        user = request.user
        
        # Get statistics
        total_users = User.objects.filter(role='user').count()
        
        today = timezone.now().date()
        todays_new_users = User.objects.filter(
            role='user',
            created_at__date=today
        ).count()
        
        total_subscribers = User.objects.filter(
            role='user',
            subscription_status__in=['premium', 'pro']
        ).count()
        
        # Total earnings from payments
        total_earned = Payment.objects.filter(
            payment_status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return success_response(
            "Dashboard statistics retrieved",
            {
                'admin_info': get_admin_info(user),
                'statistics': {
                    'total_users': total_users,
                    'todays_new_users': todays_new_users,
                    'total_subscribers': total_subscribers,
                    'total_earned': {
                        'amount': float(total_earned),
                        'currency': 'USD'
                    }
                },
                'generated_at': timezone.now().isoformat()
            }
        )
