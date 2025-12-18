"""
Views for dashboard endpoints.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from django.utils import timezone
from django.db.models import Sum, Count, Q
from core.responses import success_response, forbidden_response
from core.permissions import IsAdminUser
from core.utils import get_admin_info, timezone
from authentication.models import User
from payments.models import Payment, Subscription
from django.db.models.functions import TruncMonth, ExtractMonth
from datetime import datetime
from calendar import month_name

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
        
        # Total earnings from payments - Fixed: use 'status' not 'payment_status'
        total_earned = Payment.objects.filter(
            status='succeeded'
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
                        'currency': 'EUR'  # Changed to EUR since Stripe uses EUR
                    }
                },
                'generated_at': timezone.now().isoformat()
            }
        )
    
class PremiumSubscribersAnalyticsView(APIView):
    """
    GET /api/analytics/premium-subscribers?year=2024
    
    Retrieves monthly count of premium and pro subscribers.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        # Get year parameter
        year = request.query_params.get('year')
        
        if not year:
            return Response({
                'status': 'error',
                'message': 'Year parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            year = int(year)
        except ValueError:
            return Response({
                'status': 'error',
                'message': 'Year must be a valid integer'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate year range
        current_year = timezone.now().year
        if year < 2000 or year > current_year + 1:
            return Response({
                'status': 'error',
                'message': f'Year must be between 2000 and {current_year + 1}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Query subscriptions by month
        monthly_data = []
        total_premium = 0
        total_pro = 0
        
        for month_num in range(1, 13):
            # Count premium subscriptions created in this month
            premium_count = Subscription.objects.filter(
                plan__plan_id='premium',
                created_at__year=year,
                created_at__month=month_num
            ).count()
            
            # Count pro subscriptions created in this month
            pro_count = Subscription.objects.filter(
                plan__plan_id='pro',
                created_at__year=year,
                created_at__month=month_num
            ).count()
            
            total_paid = premium_count + pro_count
            total_premium += premium_count
            total_pro += pro_count
            
            monthly_data.append({
                'month': month_name[month_num],
                'month_number': month_num,
                'premium_users': premium_count,
                'pro_users': pro_count,
                'total_paid_users': total_paid
            })
        
        # Calculate yearly summary
        total_paid_users = total_premium + total_pro
        avg_premium = round(total_premium / 12, 2) if total_premium > 0 else 0
        avg_pro = round(total_pro / 12, 2) if total_pro > 0 else 0
        
        return Response({
            'status': 'success',
            'year': year,
            'data': {
                'monthly_breakdown': monthly_data,
                'yearly_summary': {
                    'total_premium_users': total_premium,
                    'total_pro_users': total_pro,
                    'total_paid_users': total_paid_users,
                    'average_premium_per_month': avg_premium,
                    'average_pro_per_month': avg_pro
                }
            }
        })


class FreeUsersAnalyticsView(APIView):
    """
    GET /api/analytics/free-users?year=2024
    
    Retrieves monthly count of free users joining the platform.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        # Get year parameter
        year = request.query_params.get('year')
        
        if not year:
            return Response({
                'status': 'error',
                'message': 'Year parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            year = int(year)
        except ValueError:
            return Response({
                'status': 'error',
                'message': 'Year must be a valid integer'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate year range
        current_year = timezone.now().year
        if year < 2000 or year > current_year + 1:
            return Response({
                'status': 'error',
                'message': f'Year must be between 2000 and {current_year + 1}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Query free users by month
        # Free users = users without active premium/pro subscription
        monthly_data = []
        total_free = 0
        peak_count = 0
        peak_month = ''
        lowest_count = float('inf')
        lowest_month = ''
        
        for month_num in range(1, 13):
            # Count users created in this month who don't have paid subscription
            # Option 1: Users with no subscription at all
            # Option 2: Users with 'basic' plan or no plan
            
            free_count = User.objects.filter(
                created_at__year=year,
                created_at__month=month_num
            ).exclude(
                subscription__plan__plan_id__in=['premium', 'pro']
            ).count()
            
            total_free += free_count
            
            # Track peak and lowest months
            if free_count > peak_count:
                peak_count = free_count
                peak_month = month_name[month_num]
            
            if free_count < lowest_count:
                lowest_count = free_count
                lowest_month = month_name[month_num]
            
            monthly_data.append({
                'month': month_name[month_num],
                'month_number': month_num,
                'free_users': free_count
            })
        
        # Handle edge case where no data exists
        if lowest_count == float('inf'):
            lowest_count = 0
            lowest_month = 'N/A'
        if peak_count == 0:
            peak_month = 'N/A'
        
        # Calculate average
        avg_free = round(total_free / 12, 2) if total_free > 0 else 0
        
        return Response({
            'status': 'success',
            'year': year,
            'data': {
                'monthly_breakdown': monthly_data,
                'yearly_summary': {
                    'total_free_users': total_free,
                    'average_free_users_per_month': avg_free,
                    'peak_month': peak_month,
                    'lowest_month': lowest_month
                }
            }
        })


class CombinedAnalyticsView(APIView):
    """
    GET /api/analytics/overview?year=2024
    
    Retrieves combined analytics for all user types.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        year = request.query_params.get('year')
        
        if not year:
            year = timezone.now().year
        else:
            try:
                year = int(year)
            except ValueError:
                return Response({
                    'status': 'error',
                    'message': 'Year must be a valid integer'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        monthly_data = []
        
        for month_num in range(1, 13):
            # Premium users
            premium_count = Subscription.objects.filter(
                plan__plan_id='premium',
                created_at__year=year,
                created_at__month=month_num
            ).count()
            
            # Pro users
            pro_count = Subscription.objects.filter(
                plan__plan_id='pro',
                created_at__year=year,
                created_at__month=month_num
            ).count()
            
            # Free users
            free_count = User.objects.filter(
                created_at__year=year,
                created_at__month=month_num
            ).exclude(
                subscription__plan__plan_id__in=['premium', 'pro']
            ).count()
            
            # Total users registered this month
            total_users = User.objects.filter(
                created_at__year=year,
                created_at__month=month_num
            ).count()
            
            monthly_data.append({
                'month': month_name[month_num],
                'month_number': month_num,
                'free_users': free_count,
                'premium_users': premium_count,
                'pro_users': pro_count,
                'total_paid_users': premium_count + pro_count,
                'total_users': total_users
            })
        
        # Calculate totals
        total_free = sum(m['free_users'] for m in monthly_data)
        total_premium = sum(m['premium_users'] for m in monthly_data)
        total_pro = sum(m['pro_users'] for m in monthly_data)
        total_all = sum(m['total_users'] for m in monthly_data)
        
        return Response({
            'status': 'success',
            'year': year,
            'data': {
                'monthly_breakdown': monthly_data,
                'yearly_summary': {
                    'total_free_users': total_free,
                    'total_premium_users': total_premium,
                    'total_pro_users': total_pro,
                    'total_paid_users': total_premium + total_pro,
                    'total_all_users': total_all,
                    'conversion_rate': round((total_premium + total_pro) / total_all * 100, 2) if total_all > 0 else 0
                }
            }
        })