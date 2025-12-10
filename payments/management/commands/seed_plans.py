"""
Management command to seed subscription plans.
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from payments.models import Plan


class Command(BaseCommand):
    help = 'Seed subscription plans into the database'

    def handle(self, *args, **options):
        plans_data = [
            {
                'plan_id': 'basic',
                'name': 'Basic',
                'price': Decimal('0.00'),
                'currency': 'EUR',
                'billing_cycle': 'monthly',
                'stripe_price_id': None,
                'itineraries_per_month': '1',
                'videos_per_month': 0,
                'video_price': Decimal('5.99'),
                'video_quality': 'standard',
                'chatbot_access': True,
                'customization': True,
                'social_sharing': True,
                'exclusive_deals': False,
                'priority_support': False,
            },
            {
                'plan_id': 'premium',
                'name': 'Premium',
                'price': Decimal('19.99'),
                'currency': 'EUR',
                'billing_cycle': 'monthly',
                'stripe_price_id': getattr(settings, 'STRIPE_PREMIUM_PRICE_ID', ''),
                'itineraries_per_month': 'unlimited',
                'videos_per_month': 3,
                'video_price': Decimal('5.99'),
                'video_quality': 'standard',
                'chatbot_access': True,
                'customization': True,
                'social_sharing': True,
                'exclusive_deals': False,
                'priority_support': False,
            },
            {
                'plan_id': 'pro',
                'name': 'Pro',
                'price': Decimal('39.99'),
                'currency': 'EUR',
                'billing_cycle': 'monthly',
                'stripe_price_id': getattr(settings, 'STRIPE_PRO_PRICE_ID', ''),
                'itineraries_per_month': 'unlimited',
                'videos_per_month': 5,
                'video_price': Decimal('5.99'),
                'video_quality': 'high',
                'chatbot_access': True,
                'customization': True,
                'social_sharing': True,
                'exclusive_deals': True,
                'priority_support': True,
            },
        ]

        for plan_data in plans_data:
            plan, created = Plan.objects.update_or_create(
                plan_id=plan_data['plan_id'],
                defaults=plan_data
            )
            action = 'Created' if created else 'Updated'
            self.stdout.write(
                self.style.SUCCESS(f"{action} plan: {plan.name}")
            )

        self.stdout.write(self.style.SUCCESS('Successfully seeded all plans!'))