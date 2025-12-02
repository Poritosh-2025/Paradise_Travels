"""
Views for payment endpoints.
"""
import stripe
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q

from core.responses import success_response, error_response
from core.permissions import IsAdminUser
from core.pagination import StandardPagination
from core.utils import get_admin_info
from .models import Payment
from .serializers import PaymentListSerializer, CreatePaymentIntentSerializer, ConfirmPaymentSerializer

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentListView(APIView):
    """
    Get list of all payment transactions.
    GET /api/payments/transactions/
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        admin_user = request.user
        
        # Filter parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = Payment.objects.all()
        
        # Apply date filters
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        queryset = queryset.order_by('-created_at')
        
        # Paginate
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        # Add serial numbers
        start_index = (paginator.page.number - 1) * paginator.get_page_size(request) + 1
        transactions_data = []
        for index, payment in enumerate(page):
            payment_data = PaymentListSerializer(payment).data
            payment_data['sl_no'] = start_index + index
            transactions_data.append(payment_data)
        
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
                    'has_next': paginator.page.has_next(),
                },
                'transactions': transactions_data
            }
        )


class CreatePaymentIntentView(APIView):
    """
    Create Stripe payment intent.
    POST /api/payments/create-intent/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreatePaymentIntentSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        amount = serializer.validated_data['amount']
        currency = serializer.validated_data['currency']
        subscription_plan = serializer.validated_data['subscription_plan']
        
        try:
            # Create Stripe payment intent
            # Amount in cents for Stripe
            amount_cents = int(float(amount) * 100)
            
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                metadata={
                    'user_id': str(request.user.id),
                    'subscription_plan': subscription_plan
                }
            )
            
            # Create pending payment record
            Payment.objects.create(
                user=request.user,
                amount=amount,
                currency=currency.upper(),
                subscription_plan=subscription_plan,
                stripe_payment_intent_id=intent.id,
                payment_status='pending'
            )
            
            return success_response(
                "Payment intent created successfully",
                {
                    'client_secret': intent.client_secret,
                    'payment_intent_id': intent.id,
                    'amount': float(amount),
                    'currency': currency.upper(),
                    'publishable_key': settings.STRIPE_PUBLISHABLE_KEY
                }
            )
        except stripe.error.StripeError as e:
            return error_response(f"Payment error: {str(e)}")


class ConfirmPaymentView(APIView):
    """
    Confirm successful payment.
    POST /api/payments/confirm/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ConfirmPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid request", serializer.errors)
        
        payment_intent_id = serializer.validated_data['payment_intent_id']
        payment_method_id = serializer.validated_data['payment_method_id']
        
        try:
            # Get payment record
            payment = Payment.objects.get(
                stripe_payment_intent_id=payment_intent_id,
                user=request.user
            )
        except Payment.DoesNotExist:
            return error_response("Payment not found")
        
        try:
            # Verify with Stripe
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status == 'succeeded':
                # Update payment record
                payment.payment_status = 'completed'
                payment.payment_date = timezone.now()
                payment.stripe_payment_method_id = payment_method_id
                payment.save()
                
                # Update user subscription
                user = request.user
                if 'premium' in payment.subscription_plan:
                    user.subscription_status = 'premium'
                elif 'pro' in payment.subscription_plan:
                    user.subscription_status = 'pro'
                user.save()
                
                return success_response(
                    "Payment confirmed successfully",
                    {
                        'transaction_id': str(payment.id),
                        'user_email': user.email,
                        'amount': float(payment.amount),
                        'currency': payment.currency,
                        'subscription_status': user.subscription_status,
                        'payment_date': payment.payment_date.isoformat()
                    }
                )
            else:
                payment.payment_status = 'failed'
                payment.save()
                return error_response("Payment not completed")
                
        except stripe.error.StripeError as e:
            return error_response(f"Payment verification error: {str(e)}")


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    """
    Stripe webhook handler.
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
        
        # Handle event
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            self._handle_payment_success(payment_intent)
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            self._handle_payment_failure(payment_intent)
        
        return success_response("Webhook processed successfully")

    def _handle_payment_success(self, payment_intent):
        """Handle successful payment."""
        try:
            payment = Payment.objects.get(
                stripe_payment_intent_id=payment_intent['id']
            )
            payment.payment_status = 'completed'
            payment.payment_date = timezone.now()
            payment.save()
            
            # Update user subscription
            user = payment.user
            if 'premium' in payment.subscription_plan:
                user.subscription_status = 'premium'
            elif 'pro' in payment.subscription_plan:
                user.subscription_status = 'pro'
            user.save()
        except Payment.DoesNotExist:
            pass

    def _handle_payment_failure(self, payment_intent):
        """Handle failed payment."""
        try:
            payment = Payment.objects.get(
                stripe_payment_intent_id=payment_intent['id']
            )
            payment.payment_status = 'failed'
            payment.save()
        except Payment.DoesNotExist:
            pass
