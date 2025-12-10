"""
Views for payment and subscription endpoints.
"""
import stripe
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny

from core.responses import success_response, error_response, created_response, not_found_response
from core.permissions import IsAdminUser
from core.pagination import StandardPagination
from core.utils import get_admin_info
from .models import Plan, Subscription, Payment, UsageTracking, WebhookEvent, VideoPurchase
from .serializers import (
    PlanSerializer, SubscriptionSerializer, CreateSubscriptionSerializer,
    UpgradeSubscriptionSerializer, DowngradeSubscriptionSerializer,
    CancelSubscriptionSerializer, PaymentSerializer, AdminTransactionSerializer,
    AddPaymentMethodSerializer, VideoPurchaseSerializer, UsageSerializer,
    WebhookEventSerializer
)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Video price constant
VIDEO_PRICE = Decimal('5.99')


def get_plan(plan_id):
    """Get plan by plan_id."""
    try:
        return Plan.objects.get(plan_id=plan_id, is_active=True)
    except Plan.DoesNotExist:
        return None


def get_basic_plan():
    """Get or create basic plan."""
    plan, created = Plan.objects.get_or_create(
        plan_id='basic',
        defaults={
            'name': 'Basic',
            'price': Decimal('0.00'),
            'currency': 'EUR',
            'billing_cycle': 'monthly',
            'itineraries_per_month': '1',
            'videos_per_month': 0,
            'video_price': VIDEO_PRICE,
            'video_quality': 'standard',
            'chatbot_access': True,
            'customization': True,
            'social_sharing': True,
            'exclusive_deals': False,
            'priority_support': False,
        }
    )
    return plan


# ==================== SUBSCRIPTION ENDPOINTS ====================

class PlansListView(APIView):
    """
    Get available subscription plans.
    GET /api/payments/subscriptions/plans/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        plans = Plan.objects.filter(is_active=True).order_by('price')
        serializer = PlanSerializer(plans, many=True)
        return success_response("Plans retrieved", {'plans': serializer.data})


class CreateSubscriptionView(APIView):
    """
    Create new subscription.
    POST /api/payments/subscriptions/create/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateSubscriptionSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        user = request.user
        plan_type = serializer.validated_data['plan_type']
        payment_method_id = serializer.validated_data['payment_method_id']
        
        # Check if user already has active paid subscription
        if hasattr(user, 'subscription') and user.subscription.plan and user.subscription.plan.plan_id != 'basic':
            return error_response("Active subscription already exists", status_code=409)
        
        plan = get_plan(plan_type)
        if not plan or not plan.stripe_price_id:
            return error_response("Invalid plan or plan not configured")
        
        try:
            # Get or create Stripe customer
            if not user.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.name or user.email,
                    metadata={'user_id': str(user.id)}
                )
                user.stripe_customer_id = customer.id
                user.save()
            
            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=user.stripe_customer_id
            )
            
            # Set as default payment method
            stripe.Customer.modify(
                user.stripe_customer_id,
                invoice_settings={'default_payment_method': payment_method_id}
            )
            
            # Create subscription
            stripe_subscription = stripe.Subscription.create(
                customer=user.stripe_customer_id,
                items=[{'price': plan.stripe_price_id}],
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent']
            )
            
            # Create or update subscription record
            subscription, created = Subscription.objects.update_or_create(
                user=user,
                defaults={
                    'plan': plan,
                    'stripe_subscription_id': stripe_subscription.id,
                    'stripe_price_id': plan.stripe_price_id,
                    'status': 'active',
                    'current_period_start': timezone.datetime.fromtimestamp(
                        stripe_subscription.current_period_start, tz=timezone.utc
                    ),
                    'current_period_end': timezone.datetime.fromtimestamp(
                        stripe_subscription.current_period_end, tz=timezone.utc
                    )
                }
            )
            
            # Update user subscription status
            user.subscription_status = plan_type
            user.save()
            
            # Initialize usage tracking
            UsageTracking.objects.create(
                user=user,
                subscription=subscription,
                billing_period_start=subscription.current_period_start,
                billing_period_end=subscription.current_period_end,
                videos_remaining=plan.videos_per_month
            )
            
            return created_response(
                "Subscription created successfully",
                {'subscription': SubscriptionSerializer(subscription).data}
            )
            
        except stripe.error.StripeError as e:
            return error_response(f"Payment error: {str(e)}")


