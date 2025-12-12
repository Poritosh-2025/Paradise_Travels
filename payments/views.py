"""
Views for payment and subscription endpoints.
Stripe Checkout Session integration.
"""
import stripe
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny

from core.responses import success_response, error_response, created_response
from core.permissions import IsAdminUser
from core.pagination import StandardPagination
from core.utils import get_admin_info
from .models import Plan, Subscription, Payment, UsageTracking, WebhookEvent, VideoPurchase
from .serializers import (
    PlanSerializer, SubscriptionSerializer, PaymentSerializer,
    UsageSerializer, WebhookEventSerializer
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


class CreateCheckoutSessionView(APIView):
    """
    Create Stripe Checkout Session for subscription.
    POST /api/payments/checkout/subscription/
    
    Request Body:
    {
        "plan_type": "premium" or "pro",
        "success_url": "https://yoursite.com/success",
        "cancel_url": "https://yoursite.com/cancel"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_type = request.data.get('plan_type')
        success_url = request.data.get('success_url')
        cancel_url = request.data.get('cancel_url')
        
        if not plan_type:
            return error_response("plan_type is required")
        if not success_url or not cancel_url:
            return error_response("success_url and cancel_url are required")
        
        # Validate plan
        plan = get_plan(plan_type)
        if not plan or not plan.stripe_price_id:
            return error_response("Invalid plan or plan not configured")
        
        # Check existing subscription
        user = request.user
        if hasattr(user, 'subscription'):
            sub = user.subscription
            if sub.plan and sub.plan.plan_id != 'basic' and sub.status == 'active':
                return error_response("You already have an active subscription", status_code=409)
        
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
            
            # Create Checkout Session
            checkout_session = stripe.checkout.Session.create(
                customer=user.stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': plan.stripe_price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                metadata={
                    'user_id': str(user.id),
                    'plan_type': plan_type,
                }
            )
            
            return success_response(
                "Checkout session created",
                {
                    'checkout_url': checkout_session.url,
                    'session_id': checkout_session.id
                }
            )
            
        except stripe.error.StripeError as e:
            return error_response(f"Stripe error: {str(e)}")


class CreateVideoCheckoutSessionView(APIView):
    """
    Create Stripe Checkout Session for video purchase.
    POST /api/payments/checkout/video/
    
    Request Body:
    {
        "video_quality": "standard" or "high",
        "success_url": "https://yoursite.com/success",
        "cancel_url": "https://yoursite.com/cancel"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        video_quality = request.data.get('video_quality', 'standard')
        success_url = request.data.get('success_url')
        cancel_url = request.data.get('cancel_url')
        
        if not success_url or not cancel_url:
            return error_response("success_url and cancel_url are required")
        
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
            
            # Create Checkout Session for one-time payment
            checkout_session = stripe.checkout.Session.create(
                customer=user.stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': f'AI Video Generation ({video_quality.title()} Quality)',
                            'description': 'One-time video generation purchase',
                        },
                        'unit_amount': int(VIDEO_PRICE * 100),  # Convert to cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                metadata={
                    'user_id': str(user.id),
                    'purchase_type': 'video_generation',
                    'video_quality': video_quality,
                }
            )
            
            return success_response(
                "Checkout session created",
                {
                    'checkout_url': checkout_session.url,
                    'session_id': checkout_session.id
                }
            )
            
        except stripe.error.StripeError as e:
            return error_response(f"Stripe error: {str(e)}")


class CheckoutSuccessView(APIView):
    """
    Verify checkout session success.
    GET /api/payments/checkout/success/?session_id=xxx
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session_id = request.query_params.get('session_id')
        
        if not session_id:
            return error_response("session_id is required")
        
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            
            if session.payment_status == 'paid':
                return success_response(
                    "Payment successful",
                    {
                        'session_id': session.id,
                        'payment_status': session.payment_status,
                        'customer_email': session.customer_details.email if session.customer_details else None,
                    }
                )
            else:
                return error_response(f"Payment status: {session.payment_status}")
                
        except stripe.error.StripeError as e:
            return error_response(f"Error: {str(e)}")


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


class CancelSubscriptionView(APIView):
    """
    Cancel subscription (remains active until period end).
    POST /api/payments/subscriptions/cancel/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
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
            return error_response(f"Error: {str(e)}")


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
            return error_response(f"Error: {str(e)}")


