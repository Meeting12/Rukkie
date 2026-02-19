from django.db import migrations, models


def seed_assistant_policies(apps, schema_editor):
    AssistantPolicy = apps.get_model('store', 'AssistantPolicy')
    defaults = [
        {
            'key': 'shipping',
            'title': 'Shipping Policy',
            'content': (
                'Orders are processed in 1-2 business days. Delivery timelines depend on the shipping '
                'method selected at checkout. You can see shipping options and delivery estimates before payment.'
            ),
        },
        {
            'key': 'returns',
            'title': 'Returns Policy',
            'content': (
                'Eligible items can be returned within the policy window shown on your order confirmation. '
                'Items must be unused and in original condition. Contact support with your order number to start a return.'
            ),
        },
        {
            'key': 'payment',
            'title': 'Payment Methods',
            'content': (
                'We support secure checkout with card payments and supported payment gateways available at checkout. '
                'Visible methods may vary by your location and current configuration.'
            ),
        },
    ]
    for row in defaults:
        AssistantPolicy.objects.update_or_create(
            key=row['key'],
            defaults={
                'title': row['title'],
                'content': row['content'],
                'is_active': True,
            },
        )


def unseed_assistant_policies(apps, schema_editor):
    AssistantPolicy = apps.get_model('store', 'AssistantPolicy')
    AssistantPolicy.objects.filter(key__in=['shipping', 'returns', 'payment']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0010_paymenttransaction_paypal_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssistantPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=80, unique=True)),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField()),
                ('is_active', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['key'],
            },
        ),
        migrations.RunPython(seed_assistant_policies, unseed_assistant_policies),
    ]