class CurrentSubscriptionView(APIView):
    """
    Get current subscription details.
    GET /api/payments/subscriptions/current/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        try:
            subscription = user.subscription
        except Subscription.DoesNotExist:
            # Create basic subscription if none exists
            basic_plan = get_basic_plan()
            subscription = Subscription.objects.create(
                user=user,
                plan=basic_plan,
                status='active'
            )
        
        # Get usage data
        usage_data = None
        usage = UsageTracking.objects.filter(user=user).order_by('-created_at').first()
        if usage and subscription.plan:
            usage_data = {
                'itineraries_generated': usage.itineraries_generated,
                'itineraries_limit': subscription.plan.itineraries_per_month,
                'videos_generated': usage.videos_generated,
                'videos_remaining': usage.videos_remaining,
                'billing_period_start': usage.billing_period_start,
                'billing_period_end': usage.billing_period_end
            }
        
        return success_response(
            "Subscription retrieved",
            {
                'subscription': SubscriptionSerializer(subscription).data,
                'usage': usage_data
            }
        )


class UpgradeSubscriptionView(APIView):
    """
    Upgrade subscription to higher tier.
    PUT /api/payments/subscriptions/upgrade/
    """
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = UpgradeSubscriptionSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        user = request.user
        new_plan_type = serializer.validated_data['new_plan_type']
        
        try:
            subscription = user.subscription
        except Subscription.DoesNotExist:
            return error_response("No subscription found")
        
        current_plan_id = subscription.plan.plan_id if subscription.plan else 'basic'
        
        # Validate upgrade path
        valid_upgrades = {'basic': ['premium', 'pro'], 'premium': ['pro']}
        if new_plan_type not in valid_upgrades.get(current_plan_id, []):
            return error_response("Invalid upgrade path", status_code=400)
        
        new_plan = get_plan(new_plan_type)
        if not new_plan or not new_plan.stripe_price_id:
            return error_response("Plan not configured")
        
        try:
            if subscription.stripe_subscription_id:
                # Update Stripe subscription
                stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    items=[{
                        'id': stripe_sub['items']['data'][0].id,
                        'price': new_plan.stripe_price_id
                    }],
                    proration_behavior='create_prorations'
                )
            
            # Update local subscription
            subscription.plan = new_plan
            subscription.stripe_price_id = new_plan.stripe_price_id
            subscription.save()
            
            # Update user
            user.subscription_status = new_plan_type
            user.save()
            
            # Update usage tracking
            usage = UsageTracking.objects.filter(user=user).order_by('-created_at').first()
            if usage:
                usage.videos_remaining = new_plan.videos_per_month
                usage.save()
            
            return success_response(
                "Subscription upgraded successfully",
                {'subscription': SubscriptionSerializer(subscription).data}
            )
            
        except stripe.error.StripeError as e:
            return error_response(f"Upgrade error: {str(e)}")


class DowngradeSubscriptionView(APIView):
    """
    Downgrade subscription (effective at period end).
    PUT /api/payments/subscriptions/downgrade/
    """
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = DowngradeSubscriptionSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        user = request.user
        new_plan_type = serializer.validated_data['new_plan_type']
        
        try:
            subscription = user.subscription
        except Subscription.DoesNotExist:
            return error_response("No subscription found")
        
        current_plan_id = subscription.plan.plan_id if subscription.plan else 'basic'
        
        # Validate downgrade path
        valid_downgrades = {'pro': ['premium', 'basic'], 'premium': ['basic']}
        if new_plan_type not in valid_downgrades.get(current_plan_id, []):
            return error_response("Invalid downgrade path", status_code=400)
        
        try:
            if new_plan_type == 'basic' and subscription.stripe_subscription_id:
                # Cancel at period end for basic downgrade
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
                subscription.cancel_at_period_end = True
            elif subscription.stripe_subscription_id:
                # Schedule plan change at period end
                new_plan = get_plan(new_plan_type)
                stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    items=[{
                        'id': stripe_sub['items']['data'][0].id,
                        'price': new_plan.stripe_price_id
                    }],
                    proration_behavior='none'
                )
            
            subscription.save()
            
            return success_response(
                "Subscription will be downgraded at the end of current billing period",
                {
                    'subscription': SubscriptionSerializer(subscription).data,
                    'change_effective_date': subscription.current_period_end
                }
            )
            
        except stripe.error.StripeError as e:
            return error_response(f"Downgrade error: {str(e)}")


class CancelSubscriptionView(APIView):
    """
    Cancel subscription (remains active until period end).
    POST /api/payments/subscriptions/cancel/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CancelSubscriptionSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        user = request.user
        
        try:
            subscription = user.subscription
        except Subscription.DoesNotExist:
            return error_response("No subscription found")
        
        if subscription.plan and subscription.plan.plan_id == 'basic':
            return error_response("Cannot cancel free plan")
        
        try:
            if subscription.stripe_subscription_id:
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
            
            subscription.cancel_at_period_end = True
            subscription.cancelled_at = timezone.now()
            subscription.save()
            
            return success_response(
                "Subscription will be cancelled at the end of current billing period",
                {
                    'subscription': SubscriptionSerializer(subscription).data,
                    'cancellation_date': subscription.current_period_end
                }
            )
            
        except stripe.error.StripeError as e:
            return error_response(f"Cancellation error: {str(e)}")


