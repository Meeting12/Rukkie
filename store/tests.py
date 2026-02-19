from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
from django.core.cache import cache
from .models import (
	Product,
	ProductImage,
	Cart,
	CartItem,
	Order,
	OrderItem,
	Category,
	ShippingMethod,
	PaymentTransaction,
	AssistantPolicy,
	UserNotification,
	UserMailboxMessage,
)
from django.conf import settings
from unittest.mock import Mock, patch
from django.contrib.auth.models import User
import io
import os
import tempfile
import shutil
import zipfile
from PIL import Image


class CartPermissionTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.p = Product.objects.create(name='Test', slug='test', price='9.99', stock=10)
		# create a cart and item (cart A)
		self.cart_a = Cart.objects.create(session_key='a')
		self.item = CartItem.objects.create(cart=self.cart_a, product=self.p, quantity=1)
		# create another cart (cart B)
		self.cart_b = Cart.objects.create(session_key='b')

	def test_cannot_update_other_cart_item(self):
		# simulate session for cart_b
		session = self.client.session
		session['cart_id'] = self.cart_b.id
		session.save()

		resp = self.client.post('/api/cart/update/', {'item_id': self.item.id, 'quantity': 5}, content_type='application/json')
		self.assertEqual(resp.status_code, 404)

	def test_cannot_remove_other_cart_item(self):
		session = self.client.session
		session['cart_id'] = self.cart_b.id
		session.save()

		resp = self.client.post('/api/cart/remove/', {'item_id': self.item.id}, content_type='application/json')
		self.assertEqual(resp.status_code, 404)


class CheckoutAndPaymentTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.user = User.objects.create_user(username='checkout_user', password='test12345', email='checkout@example.com')
		self.client.force_login(self.user)
		self.p = Product.objects.create(name='Chk', slug='chk', price='10.00', stock=5)
		# prepare session cart
		session = self.client.session
		cart = Cart.objects.create(session_key='s', user=self.user)
		session['cart_id'] = cart.id
		session.save()
		CartItem.objects.create(cart=cart, product=self.p, quantity=2)

	def test_checkout_creates_order_and_keeps_cart_until_payment(self):
		data = {
			'shipping_method': None,
			'shipping_address': {'full_name': 'T', 'line1': 'A', 'city': 'C', 'postal_code': '000', 'country': 'US'},
			'billing_address': {'full_name': 'T', 'line1': 'A', 'city': 'C', 'postal_code': '000', 'country': 'US'}
		}
		resp = self.client.post('/api/checkout/', data, content_type='application/json')
		self.assertEqual(resp.status_code, 200)
		order = Order.objects.first()
		self.assertIsNotNone(order)
		self.assertEqual(order.status, Order.STATUS_PENDING)
		# cart should remain until payment is confirmed
		cart_id = self.client.session.get('cart_id')
		from .models import Cart
		cart = Cart.objects.get(id=cart_id)
		self.assertEqual(cart.items.count(), 1)

	def test_payment_verify_marks_paid_and_clears_cart(self):
		settings.PAYMENT_VERIFY_TOKEN = 'testtoken'
		data = {
			'shipping_method': None,
			'shipping_address': {'full_name': 'T', 'line1': 'A', 'city': 'C', 'postal_code': '000', 'country': 'US'},
			'billing_address': {'full_name': 'T', 'line1': 'A', 'city': 'C', 'postal_code': '000', 'country': 'US'}
		}
		resp = self.client.post('/api/checkout/', data, content_type='application/json')
		self.assertEqual(resp.status_code, 200)
		order_id = resp.json()['id']

		verify = self.client.post(
			'/api/payments/verify/',
			{'order_id': order_id, 'provider': 'test', 'transaction_id': 'txn_1', 'verify_token': 'testtoken'},
			content_type='application/json'
		)
		self.assertEqual(verify.status_code, 200)

		order = Order.objects.get(id=order_id)
		self.assertEqual(order.status, Order.STATUS_PAID)
		cart_id = self.client.session.get('cart_id')
		from .models import Cart
		cart = Cart.objects.get(id=cart_id)
		self.assertEqual(cart.items.count(), 0)

	def test_payment_finalize_only_deducts_ordered_quantity_from_cart(self):
		settings.PAYMENT_VERIFY_TOKEN = 'testtoken'
		data = {
			'shipping_method': None,
			'shipping_address': {'full_name': 'T', 'line1': 'A', 'city': 'C', 'postal_code': '000', 'country': 'US'},
			'billing_address': {'full_name': 'T', 'line1': 'A', 'city': 'C', 'postal_code': '000', 'country': 'US'}
		}
		resp = self.client.post('/api/checkout/', data, content_type='application/json')
		self.assertEqual(resp.status_code, 200)
		order_id = resp.json()['id']

		cart_id = self.client.session.get('cart_id')
		cart = Cart.objects.get(id=cart_id)
		cart_item = cart.items.first()
		cart_item.quantity = 5
		cart_item.save(update_fields=['quantity'])

		verify = self.client.post(
			'/api/payments/verify/',
			{'order_id': order_id, 'provider': 'test', 'transaction_id': 'txn_partial_clear', 'verify_token': 'testtoken'},
			content_type='application/json'
		)
		self.assertEqual(verify.status_code, 200)

		cart.refresh_from_db()
		self.assertEqual(cart.items.count(), 1)
		self.assertEqual(cart.items.first().quantity, 3)

	def test_payment_verify_requires_token_if_set(self):
		# set token in settings for test
		settings.PAYMENT_VERIFY_TOKEN = 'testtoken'
		order = Order.objects.create(total=20)
		session = self.client.session
		session['checkout_order_ids'] = [str(order.id)]
		session.save()
		# call without token
		resp = self.client.post('/api/payments/verify/', {'order_id': order.id, 'provider': 'test'}, content_type='application/json')
		self.assertEqual(resp.status_code, 403)
		# call with token
		resp = self.client.post('/api/payments/verify/', {'order_id': order.id, 'provider': 'test', 'verify_token': 'testtoken'}, content_type='application/json')
		self.assertEqual(resp.status_code, 200)
		order.refresh_from_db()
		self.assertEqual(order.status, Order.STATUS_PAID)

	def test_payment_verify_rejects_amount_mismatch(self):
		settings.PAYMENT_VERIFY_TOKEN = 'testtoken'
		order = Order.objects.create(total=20)
		session = self.client.session
		session['checkout_order_ids'] = [str(order.id)]
		session.save()
		resp = self.client.post(
			'/api/payments/verify/',
			{
				'order_id': order.id,
				'provider': 'test',
				'amount': '15.00',
				'transaction_id': 'txn_mismatch',
				'verify_token': 'testtoken',
			},
			content_type='application/json'
		)
		self.assertEqual(resp.status_code, 400)
		self.assertEqual(resp.json().get('error'), 'amount_mismatch')
		order.refresh_from_db()
		self.assertEqual(order.status, Order.STATUS_PENDING)


class ChatAssistantTests(TestCase):
	def setUp(self):
		self.client = Client()
		Product.objects.create(name='Whitening Soap', slug='whitening-soap', price='12.00', stock=5, is_active=True)

	def test_chat_requires_message(self):
		resp = self.client.post('/api/chat/', {}, content_type='application/json')
		self.assertEqual(resp.status_code, 400)

	def test_chat_can_find_product_match(self):
		resp = self.client.post('/api/chat/', {'message': 'soap'}, content_type='application/json')
		self.assertEqual(resp.status_code, 200)
		self.assertIn('reply', resp.json())
		self.assertIn('Whitening Soap', resp.json()['reply'])


class AssistantChatEndpointTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.category = Category.objects.create(name='Skincare', slug='skincare', is_active=True)
		self.product = Product.objects.create(name='Glow Soap', slug='glow-soap', price='15.00', stock=7, is_active=True)
		self.product.categories.add(self.category)
		ShippingMethod.objects.create(name='Standard', price='5.00', delivery_days='3-5 days', active=True)
		self.order = Order.objects.create(total='15.00')
		OrderItem.objects.create(order=self.order, product=self.product, quantity=1, price='15.00')
		PaymentTransaction.objects.create(
			order=self.order,
			provider='stripe',
			provider_transaction_id='txn-assistant-1',
			amount='15.00',
			status='succeeded',
			success=True,
		)
		AssistantPolicy.objects.update_or_create(
			key='shipping',
			defaults={'title': 'Shipping Policy', 'content': 'Shipping policy for tests.', 'is_active': True},
		)
		AssistantPolicy.objects.update_or_create(
			key='returns',
			defaults={'title': 'Returns Policy', 'content': 'Returns policy for tests.', 'is_active': True},
		)
		AssistantPolicy.objects.update_or_create(
			key='payment',
			defaults={'title': 'Payment Methods', 'content': 'Payment policy for tests.', 'is_active': True},
		)

	def _ask(self, message, **extra):
		payload = {'message': message, 'session_id': extra.get('session_id'), 'context': extra.get('context')}
		return self.client.post('/api/assistant/chat/', payload, content_type='application/json')

	def test_shipping_intent_uses_policy(self):
		resp = self._ask('Tell me about shipping options')
		self.assertEqual(resp.status_code, 200)
		body = resp.json()
		self.assertEqual(body.get('intent'), 'shipping')
		self.assertIn('Shipping policy for tests.', body.get('reply', ''))
		self.assertTrue(body.get('session_id'))
		self.assertTrue(isinstance(body.get('suggestions'), list))

	def test_payment_intent_reports_available_providers(self):
		settings.STRIPE_SECRET_KEY = 'sk_test_x'
		settings.STRIPE_PUBLISHABLE_KEY = 'pk_test_x'
		settings.FLUTTERWAVE_SECRET_KEY = 'FLWSECK_TEST-abc-X'
		settings.PAYPAL_CLIENT_ID = 'paypal_client'
		settings.PAYPAL_SECRET = 'paypal_secret'
		resp = self._ask('What payment methods do you support?')
		self.assertEqual(resp.status_code, 200)
		body = resp.json()
		self.assertEqual(body.get('intent'), 'payment')
		self.assertIn('Stripe', body.get('reply', ''))

	def test_returns_intent_uses_policy(self):
		resp = self._ask('I need a refund for my order')
		self.assertEqual(resp.status_code, 200)
		body = resp.json()
		self.assertEqual(body.get('intent'), 'returns')
		self.assertIn('Returns policy for tests.', body.get('reply', ''))

	def test_product_search_returns_products(self):
		resp = self._ask('find glow soap')
		self.assertEqual(resp.status_code, 200)
		body = resp.json()
		self.assertEqual(body.get('intent'), 'product_search')
		self.assertIn('Glow Soap', body.get('reply', ''))
		self.assertIn('$15.00', body.get('reply', ''))

	def test_order_tracking_with_order_number(self):
		resp = self._ask(f'track order {self.order.order_number}')
		self.assertEqual(resp.status_code, 200)
		body = resp.json()
		self.assertEqual(body.get('intent'), 'order_tracking')
		self.assertIn(self.order.order_number, body.get('reply', ''))


class PublicEndpointRateLimitTests(TestCase):
	def setUp(self):
		self.client = Client()
		cache.clear()
		self.user = User.objects.create_user(username='ratelimit_user', password='test12345', email='ratelimit@example.com')

	def tearDown(self):
		cache.clear()

	def test_login_rate_limit_returns_429(self):
		payload = {'username': self.user.username, 'password': 'wrong-password'}
		for _ in range(12):
			resp = self.client.post('/api/auth/login/', payload, content_type='application/json')
			self.assertEqual(resp.status_code, 401)
		blocked = self.client.post('/api/auth/login/', payload, content_type='application/json')
		self.assertEqual(blocked.status_code, 429)
		self.assertEqual(blocked.json().get('error'), 'rate_limited')

	def test_contact_rate_limit_returns_429(self):
		for _ in range(8):
			resp = self.client.post('/api/contact/', {}, content_type='application/json')
			self.assertEqual(resp.status_code, 400)
		blocked = self.client.post('/api/contact/', {}, content_type='application/json')
		self.assertEqual(blocked.status_code, 429)
		self.assertEqual(blocked.json().get('error'), 'rate_limited')


class WishlistAndHomeContentTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.user = User.objects.create_user(username='wish_user', password='test12345', email='wish@example.com')
		self.product = Product.objects.create(name='Wish Product', slug='wish-product', price='20.00', stock=10, is_active=True)

	def test_wishlist_clear_endpoint(self):
		from .models import Wishlist
		wishlist, _ = Wishlist.objects.get_or_create(user=self.user)
		wishlist.products.add(self.product)
		self.client.force_login(self.user)

		resp = self.client.post('/api/wishlist/clear/', {}, content_type='application/json')
		self.assertEqual(resp.status_code, 200)
		self.assertTrue(resp.json().get('ok'))
		wishlist.refresh_from_db()
		self.assertEqual(wishlist.products.count(), 0)

	def test_home_content_returns_payload(self):
		from .models import Category, HomeHeroSlide
		Category.objects.create(name='Home Cat', slug='home-cat', is_active=True)
		HomeHeroSlide.objects.create(title='Home Hero', title_accent='Slide', is_active=True, sort_order=1)

		resp = self.client.get('/api/home/content/')
		self.assertEqual(resp.status_code, 200)
		body = resp.json()
		self.assertIn('hero_slides', body)
		self.assertIn('categories', body)


class AddressCheckoutTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.user = User.objects.create_user(username='addr_user', password='test12345', email='addr@example.com')
		self.client.force_login(self.user)
		self.product = Product.objects.create(name='Addr Item', slug='addr-item', price='10.00', stock=5)

		session = self.client.session
		cart = Cart.objects.create(session_key='addr_s', user=self.user)
		session['cart_id'] = cart.id
		session.save()
		CartItem.objects.create(cart=cart, product=self.product, quantity=1)

		from .models import Address
		self.saved_shipping = Address.objects.create(
			user=self.user,
			full_name='Saved User',
			line1='123 Saved Street',
			city='Saved City',
			postal_code='00001',
			country='US',
		)

	def test_checkout_uses_saved_addresses(self):
		resp = self.client.post(
			'/api/checkout/',
			{
				'shipping_address_id': self.saved_shipping.id,
				'billing_address_id': self.saved_shipping.id,
			},
			content_type='application/json'
		)
		self.assertEqual(resp.status_code, 200)
		order = Order.objects.get(id=resp.json()['id'])
		self.assertEqual(order.shipping_address_id, self.saved_shipping.id)
		self.assertEqual(order.billing_address_id, self.saved_shipping.id)

	def test_checkout_rejects_address_owned_by_another_user(self):
		other_user = User.objects.create_user(username='other_addr_user', password='test12345', email='other@example.com')
		from .models import Address
		other_address = Address.objects.create(
			user=other_user,
			full_name='Other User',
			line1='9 Other Road',
			city='Other City',
			postal_code='00002',
			country='US',
		)

		resp = self.client.post(
			'/api/checkout/',
			{
				'shipping_address_id': other_address.id,
				'billing_address_id': self.saved_shipping.id,
			},
			content_type='application/json'
		)
		self.assertEqual(resp.status_code, 400)
		self.assertEqual(resp.json().get('error'), 'invalid_shipping_address_id')


class AccountNotificationsMailboxTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.user = User.objects.create_user(
			username='notify_user',
			password='test12345',
			email='notify@example.com',
		)
		self.client.force_login(self.user)
		UserNotification.objects.create(
			user=self.user,
			title='Order created',
			message='Order ABC123 created.',
			level='info',
		)
		UserMailboxMessage.objects.create(
			user=self.user,
			subject='Welcome',
			body='Welcome to De-Rukkies Collections.',
			category='account',
		)

	def test_notifications_list_and_mark_read(self):
		resp = self.client.get('/api/account/notifications/')
		self.assertEqual(resp.status_code, 200)
		body = resp.json()
		self.assertIn('results', body)
		self.assertEqual(len(body['results']), 1)
		self.assertEqual(int(body.get('unread_count') or 0), 1)

		row_id = body['results'][0]['id']
		mark = self.client.post(f'/api/account/notifications/{row_id}/read/', {}, content_type='application/json')
		self.assertEqual(mark.status_code, 200)
		self.assertTrue(UserNotification.objects.get(id=row_id).is_read)

	def test_mailbox_list_and_mark_all_read(self):
		resp = self.client.get('/api/account/mailbox/')
		self.assertEqual(resp.status_code, 200)
		body = resp.json()
		self.assertIn('results', body)
		self.assertEqual(len(body['results']), 1)
		self.assertEqual(int(body.get('unread_count') or 0), 1)

		mark_all = self.client.post('/api/account/mailbox/mark-all-read/', {}, content_type='application/json')
		self.assertEqual(mark_all.status_code, 200)
		self.assertEqual(UserMailboxMessage.objects.filter(user=self.user, is_read=False).count(), 0)

	def test_login_creates_security_notification_and_mailbox(self):
		self.client.post('/api/auth/logout/', {}, content_type='application/json')
		resp = self.client.post(
			'/api/auth/login/',
			{'username': self.user.username, 'password': 'test12345'},
			content_type='application/json',
		)
		self.assertEqual(resp.status_code, 200)
		self.assertTrue(UserNotification.objects.filter(user=self.user, title='New login detected').exists())
		self.assertTrue(UserMailboxMessage.objects.filter(user=self.user, category='security').exists())


class FlutterwavePaymentConfigTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.user = User.objects.create_user(username='flw_user', password='test12345', email='flw@example.com')
		self.client.force_login(self.user)
		self.product = Product.objects.create(name='FLW Item', slug='flw-item', price='10.00', stock=5)
		self.order = Order.objects.create(user=self.user, total=10)
		OrderItem.objects.create(order=self.order, product=self.product, quantity=1, price='10.00')

	def test_flutterwave_returns_config_error_when_secret_missing(self):
		settings.FLUTTERWAVE_SECRET_KEY = ''
		resp = self.client.post(
			'/api/payments/flutterwave/create/',
			{'order_id': self.order.id, 'redirect_url': 'https://example.com/'},
			content_type='application/json',
		)
		self.assertEqual(resp.status_code, 500)
		self.assertEqual(resp.json().get('error'), 'flutterwave_not_configured')

	@patch('store.views.requests.post')
	def test_flutterwave_create_payment_success(self, mock_post):
		settings.FLUTTERWAVE_SECRET_KEY = 'FLWSECK_TEST-validkey'
		settings.FLUTTERWAVE_MODE = 'TEST'

		mock_resp = Mock()
		mock_resp.status_code = 200
		mock_resp.json.return_value = {'data': {'link': 'https://checkout.flutterwave.com/pay/abc'}}
		mock_post.return_value = mock_resp

		resp = self.client.post(
			'/api/payments/flutterwave/create/',
			{'order_id': self.order.id, 'redirect_url': 'https://example.com/'},
			content_type='application/json',
		)
		self.assertEqual(resp.status_code, 200)
		self.assertIn('link', resp.json())

	@patch('store.views.requests.get')
	def test_flutterwave_confirm_marks_order_paid(self, mock_get):
		settings.FLUTTERWAVE_SECRET_KEY = 'FLWSECK_TEST-validkey'
		settings.FLUTTERWAVE_MODE = 'TEST'

		mock_resp = Mock()
		mock_resp.status_code = 200
		mock_resp.json.return_value = {
			'status': 'success',
			'data': {
				'id': 998877,
				'status': 'successful',
				'amount': '10.00',
				'tx_ref': f'order-{self.order.id}-abcd1234',
				'meta': {'order_id': str(self.order.id)},
			},
		}
		mock_get.return_value = mock_resp

		resp = self.client.post(
			'/api/payments/flutterwave/confirm/',
			{'order_id': self.order.id, 'transaction_id': '998877', 'status': 'successful'},
			content_type='application/json',
		)
		self.assertEqual(resp.status_code, 200)
		self.assertTrue(resp.json().get('paid'))
		self.order.refresh_from_db()
		self.assertEqual(self.order.status, Order.STATUS_PAID)


class PayPalPaymentConfigTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.user = User.objects.create_user(username='paypal_user', password='test12345', email='paypal@example.com')
		self.client.force_login(self.user)
		self.product = Product.objects.create(name='PayPal Item', slug='paypal-item', price='10.00', stock=5)
		self.order = Order.objects.create(user=self.user, total=10)
		OrderItem.objects.create(order=self.order, product=self.product, quantity=1, price='10.00')

	@patch('store.views.paypalrestsdk.Payment.find')
	def test_paypal_confirm_marks_order_paid(self, mock_find):
		settings.PAYPAL_CLIENT_ID = 'paypal_client'
		settings.PAYPAL_SECRET = 'paypal_secret'
		settings.PAYPAL_MODE = 'sandbox'

		mock_payment = Mock()
		mock_payment.state = 'approved'
		mock_payment.to_dict.return_value = {
			'transactions': [
				{
					'description': f'Order {self.order.id}',
					'amount': {'total': '10.00', 'currency': 'USD'},
					'related_resources': [{'sale': {'id': 'SALE-123'}}],
				}
			]
		}
		mock_find.return_value = mock_payment

		resp = self.client.post(
			'/api/payments/paypal/confirm/',
			{'order_id': self.order.id, 'payment_id': 'PAY-123', 'payer_id': 'PAYER-123'},
			content_type='application/json',
		)
		self.assertEqual(resp.status_code, 200)
		self.assertTrue(resp.json().get('paid'))
		self.order.refresh_from_db()
		self.assertEqual(self.order.status, Order.STATUS_PAID)


class StripePaymentConfigTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.user = User.objects.create_user(username='stripe_user', password='test12345', email='stripe@example.com')
		self.client.force_login(self.user)
		self.product = Product.objects.create(name='Stripe Item', slug='stripe-item', price='10.00', stock=5)
		self.order = Order.objects.create(user=self.user, total=10)
		OrderItem.objects.create(order=self.order, product=self.product, quantity=1, price='10.00')

	def test_stripe_returns_config_error_when_secret_missing(self):
		settings.STRIPE_SECRET_KEY = ''
		settings.STRIPE_MODE = 'TEST'
		resp = self.client.post(
			'/api/payments/stripe/create/',
			{'order_id': self.order.id, 'redirect_url': 'https://example.com/'},
			content_type='application/json',
		)
		self.assertEqual(resp.status_code, 500)
		self.assertEqual(resp.json().get('error'), 'stripe_not_configured')

	def test_stripe_rejects_test_key_in_live_mode(self):
		settings.STRIPE_SECRET_KEY = 'sk_test_example'
		settings.STRIPE_MODE = 'LIVE'
		resp = self.client.post(
			'/api/payments/stripe/create/',
			{'order_id': self.order.id, 'redirect_url': 'https://example.com/'},
			content_type='application/json',
		)
		self.assertEqual(resp.status_code, 500)
		self.assertEqual(resp.json().get('error'), 'stripe_live_mode_requires_live_key')

	@patch('store.views.stripe.checkout.Session.create')
	def test_stripe_create_payment_success(self, mock_create):
		settings.STRIPE_SECRET_KEY = 'sk_test_example'
		settings.STRIPE_MODE = 'TEST'
		mock_session = Mock()
		mock_session.id = 'cs_test_example'
		mock_session.url = 'https://checkout.stripe.com/c/pay/cs_test_example'
		mock_session.payment_status = 'unpaid'
		mock_create.return_value = mock_session

		resp = self.client.post(
			'/api/payments/stripe/create/',
			{'order_id': self.order.id, 'redirect_url': 'https://example.com/'},
			content_type='application/json',
		)
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.json().get('checkout_url'), 'https://checkout.stripe.com/c/pay/cs_test_example')

	@patch('store.views.stripe.checkout.Session.retrieve')
	def test_stripe_confirm_session_marks_order_paid(self, mock_retrieve):
		settings.STRIPE_SECRET_KEY = 'sk_test_example'
		settings.STRIPE_MODE = 'TEST'

		mock_retrieve.return_value = Mock(
			id='cs_test_123',
			payment_status='paid',
			amount_total=1000,
			metadata={'order_id': str(self.order.id)},
			payment_intent='pi_test_123',
		)

		resp = self.client.post(
			'/api/payments/stripe/confirm/',
			{'order_id': self.order.id, 'session_id': 'cs_test_123'},
			content_type='application/json',
		)
		self.assertEqual(resp.status_code, 200)
		self.assertTrue(resp.json().get('paid'))
		self.order.refresh_from_db()
		self.assertEqual(self.order.status, Order.STATUS_PAID)


class ProductCSVImageImportTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.admin_user = User.objects.create_superuser(
			username='csv_admin',
			email='csv_admin@example.com',
			password='test12345'
		)
		self.client.force_login(self.admin_user)

		self.temp_media_root = tempfile.mkdtemp(prefix='rukkie_media_')
		self.settings_override = override_settings(MEDIA_ROOT=self.temp_media_root)
		self.settings_override.enable()

	def tearDown(self):
		self.settings_override.disable()
		shutil.rmtree(self.temp_media_root, ignore_errors=True)

	def _post_csv(self, csv_text):
		csv_file = SimpleUploadedFile(
			'products.csv',
			csv_text.encode('utf-8'),
			content_type='text/csv',
		)
		return self.client.post(
			reverse('admin:store_product_import_csv'),
			{'csv_file': csv_file},
			follow=True,
		)

	def test_csv_import_attaches_existing_media_product_image(self):
		os.makedirs(os.path.join(self.temp_media_root, 'products'), exist_ok=True)
		local_image_path = os.path.join(self.temp_media_root, 'products', 'chair.jpg')
		with open(local_image_path, 'wb') as fh:
			fh.write(b'fake-jpeg-content')

		resp = self._post_csv(
			'name,slug,price,stock,categories,image\n'
			'Chair,chair,19.99,5,Decor,/media/products/chair.jpg\n'
		)
		self.assertEqual(resp.status_code, 200)

		product = Product.objects.get(slug='chair')
		self.assertEqual(product.images.count(), 1)
		self.assertEqual(product.images.first().image.name, 'products/chair.jpg')

	@patch('store.admin.requests.get')
	def test_csv_import_downloads_remote_image_url(self, mock_get):
		mock_response = Mock()
		mock_response.content = b'fake-png-content'
		mock_response.headers = {'Content-Type': 'image/png'}
		mock_response.raise_for_status = Mock()
		mock_get.return_value = mock_response

		resp = self._post_csv(
			'name,slug,price,stock,categories,image_url\n'
			'Lamp,lamp,29.99,2,Decor,https://example.com/lamp.png\n'
		)
		self.assertEqual(resp.status_code, 200)

		product = Product.objects.get(slug='lamp')
		self.assertEqual(product.images.count(), 1)
		image_name = product.images.first().image.name
		self.assertTrue(image_name.startswith('products/'))
		self.assertTrue(image_name.endswith('.png'))
		mock_get.assert_called_once()

	def test_csv_import_resolves_relative_path_from_uploaded_zip_archive(self):
		buffer = io.BytesIO()
		with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
			zf.writestr('usd_image_test_imgs/1_fa74956e7b.jpg', b'fake-jpg-content')
		buffer.seek(0)

		csv_file = SimpleUploadedFile(
			'products.csv',
			(
				'name,slug,price,stock,categories,image\n'
				'Wig Sample,wig-sample,39.99,8,Fashion,usd_image_test_imgs\\1_fa74956e7b.jpg\n'
			).encode('utf-8'),
			content_type='text/csv',
		)
		archive_file = SimpleUploadedFile('images.zip', buffer.read(), content_type='application/zip')

		resp = self.client.post(
			reverse('admin:store_product_import_csv'),
			{'csv_file': csv_file, 'image_archive': archive_file},
			follow=True,
		)
		self.assertEqual(resp.status_code, 200)

		product = Product.objects.get(slug='wig-sample')
		self.assertEqual(product.images.count(), 1)
		self.assertTrue(product.images.first().image.name.startswith('products/'))

	def test_csv_import_resolves_filename_from_auto_category_folder(self):
		from .models import Category
		category = Category.objects.create(name='Fashion', slug='fashion', is_active=True)

		category_raw = os.path.join(self.temp_media_root, 'products', 'categories', category.slug, 'raw')
		os.makedirs(category_raw, exist_ok=True)
		file_name = '1_fa74956e7b.jpg'
		with open(os.path.join(category_raw, file_name), 'wb') as fh:
			fh.write(b'fake-jpg-content')

		resp = self._post_csv(
			'name,slug,price,stock,categories,image\n'
			f'Category Folder Test,category-folder-test,49.99,3,Fashion,{file_name}\n'
		)
		self.assertEqual(resp.status_code, 200)

		product = Product.objects.get(slug='category-folder-test')
		self.assertEqual(product.images.count(), 1)
		self.assertTrue(product.images.first().image.name.startswith('products/'))

	def test_csv_import_long_slug_generates_db_safe_image_path(self):
		buffer = io.BytesIO()
		with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
			zf.writestr('hairs_images/sample.jpg', b'fake-jpg-content')
		buffer.seek(0)

		long_slug = 'ultra-long-product-' + ('very-long-segment-' * 20)
		csv_file = SimpleUploadedFile(
			'products.csv',
			(
				'name,slug,price,stock,categories,image\n'
				f'Long Name Product,{long_slug},59.99,6,Fashion,hairs_images\\sample.jpg\n'
			).encode('utf-8'),
			content_type='text/csv',
		)
		archive_file = SimpleUploadedFile('images.zip', buffer.read(), content_type='application/zip')

		resp = self.client.post(
			reverse('admin:store_product_import_csv'),
			{'csv_file': csv_file, 'image_archive': archive_file},
			follow=True,
		)
		self.assertEqual(resp.status_code, 200)

		product = Product.objects.get(slug=long_slug)
		self.assertEqual(product.images.count(), 1)
		image_name = product.images.first().image.name
		max_len = ProductImage._meta.get_field('image').max_length
		self.assertLessEqual(len(image_name), max_len)


