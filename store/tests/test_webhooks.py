from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from store.models import Order, PaymentTransaction
from django.contrib.auth.models import User
import json


class WebhookTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='t', password='p')
        # create a simple order
        self.order = Order.objects.create(user=self.user, total=10)

    @override_settings(STRIPE_WEBHOOK_SECRET='')
    def test_stripe_webhook_marks_order_paid(self):
        # Simulate a stripe event payload with metadata order_id
        event = {
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_12345',
                    'metadata': {'order_id': str(self.order.id)},
                    'amount': int(self.order.total * 100),
                }
            }
        }
        resp = self.client.post('/api/payments/webhook/stripe/', data=json.dumps(event), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_PAID)
        tx = PaymentTransaction.objects.filter(order=self.order, provider='stripe', provider_transaction_id='pi_12345').first()
        self.assertIsNotNone(tx)

    @override_settings(STRIPE_WEBHOOK_SECRET='')
    def test_stripe_webhook_idempotent(self):
        event = {
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_777',
                    'metadata': {'order_id': str(self.order.id)},
                    'amount': int(self.order.total * 100),
                }
            }
        }
        # Post twice (simulate retry)
        resp1 = self.client.post('/api/payments/webhook/stripe/', data=json.dumps(event), content_type='application/json')
        resp2 = self.client.post('/api/payments/webhook/stripe/', data=json.dumps(event), content_type='application/json')
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        txs = PaymentTransaction.objects.filter(order=self.order, provider='stripe', provider_transaction_id='pi_777')
        self.assertEqual(txs.count(), 1)