class ReactivateSubscriptionView(APIView):
    """
    Reactivate cancelled subscription.
    POST /api/payments/subscriptions/reactivate/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        try:
            subscription = user.subscription
        except Subscription.DoesNotExist:
            return error_response("No subscription found")
        
        if not subscription.cancel_at_period_end:
            return error_response("Subscription is not cancelled")
        
        try:
            if subscription.stripe_subscription_id:
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=False
                )
            
            subscription.cancel_at_period_end = False
            subscription.cancelled_at = None
            subscription.save()
            
            return success_response(
                "Subscription reactivated successfully",
                {'subscription': SubscriptionSerializer(subscription).data}
            )
            
        except stripe.error.StripeError as e:
            return error_response(f"Reactivation error: {str(e)}")


# ==================== PAYMENT ENDPOINTS ====================

class SetupIntentView(APIView):
    """
    Create Stripe SetupIntent for saving payment method.
    POST /api/payments/setup-intent/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        try:
            # Get or create Stripe customer
            if not user.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.name or user.email,
                    metadata={'user_id': str(user.id)}
                )
                user.stripe_customer_id = customer.id
                user.save()
            
            setup_intent = stripe.SetupIntent.create(
                customer=user.stripe_customer_id,
                payment_method_types=['card']
            )
            
            return success_response(
                "Setup intent created",
                {
                    'client_secret': setup_intent.client_secret,
                    'stripe_customer_id': user.stripe_customer_id
                }
            )
            
        except stripe.error.StripeError as e:
            return error_response(f"Setup error: {str(e)}")


class PaymentMethodsView(APIView):
    """
    Get payment methods.
    GET /api/payments/methods/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        if not user.stripe_customer_id:
            return success_response("No payment methods", {'payment_methods': []})
        
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=user.stripe_customer_id,
                type='card'
            )
            
            customer = stripe.Customer.retrieve(user.stripe_customer_id)
            default_pm = customer.get('invoice_settings', {}).get('default_payment_method')
            
            methods = []
            for pm in payment_methods.data:
                methods.append({
                    'id': pm.id,
                    'type': pm.type,
                    'card': {
                        'brand': pm.card.brand,
                        'last4': pm.card.last4,
                        'exp_month': pm.card.exp_month,
                        'exp_year': pm.card.exp_year
                    },
                    'is_default': pm.id == default_pm
                })
            
            return success_response("Payment methods retrieved", {'payment_methods': methods})
            
        except stripe.error.StripeError as e:
            return error_response(f"Error: {str(e)}")


class AddPaymentMethodView(APIView):
    """
    Add new payment method.
    POST /api/payments/methods/add/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AddPaymentMethodSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        user = request.user
        payment_method_id = serializer.validated_data['payment_method_id']
        set_as_default = serializer.validated_data['set_as_default']
        
        try:
            if not user.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.name or user.email
                )
                user.stripe_customer_id = customer.id
                user.save()
            
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=user.stripe_customer_id
            )
            
            if set_as_default:
                stripe.Customer.modify(
                    user.stripe_customer_id,
                    invoice_settings={'default_payment_method': payment_method_id}
                )
            
            return success_response(
                "Payment method added successfully",
                {
                    'payment_method': {
                        'id': payment_method_id,
                        'is_default': set_as_default
                    }
                }
            )
            
        except stripe.error.StripeError as e:
            return error_response(f"Error: {str(e)}")


