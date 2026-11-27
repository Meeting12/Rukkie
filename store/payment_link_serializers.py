from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .payment_link_gateways import available_gateways


class PaymentLinkCreateSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=160)
    customer_email = serializers.EmailField(max_length=254)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3)
    description = serializers.CharField(max_length=240)
    gateway = serializers.ChoiceField(choices=('stripe', 'flutterwave'))
    expires_at = serializers.DateTimeField()
    order_reference = serializers.CharField(required=False, allow_blank=True, max_length=64, default='')
    send_email = serializers.BooleanField(required=False, default=False)

    def validate(self, values):
        gateway = values['gateway']
        currency = values['currency'].upper()
        if currency not in available_gateways().get(gateway, ()):
            raise serializers.ValidationError({'currency': 'Choose a supported currency for an enabled gateway.'})
        if values['amount'] < 1:
            raise serializers.ValidationError({'amount': 'The amount must be at least 1.00.'})
        now = timezone.now()
        minimum = 35 if gateway == 'stripe' else 3
        if not now + timedelta(minutes=minimum) <= values['expires_at'] <= now + timedelta(days=30):
            raise serializers.ValidationError({'expires_at': f'Set expiration {minimum} minutes to 30 days in the future.'})
        values['currency'] = currency
        return values