class CreateBillingPortalView(APIView):
    """
    Create Stripe Customer Portal session for managing subscription.
    POST /api/payments/billing-portal/
    
    Request Body:
    {
        "return_url": "https://yoursite.com/account"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return_url = request.data.get('return_url')
        
        if not return_url:
            return error_response("return_url is required")
        
        user = request.user
        
        if not user.stripe_customer_id:
            return error_response("No billing account found")
        
        try:
            portal_session = stripe.billing_portal.Session.create(
                customer=user.stripe_customer_id,
                return_url=return_url,
            )
            
            return success_response(
                "Billing portal session created",
                {'portal_url': portal_session.url}
            )
            
        except stripe.error.StripeError as e:
            return error_response(f"Error: {str(e)}")


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


# ==================== ADMIN ENDPOINTS ====================

class AdminTransactionsView(APIView):
    """
    Admin: List all payment transactions.
    GET /api/payments/admin/transactions/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        admin_user = request.user
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = Payment.objects.select_related('user').all()
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        queryset = queryset.order_by('-created_at')
        
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        
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
        """Process webhook events."""
        event_type = event.type
        data = event.data.object
        
        handlers = {
            'checkout.session.completed': self._handle_checkout_completed,
            'customer.subscription.created': self._handle_subscription_created,
            'customer.subscription.updated': self._handle_subscription_updated,
            'customer.subscription.deleted': self._handle_subscription_deleted,
            'invoice.payment_succeeded': self._handle_invoice_paid,
            'invoice.payment_failed': self._handle_invoice_failed,
        }
        
        handler = handlers.get(event_type)
        if handler:
            handler(data)

    def _handle_checkout_completed(self, session):
        """Handle checkout.session.completed event."""
        from authentication.models import User
        
        user_id = session.metadata.get('user_id')
        if not user_id:
            return
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return
        
        # Check if subscription or one-time payment
        if session.mode == 'subscription':
            plan_type = session.metadata.get('plan_type')
            plan = get_plan(plan_type)
            
            if plan and session.subscription:
                # Get Stripe subscription details
                stripe_sub = stripe.Subscription.retrieve(session.subscription)
                
                # Create or update subscription
                subscription, created = Subscription.objects.update_or_create(
                    user=user,
                    defaults={
                        'plan': plan,
                        'stripe_subscription_id': session.subscription,
                        'stripe_price_id': plan.stripe_price_id,
                        'status': 'active',
                        'current_period_start': timezone.datetime.fromtimestamp(
                            stripe_sub.current_period_start, tz=timezone.utc
                        ),
                        'current_period_end': timezone.datetime.fromtimestamp(
                            stripe_sub.current_period_end, tz=timezone.utc
                        )
                    }
                )
                
                # Update user
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
                
        elif session.mode == 'payment':
            # One-time payment (video purchase)
            video_quality = session.metadata.get('video_quality', 'standard')
            
            # Create payment record
            payment = Payment.objects.create(
                user=user,
                stripe_payment_intent_id=session.payment_intent,
                payment_type='video_generation',
                amount=Decimal(session.amount_total) / 100,
                currency=session.currency.upper(),
                status='succeeded',
                description='Video generation purchase',
                payment_date=timezone.now()
            )
            
            # Create video purchase record
            VideoPurchase.objects.create(
                user=user,
                payment=payment,
                video_quality=video_quality,
                amount_paid=Decimal(session.amount_total) / 100,
                generation_status='pending'
            )

    def _handle_subscription_created(self, data):
        """Handle subscription created."""
        pass  # Handled in checkout.session.completed

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

    def _handle_invoice_paid(self, invoice):
        """Handle successful invoice payment."""
        if not invoice.subscription:
            return
            
        try:
            subscription = Subscription.objects.get(stripe_subscription_id=invoice.subscription)
            
            # Record payment
            Payment.objects.create(
                user=subscription.user,
                subscription=subscription,
                stripe_invoice_id=invoice.id,
                stripe_payment_intent_id=invoice.payment_intent,
                payment_type='subscription',
                amount=Decimal(invoice.amount_paid) / 100,
                currency=invoice.currency.upper(),
                status='succeeded',
                description=f"{subscription.plan.name if subscription.plan else 'Subscription'} - Monthly",
                receipt_url=invoice.hosted_invoice_url,
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

    def _handle_invoice_failed(self, invoice):
        """Handle failed invoice payment."""
        if not invoice.subscription:
            return
            
        try:
            subscription = Subscription.objects.get(stripe_subscription_id=invoice.subscription)
            subscription.status = 'past_due'
            subscription.save()
            
            Payment.objects.create(
                user=subscription.user,
                subscription=subscription,
                stripe_invoice_id=invoice.id,
                payment_type='subscription',
                amount=Decimal(invoice.amount_due) / 100,
                currency=invoice.currency.upper(),
                status='failed',
                description='Payment failed'
            )
        except Subscription.DoesNotExist:
            pass