class DeletePaymentMethodView(APIView):
    """
    Delete payment method.
    DELETE /api/payments/methods/{payment_method_id}/
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, payment_method_id):
        try:
            stripe.PaymentMethod.detach(payment_method_id)
            return success_response("Payment method removed successfully")
        except stripe.error.StripeError as e:
            return error_response(f"Error: {str(e)}")


class VideoPurchaseView(APIView):
    """
    Purchase single video generation.
    POST /api/payments/video-purchase/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VideoPurchaseSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        user = request.user
        payment_method_id = serializer.validated_data['payment_method_id']
        video_quality = serializer.validated_data['video_quality']
        
        try:
            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=int(VIDEO_PRICE * 100),  # Convert to cents
                currency='eur',
                customer=user.stripe_customer_id,
                payment_method=payment_method_id,
                confirm=True,
                metadata={
                    'user_id': str(user.id),
                    'purchase_type': 'video_generation',
                    'video_quality': video_quality
                }
            )
            
            # Create payment record
            payment = Payment.objects.create(
                user=user,
                stripe_payment_intent_id=payment_intent.id,
                payment_type='video_generation',
                amount=VIDEO_PRICE,
                currency='EUR',
                status='succeeded' if payment_intent.status == 'succeeded' else 'pending',
                description='Video generation purchase',
                payment_date=timezone.now() if payment_intent.status == 'succeeded' else None
            )
            
            # Create video purchase record
            video_purchase = VideoPurchase.objects.create(
                user=user,
                payment=payment,
                video_quality=video_quality,
                amount_paid=VIDEO_PRICE,
                generation_status='pending'
            )
            
            return created_response(
                "Video purchase successful",
                {
                    'payment': PaymentSerializer(payment).data,
                    'purchase': {
                        'purchase_id': str(video_purchase.id),
                        'generation_status': video_purchase.generation_status
                    }
                }
            )
            
        except stripe.error.StripeError as e:
            return error_response(f"Payment error: {str(e)}")


class PaymentHistoryView(APIView):
    """
    Get payment history.
    GET /api/payments/history/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        payment_type = request.query_params.get('payment_type', 'all')
        
        queryset = Payment.objects.filter(user=user)
        
        if payment_type != 'all':
            queryset = queryset.filter(payment_type=payment_type)
        
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        return success_response(
            "Payment history retrieved",
            {
                'payments': PaymentSerializer(page, many=True).data,
                'pagination': {
                    'current_page': paginator.page.number,
                    'total_pages': paginator.page.paginator.num_pages,
                    'total_items': paginator.page.paginator.count,
                    'items_per_page': paginator.get_page_size(request)
                }
            }
        )


# ==================== USAGE ENDPOINTS ====================

class CurrentUsageView(APIView):
    """
    Get current billing period usage.
    GET /api/payments/usage/current/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        usage = UsageTracking.objects.filter(user=user).order_by('-created_at').first()
        
        if not usage:
            return success_response("No usage data", {'usage': None})
        
        try:
            subscription = user.subscription
            plan = subscription.plan
        except (Subscription.DoesNotExist, AttributeError):
            plan = get_basic_plan()
        
        return success_response(
            "Usage retrieved",
            {
                'usage': {
                    'billing_period_start': usage.billing_period_start,
                    'billing_period_end': usage.billing_period_end,
                    'plan_type': plan.plan_id if plan else 'basic',
                    'itineraries': {
                        'generated': usage.itineraries_generated,
                        'limit': plan.itineraries_per_month if plan else '1'
                    },
                    'videos': {
                        'generated': usage.videos_generated,
                        'remaining': usage.videos_remaining,
                        'limit': plan.videos_per_month if plan else 0
                    },
                    'chatbot_queries': usage.chatbot_queries,
                    'next_reset_date': usage.billing_period_end
                }
            }
        )


