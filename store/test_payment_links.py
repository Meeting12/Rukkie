import hashlib
import hmac
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.db import IntegrityError, close_old_connections, transaction
from django.test import Client, TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from .email_delivery import LOGO_CONTENT_ID
from .models import Order, PaymentLink, PaymentLinkAttempt, PaymentLinkNotice, PaymentTransaction
from .payment_link_gateways import GatewayError, Verification
from .payment_links import apply_verification, payment_url, reserve_attempt
from .tasks import deliver_payment_link_notice


CONFIG = dict(
    PAYMENT_LINK_ORIGIN='https://rukkies.com', PAYMENT_LINK_SIGNING_KEY='unit-test-key-with-enough-characters',
    STRIPE_SECRET_KEY='sk_test_paymentlinks', PAYMENT_LINK_STRIPE_WEBHOOK_SECRET='whsec_paymentlinks',
    FLUTTERWAVE_SECRET_KEY='FLWSECK_TEST-paymentlinks', PAYMENT_LINK_FLUTTERWAVE_WEBHOOK_SECRET='flutterwave-paymentlinks',
    PAYMENT_LINK_ADMIN_EMAIL='operations@example.test', CONTACT_RECIPIENT_EMAIL='support@example.test',
)


def link_factory(**overrides):
    fields = dict(
        customer_name='Sample Customer', customer_email='customer@example.test',
        amount='25.00', currency='USD', description='Custom order', gateway='stripe',
        expires_at=timezone.now() + timedelta(days=1),
    )
    return PaymentLink.objects.create(**(fields | overrides))