class CategoryMediaStructureTests(TestCase):
	def setUp(self):
		self.temp_media_root = tempfile.mkdtemp(prefix='rukkie_media_category_')
		self.settings_override = override_settings(MEDIA_ROOT=self.temp_media_root)
		self.settings_override.enable()

	def tearDown(self):
		self.settings_override.disable()
		shutil.rmtree(self.temp_media_root, ignore_errors=True)

	def test_category_save_creates_media_structure(self):
		from .models import Category
		category = Category.objects.create(name='Decor', slug='decor', is_active=True)

		expected_paths = [
			os.path.join(self.temp_media_root, 'categories', category.slug),
			os.path.join(self.temp_media_root, 'products', 'categories', category.slug),
			os.path.join(self.temp_media_root, 'products', 'categories', category.slug, 'raw'),
			os.path.join(self.temp_media_root, 'products', 'categories', category.slug, 'processed'),
			os.path.join(self.temp_media_root, 'products', 'categories', category.slug, 'archive'),
			os.path.join(self.temp_media_root, 'imports', 'csv', category.slug),
		]
		for path in expected_paths:
			self.assertTrue(os.path.isdir(path), f'Expected directory missing: {path}')


class ProductReviewTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.product = Product.objects.create(
			name='Reviewable Product',
			slug='reviewable-product',
			price='25.00',
			stock=10,
			is_active=True,
		)

	def test_can_create_and_list_reviews(self):
		create_resp = self.client.post(
			'/api/products/slug/reviewable-product/reviews/',
			{
				'reviewer_name': 'Alice',
				'reviewer_email': 'alice@example.com',
				'rating': 4,
				'comment': 'Great quality and fast delivery.',
			},
			content_type='application/json',
		)
		self.assertEqual(create_resp.status_code, 201)
		self.product.refresh_from_db()
		self.assertEqual(self.product.review_count, 1)
		self.assertEqual(float(self.product.rating), 4.00)

		list_resp = self.client.get('/api/products/slug/reviewable-product/reviews/')
		self.assertEqual(list_resp.status_code, 200)
		rows = list_resp.json()
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]['display_name'], 'Alice')
		self.assertEqual(int(rows[0]['rating']), 4)


class MetadataReviewSeedTests(TestCase):
	def setUp(self):
		self.product = Product.objects.create(
			name='Meta Product',
			slug='meta-product',
			price='60.00',
			stock=8,
			is_active=True,
		)

	def test_metadata_generation_randomizes_review_fields(self):
		from .tasks import analyze_and_apply_image

		buf = io.BytesIO()
		image = Image.new('RGB', (800, 800), color='white')
		image.save(buf, format='JPEG')
		buf.seek(0)

		upload = SimpleUploadedFile('premium-modern-lamp.jpg', buf.read(), content_type='image/jpeg')
		pimg = ProductImage.objects.create(product=self.product, image=upload, alt='meta')

		result = analyze_and_apply_image(pimg.id)
		self.assertEqual(result.get('status'), 'ok')

		self.product.refresh_from_db()
		self.assertGreaterEqual(self.product.review_count, 20)
		self.assertGreaterEqual(float(self.product.rating), 3.0)
		self.assertLessEqual(float(self.product.rating), 5.0)