class UsageHistoryView(APIView):
    """
    Get historical usage data.
    GET /api/payments/usage/history/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = UsageTracking.objects.filter(user=user)
        
        if start_date:
            queryset = queryset.filter(billing_period_start__gte=start_date)
        if end_date:
            queryset = queryset.filter(billing_period_end__lte=end_date)
        
        usage_history = []
        for usage in queryset:
            usage_history.append({
                'period_start': usage.billing_period_start,
                'period_end': usage.billing_period_end,
                'itineraries_generated': usage.itineraries_generated,
                'videos_generated': usage.videos_generated,
                'chatbot_queries': usage.chatbot_queries
            })
        
        return success_response("Usage history retrieved", {'usage_history': usage_history})


# ==================== ADMIN ENDPOINTS ====================

class AdminTransactionsView(APIView):
    """
    Admin: List all payment transactions.
    GET /api/payments/admin/transactions/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        admin_user = request.user
        
        # Filter parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = Payment.objects.select_related('user').all()
        
        # Apply date filters
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        queryset = queryset.order_by('-created_at')
        
        # Paginate
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        # Build transaction list with serial numbers
        start_index = (paginator.page.number - 1) * paginator.get_page_size(request) + 1
        transactions = []
        for index, payment in enumerate(page):
            transactions.append({
                'sl_no': start_index + index,
                'user_name': payment.user.name or payment.user.email,
                'user_email': payment.user.email,
                'pay_amount': {
                    'amount': float(payment.amount),
                    'currency': payment.currency
                },
                'payment_date': payment.payment_date,
                'payment_status': payment.status,
                'stripe_payment_id': payment.stripe_payment_intent_id or ''
            })
        
        return success_response(
            "Transactions retrieved",
            {
                'admin_info': get_admin_info(admin_user),
                'pagination': {
                    'current_page': paginator.page.number,
                    'total_pages': paginator.page.paginator.num_pages,
                    'total_transactions': paginator.page.paginator.count,
                    'page_size': paginator.get_page_size(request),
                    'has_previous': paginator.page.has_previous(),
                    'has_next': paginator.page.has_next()
                },
                'transactions': transactions
            }
        )


class AdminSubscriptionsView(APIView):
    """
    Admin: List all subscriptions.
    GET /api/payments/admin/subscriptions/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        admin_user = request.user
        status_filter = request.query_params.get('status')
        plan_filter = request.query_params.get('plan_type')
        
        queryset = Subscription.objects.select_related('user', 'plan').all()
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if plan_filter:
            queryset = queryset.filter(plan__plan_id=plan_filter)
        
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        subscriptions = []
        for sub in page:
            subscriptions.append({
                'subscription_id': str(sub.id),
                'user_email': sub.user.email,
                'plan_type': sub.plan.plan_id if sub.plan else 'basic',
                'status': sub.status,
                'created_at': sub.created_at,
                'current_period_end': sub.current_period_end
            })
        
        return success_response(
            "Subscriptions retrieved",
            {
                'admin_info': get_admin_info(admin_user),
                'subscriptions': subscriptions,
                'pagination': {
                    'current_page': paginator.page.number,
                    'total_pages': paginator.page.paginator.num_pages,
                    'total_items': paginator.page.paginator.count
                }
            }
        )


class AdminWebhookEventsView(APIView):
    """
    Admin: List webhook events.
    GET /api/payments/admin/webhooks/events/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        admin_user = request.user
        event_type = request.query_params.get('event_type')
        status = request.query_params.get('status')
        
        queryset = WebhookEvent.objects.all()
        
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if status:
            queryset = queryset.filter(processing_status=status)
        
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        return success_response(
            "Webhook events retrieved",
            {
                'admin_info': get_admin_info(admin_user),
                'events': WebhookEventSerializer(page, many=True).data
            }
        )


