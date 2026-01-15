import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_services', '0001_initial'),
        ('payments', '0002_plan_remove_subscription_billing_cycle_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='videopurchase',
            name='video_generation',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='video_purchase',
                to='ai_services.videogeneration'
            ),
        ),
    ]