@override_settings(
    **CONFIG,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class PaymentLinkTests(TestCase):
    def post(self, path, payload, client=None, **headers):
        return (client or self.client).post(
            path, json.dumps(payload), content_type='application/json', secure=True, **headers,
        )

    def token(self, link):
        return payment_url(link).rsplit('/', 1)[-1]

    def stripe_event(self, attempt, event='checkout.session.completed', valid=True):
        payload = json.dumps({
            'id': 'evt_unit_test', 'object': 'event', 'type': event,
            'data': {'object': {'object': 'checkout.session', 'id': 'cs_test_paymentlink', 'metadata': {
                'payment_link_attempt': attempt.reference.hex,
            }}},
        })
        timestamp = str(int(time.time()))
        signature = hmac.new(CONFIG['PAYMENT_LINK_STRIPE_WEBHOOK_SECRET'].encode(), f'{timestamp}.{payload}'.encode(), hashlib.sha256).hexdigest()
        return self.client.post(
            reverse('payment-link-stripe-webhook'), payload, content_type='application/json', secure=True,
            HTTP_STRIPE_SIGNATURE=f't={timestamp},v1={signature if valid else "bad"}',
        )

    def test_admin_creation_uses_staff_permission_and_csrf(self):
        url = reverse('payment-link-admin-create')
        payload = {
            'customer_name': 'Customer', 'customer_email': 'customer@example.test', 'amount': '10.00',
            'currency': 'USD', 'gateway': 'stripe', 'description': 'Request',
            'expires_at': (timezone.now() + timedelta(days=1)).isoformat(), 'send_email': True,
        }
        self.assertEqual(self.post(url, payload).status_code, 403)
        admin = get_user_model().objects.create_superuser('manager', 'manager@example.test', 'test-password')
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(admin)
        self.assertEqual(self.post(url, payload, browser).status_code, 403)
        config = browser.get(reverse('payment-link-admin-config'), secure=True)
        self.assertEqual(config.status_code, 200)
        with self.captureOnCommitCallbacks() as callbacks:
            result = self.post(
                url, payload, browser, HTTP_X_CSRFTOKEN=browser.cookies['csrftoken'].value, HTTP_ORIGIN='https://testserver',
            )
        self.assertEqual(result.status_code, 201)
        self.assertTrue(result.json()['url'].startswith('https://rukkies.com/pay/'))
        self.assertEqual(PaymentLinkNotice.objects.get().kind, 'invitation')
        self.assertEqual(PaymentLink.objects.get().created_by, admin)
        self.assertEqual(len(callbacks), 1)
        self.assertContains(browser.get(reverse('admin:store_paymentlink_changelist'), secure=True), 'Copy link')
        self.assertContains(browser.get(reverse('admin:store_paymentlink_details', args=[PaymentLink.objects.get().pk]), secure=True), 'Audit trail')

    def test_generate_button_and_server_form_require_add_permission(self):
        staff = get_user_model().objects.create_user('payment-staff', is_staff=True)
        staff.user_permissions.add(Permission.objects.get(content_type__app_label='store', codename='view_paymentlink'))
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(staff)
        index = reverse('admin:index')
        listing = reverse('admin:store_paymentlink_changelist')
        form_url = reverse('admin:store_paymentlink_add')

        self.assertNotContains(browser.get(index, secure=True), 'data-payment-link-generator')
        self.assertContains(browser.get(listing, secure=True), 'Generating links requires the Add payment link permission.')
        self.assertEqual(browser.get(form_url, secure=True).status_code, 403)

        staff.user_permissions.add(Permission.objects.get(content_type__app_label='store', codename='add_paymentlink'))
        for path in (index, listing):
            page = browser.get(path, secure=True)
            self.assertContains(page, f'href="{form_url}" data-payment-link-generator>Generate Payment Link</a>')

        form = browser.get(form_url, secure=True)
        self.assertContains(form, 'Customer full name')
        fields = {
            'customer_name': 'Form Customer', 'customer_email': 'customer@example.test',
            'amount': '25.00', 'gateway': 'stripe', 'currency': 'USD', 'description': 'Custom order',
            'expires_at': timezone.localtime(timezone.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'),
            'send_email': 'on',
        }
        origin = {'HTTP_ORIGIN': 'https://testserver'}
        self.assertEqual(browser.post(form_url, fields, secure=True, **origin).status_code, 403)
        with self.captureOnCommitCallbacks() as callbacks:
            result = browser.post(form_url, fields, secure=True, **origin, HTTP_X_CSRFTOKEN=browser.cookies['csrftoken'].value)
        link = PaymentLink.objects.get()
        self.assertEqual(link.created_by, staff)
        self.assertContains(result, payment_url(link))
        self.assertEqual(link.audit.get(action='created').actor, staff)
        self.assertEqual(PaymentLinkNotice.objects.get().kind, 'invitation')
        self.assertEqual(len(callbacks), 1)

    @override_settings(PAYMENT_LINK_SIGNING_KEY='')
    def test_generate_button_is_visible_even_when_gateways_are_disabled(self):
        admin = get_user_model().objects.create_superuser('manager', 'manager@example.test', 'test-password')
        self.client.force_login(admin)
        self.assertContains(self.client.get(reverse('admin:index'), secure=True), 'Generate Payment Link')
        self.assertContains(self.client.get(reverse('admin:store_paymentlink_add'), secure=True), 'Payment gateways are unavailable.')

    def test_http_admin_explains_https_requirement_and_rejects_creation(self):
        admin = get_user_model().objects.create_superuser('local-manager', 'manager@example.test', 'test-password')
        self.client.force_login(admin)
        form_url = reverse('admin:store_paymentlink_add')
        self.assertContains(self.client.get(form_url), 'Open the admin over HTTPS')
        self.assertEqual(self.client.post(form_url, {'amount': '25.00'}).status_code, 403)
        self.assertFalse(PaymentLink.objects.exists())

    def test_public_page_has_no_cache_and_no_referrer(self):
        link = link_factory()
        page = self.client.get(reverse('payment-link-page', args=[self.token(link)]), secure=True)
        self.assertContains(page, 'payment-link-page.js')
        self.assertEqual(page['Cache-Control'], 'private, no-store')
        self.assertEqual(page['Referrer-Policy'], 'no-referrer')
        self.assertIn('csrftoken', page.cookies)

    def test_invalid_expired_and_revoked_links_are_unpayable(self):
        expired = link_factory(expires_at=timezone.now() - timedelta(seconds=1))
        revoked = link_factory(status='revoked')
        detail = reverse('payment-link-detail')
        start = reverse('payment-link-start')
        self.assertEqual(self.post(detail, {'token': 'abc'}).status_code, 404)
        self.assertEqual(self.post(detail, {'token': self.token(expired)}).json()['status'], 'expired')
        self.assertEqual(self.post(detail, {'token': self.token(revoked)}).json()['status'], 'revoked')
        self.assertEqual(self.post(start, {'token': self.token(expired)}).status_code, 409)
        self.assertEqual(self.post(start, {'token': self.token(revoked)}).status_code, 409)
        self.assertFalse(PaymentLinkAttempt.objects.exists())

    def test_revoke_freezes_unused_link_and_writes_audit(self):
        link = link_factory()
        admin = get_user_model().objects.create_superuser('manager', 'manager@example.test', 'test-password')
        self.client.force_login(admin)
        response = self.post(reverse('payment-link-admin-revoke', args=[link.reference]), {})
        self.assertEqual(response.json()['status'], 'revoked')
        self.assertEqual(link.audit.get(action='revoked').actor, admin)
        self.assertEqual(self.post(reverse('payment-link-start'), {'token': self.token(link)}).status_code, 409)

    @patch('store.payment_link_views.create_checkout', return_value=('cs_test_paymentlink', 'https://checkout.stripe.com/c/pay/test'))
    @patch('store.payment_links.verify_checkout', return_value=Verification())
    def test_one_hosted_checkout_and_server_controlled_amount(self, verify, create):
        link = link_factory()
        url = reverse('payment-link-start')
        payload = {'token': self.token(link), 'amount': '0.01', 'currency': 'EUR'}
        result = self.post(url, payload)
        self.assertEqual(result.status_code, 200)
        first = create.call_args.args[0]
        self.assertEqual(str(first.link.amount), '25.00')
        self.assertEqual(first.link.currency, 'USD')
        self.assertEqual(self.post(url, payload, Client()).status_code, 409)
        self.assertEqual(self.post(url, payload).json()['checkout_url'], result.json()['checkout_url'])
        create.assert_called_once()
        self.assertEqual(link.attempts.count(), 1)

    def test_confirmed_failure_releases_attempt_with_limit(self):
        link = link_factory()
        for number in range(3):
            attempt, status = reserve_attempt(link.reference)
            self.assertEqual(status, 'processing')
            apply_verification(attempt, Verification('failed', f'cs_test_{number}'))
            self.assertEqual(PaymentLink.objects.get(pk=link.pk).status, 'failed')
        self.assertEqual(reserve_attempt(link.reference), (None, 'attempt_limit'))
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_checkout_unknown_result_stays_reserved(self):
        link = link_factory()
        with patch('store.payment_link_views.create_checkout', side_effect=GatewayError):
            result = self.post(reverse('payment-link-start'), {'token': self.token(link)})
        self.assertEqual(result.status_code, 202)
        self.assertEqual(reserve_attempt(link.reference), (None, 'processing'))

    @patch('store.payment_link_gateways.stripe.PaymentIntent.retrieve')
    @patch('store.payment_link_gateways.stripe.checkout.Session.retrieve')
    def test_signed_stripe_webhook_confirms_provider_data_only_once(self, retrieve_session, retrieve_intent):
        link = link_factory()
        attempt, _ = reserve_attempt(link.reference)
        metadata = {'payment_link_attempt': attempt.reference.hex}
        retrieve_session.return_value = {
            'metadata': metadata, 'client_reference_id': attempt.reference.hex, 'id': 'cs_test_paymentlink',
            'mode': 'payment', 'status': 'complete', 'payment_status': 'unpaid', 'currency': 'usd',
            'amount_total': 2500, 'payment_intent': 'pi_test_paymentlink',
        }
        retrieve_intent.return_value = {
            'id': 'pi_test_paymentlink', 'metadata': metadata, 'amount_received': 2500, 'currency': 'usd', 'status': 'succeeded',
        }
        self.assertEqual(self.stripe_event(attempt, valid=False).status_code, 400)
        retrieve_session.assert_not_called()
        self.assertEqual(self.stripe_event(attempt).status_code, 200)
        self.assertEqual(PaymentLink.objects.get(pk=link.pk).status, 'processing')
        retrieve_session.return_value['payment_status'] = 'paid'
        retrieve_intent.return_value['currency'] = 'eur'
        self.assertEqual(self.stripe_event(attempt).status_code, 503)
        self.assertFalse(PaymentTransaction.objects.exists())
        retrieve_intent.return_value['currency'] = 'usd'
        self.assertEqual(self.stripe_event(attempt).status_code, 200)
        self.assertEqual(self.stripe_event(attempt).status_code, 200)
        link.refresh_from_db()
        self.assertEqual(link.status, 'paid')
        self.assertEqual(link.transactions.count(), 1)
        self.assertIsNone(link.transactions.get().order_id)
        self.assertEqual(set(PaymentLinkNotice.objects.values_list('kind', flat=True)), {'confirmation', 'receipt', 'admin_payment'})
        paid = self.post(reverse('payment-link-detail'), {'token': self.token(link)}).json()
        self.assertEqual(paid['status'], 'paid')
        self.assertNotIn('name', paid)
        self.assertEqual(self.post(reverse('payment-link-start'), {'token': self.token(link)}).status_code, 409)

    @patch('store.payment_link_gateways._flutterwave')
    def test_signed_flutterwave_reference_verified_on_legacy_endpoint(self, provider):
        link = link_factory(gateway='flutterwave', currency='NGN')
        attempt, _ = reserve_attempt(link.reference)
        ref = f'pl-{attempt.reference.hex}'
        payload = {'event': 'charge.completed', 'data': {'tx_ref': ref, 'id': 911, 'status': 'successful'}}
        provider.return_value = {'tx_ref': ref, 'id': 911, 'status': 'successful', 'currency': 'NGN', 'amount': '20.00'}
        endpoint = '/api/payments/webhook/flutterwave/'
        self.assertEqual(self.post(endpoint, payload).status_code, 400)
        provider.assert_not_called()
        signature = dict(HTTP_VERIF_HASH=CONFIG['PAYMENT_LINK_FLUTTERWAVE_WEBHOOK_SECRET'])
        self.assertEqual(self.post(endpoint, payload, **signature).status_code, 503)
        self.assertFalse(PaymentTransaction.objects.exists())
        provider.return_value['amount'] = '25.00'
        self.assertEqual(self.post(endpoint, payload, **signature).status_code, 200)
        self.assertEqual(self.post(endpoint, payload, **signature).status_code, 200)
        self.assertEqual(link.transactions.get().provider_transaction_id, '911')

    def test_notices_deliver_once_with_receipt_attachment(self):
        link = link_factory(description='Custom <order>', order_reference='ORDER-123')
        invitation = PaymentLinkNotice.objects.create(link=link, kind='invitation', recipient=link.customer_email)
        deliver_payment_link_notice.run(invitation.pk)
        deliver_payment_link_notice.run(invitation.pk)
        self.assertEqual(len(mail.outbox), 1)
        url = payment_url(link)
        email = mail.outbox[0]
        self.assertIn(url, email.body)
        html = email.alternatives[0].content
        self.assertIn('De-Rukkies Collections', html)
        self.assertIn('Open Secure Payment Page', html)
        self.assertIn(f'href="{url}"', html)
        self.assertIn('Custom &lt;order&gt;', html)
        self.assertIn('Amount due', html)
        self.assertIn('USD 25.00', html)
        self.assertIn('ORDER-123', html)
        self.assertIn('Expires', html)
        self.assertIn('mailto:support@example.test', html)

        attempt, _ = reserve_attempt(link.reference)
        apply_verification(attempt, Verification('paid', 'pi_receipt'))
        for kind in ('confirmation', 'receipt', 'admin_payment'):
            with self.subTest(kind=kind):
                notice = PaymentLinkNotice.objects.get(kind=kind)
                deliver_payment_link_notice.run(notice.pk)
                email = mail.outbox[-1]
                html = email.alternatives[0].content
                self.assertIn('De-Rukkies Collections', html)
                self.assertIn('Amount paid', html)
                self.assertIn('Sample Customer', html)
                self.assertNotIn(url, html)
                self.assertNotIn(url, email.body)
                self.assertNotIn('Open Secure Payment Page', html)
                if kind == 'receipt':
                    self.assertTrue(any(attachment.filename.endswith('.html') for attachment in email.attachments))
                    body, attachment = email.message().get_payload()
                    self.assertEqual(attachment.get_content_disposition(), 'attachment')
                    related = body.get_payload(1)
                    self.assertEqual(related.get_content_type(), 'multipart/related')
                    self.assertEqual(related.get_payload(1)['Content-ID'], f'<{LOGO_CONTENT_ID}>')
        self.assertEqual(len(mail.outbox), 4)

    def test_invitation_can_send_and_resend_while_checkout_is_processing(self):
        link = link_factory()
        invitation = PaymentLinkNotice.objects.create(link=link, kind='invitation', recipient=link.customer_email)
        attempt, _ = reserve_attempt(link.reference)
        deliver_payment_link_notice.run(invitation.pk)
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.sent_at)
        self.assertIn(payment_url(link), mail.outbox[0].body)

        admin = get_user_model().objects.create_superuser('manager', 'manager@example.test', 'test-password')
        self.client.force_login(admin)
        detail = self.client.get(reverse('admin:store_paymentlink_details', args=[link.pk]), secure=True)
        self.assertContains(detail, 'data-payment-link-action="send"')
        self.assertNotContains(detail, 'data-payment-link-action="revoke"')
        with self.captureOnCommitCallbacks() as callbacks:
            response = self.post(reverse('payment-link-admin-send', args=[link.reference]), {})
        self.assertEqual(response.json(), {'email_queued': True})
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(PaymentLinkNotice.objects.filter(link=link).count(), 2)
        self.assertEqual(reserve_attempt(link.reference), (None, 'processing'))
        self.assertEqual(link.attempts.get().pk, attempt.pk)

    def test_invitation_cancels_for_expired_processing_link(self):
        link = link_factory(status='processing', expires_at=timezone.now() - timedelta(seconds=1))
        invitation = PaymentLinkNotice.objects.create(link=link, kind='invitation', recipient=link.customer_email)
        deliver_payment_link_notice.run(invitation.pk)
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.cancelled_at)
        self.assertIsNone(invitation.sent_at)
        self.assertEqual(len(mail.outbox), 0)

    def test_database_refuses_two_active_attempts_and_two_successes(self):
        link = link_factory()
        attempt, _ = reserve_attempt(link.reference)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PaymentLinkAttempt.objects.create(link=link, expires_at=attempt.expires_at)
        apply_verification(attempt, Verification('paid', 'pi_first'))
        with self.assertRaises(IntegrityError), transaction.atomic():
            PaymentTransaction.objects.create(
                payment_link=link, provider='stripe', provider_transaction_id='pi_second',
                amount=link.amount, success=True,
            )

    @override_settings(PAYMENT_VERIFY_TOKEN='internal-test-verification')
    def test_link_payment_cannot_be_reused_for_an_order(self):
        link = link_factory()
        attempt, _ = reserve_attempt(link.reference)
        apply_verification(attempt, Verification('paid', 'pi_already_assigned'))
        user = get_user_model().objects.create_user('order-owner')
        order = Order.objects.create(user=user, total=link.amount)
        self.client.force_login(user)
        response = self.post('/api/payments/verify/', {
            'order_id': order.pk, 'provider': 'stripe', 'transaction_id': 'pi_already_assigned',
            'verify_token': 'internal-test-verification',
        })
        self.assertEqual(response.json(), {'error': 'order_mismatch'})
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PENDING)


@override_settings(**CONFIG)
class PaymentLinkConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_concurrent_reservations_and_success_callbacks(self):
        link = link_factory()

        def parallel(operation):
            barrier = Barrier(2)

            def invoke():
                close_old_connections()
                try:
                    barrier.wait(timeout=10)
                    return operation()
                finally:
                    close_old_connections()

            with ThreadPoolExecutor(max_workers=2) as pool:
                return [future.result(timeout=20) for future in (pool.submit(invoke), pool.submit(invoke))]

        results = parallel(lambda: reserve_attempt(link.reference))
        self.assertEqual(sum(attempt is not None for attempt, _ in results), 1)
        attempt = link.attempts.get()
        with patch('store.tasks.deliver_payment_link_notice.delay'):
            parallel(lambda: apply_verification(attempt, Verification('paid', 'pi_concurrent')))
        self.assertEqual(link.transactions.count(), 1)
        self.assertEqual(PaymentLinkNotice.objects.filter(link=link).count(), 3)