# ==================== WEBHOOK ENDPOINT ====================

@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    """
    Handle Stripe webhook events.
    POST /api/payments/webhook/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return error_response("Invalid payload", status_code=400)
        except stripe.error.SignatureVerificationError:
            return error_response("Invalid signature", status_code=400)
        
        # Check for duplicate event
        if WebhookEvent.objects.filter(stripe_event_id=event.id).exists():
            return success_response("Event already processed")
        
        # Store event
        webhook_event = WebhookEvent.objects.create(
            stripe_event_id=event.id,
            event_type=event.type,
            event_data=event.data,
            processing_status='pending'
        )
        
        try:
            self._process_event(event)
            webhook_event.processing_status = 'processed'
            webhook_event.processed_at = timezone.now()
        except Exception as e:
            webhook_event.processing_status = 'failed'
            webhook_event.error_message = str(e)
        
        webhook_event.save()
        
        return success_response("Webhook processed")

    def _process_event(self, event):
        """Process different webhook event types."""
        event_type = event.type
        data = event.data.object
        
        if event_type == 'customer.subscription.updated':
            self._handle_subscription_updated(data)
        elif event_type == 'customer.subscription.deleted':
            self._handle_subscription_deleted(data)
        elif event_type == 'invoice.payment_succeeded':
            self._handle_payment_succeeded(data)
        elif event_type == 'invoice.payment_failed':
            self._handle_payment_failed(data)

    def _handle_subscription_updated(self, data):
        """Handle subscription update."""
        try:
            subscription = Subscription.objects.get(stripe_subscription_id=data.id)
            subscription.status = data.status
            subscription.current_period_start = timezone.datetime.fromtimestamp(
                data.current_period_start, tz=timezone.utc
            )
            subscription.current_period_end = timezone.datetime.fromtimestamp(
                data.current_period_end, tz=timezone.utc
            )
            subscription.cancel_at_period_end = data.cancel_at_period_end
            subscription.save()
        except Subscription.DoesNotExist:
            pass

    def _handle_subscription_deleted(self, data):
        """Handle subscription cancellation."""
        try:
            subscription = Subscription.objects.get(stripe_subscription_id=data.id)
            subscription.status = 'cancelled'
            subscription.plan = get_basic_plan()
            subscription.stripe_subscription_id = None
            subscription.save()
            
            # Update user
            subscription.user.subscription_status = 'free'
            subscription.user.save()
        except Subscription.DoesNotExist:
            pass

    def _handle_payment_succeeded(self, data):
        """Handle successful payment."""
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=data.subscription
            )
            
            # Record payment
            Payment.objects.create(
                user=subscription.user,
                subscription=subscription,
                stripe_invoice_id=data.id,
                payment_type='subscription',
                amount=Decimal(data.amount_paid) / 100,
                currency=data.currency.upper(),
                status='succeeded',
                description=f"{subscription.plan.name if subscription.plan else 'Subscription'} - Monthly",
                receipt_url=data.hosted_invoice_url,
                payment_date=timezone.now()
            )
            
            # Reset usage for new period
            if subscription.plan:
                UsageTracking.objects.create(
                    user=subscription.user,
                    subscription=subscription,
                    billing_period_start=subscription.current_period_start,
                    billing_period_end=subscription.current_period_end,
                    videos_remaining=subscription.plan.videos_per_month
                )
        except Subscription.DoesNotExist:
            pass

    def _handle_payment_failed(self, data):
        """Handle failed payment."""
        try:
            subscription = Subscription.objects.get(
                stripe_subscription_id=data.subscription
            )
            subscription.status = 'past_due'
            subscription.save()
            
            Payment.objects.create(
                user=subscription.user,
                subscription=subscription,
                stripe_invoice_id=data.id,
                payment_type='subscription',
                amount=Decimal(data.amount_due) / 100,
                currency=data.currency.upper(),
                status='failed',
                description='Payment failed'
            )
        except Subscription.DoesNotExist:
            pass