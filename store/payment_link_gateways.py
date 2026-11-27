"""Hosted checkout adapters for payment links."""
import base64
import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

import requests
import stripe
from django.conf import settings
from django.utils import timezone


CURRENCIES = {
    'stripe': ('USD', 'EUR', 'GBP', 'CAD', 'AUD'),
    'flutterwave': ('NGN', 'USD'),
}
FLUTTERWAVE_API = 'https://api.flutterwave.com/v3'


class GatewayError(Exception):
    """The provider couldn't confirm an operation."""


@dataclass(frozen=True)
class Verification:
    state: str = 'pending'
    transaction_id: str = ''


def stripe_payload(value):
    if isinstance(value, dict):
        return value
    if hasattr(value, 'to_dict_recursive'):
        return value.to_dict_recursive()
    return value.to_dict()


def available_gateways():
    if len(settings.PAYMENT_LINK_SIGNING_KEY) < 32:
        return {}
    enabled = {}
    if settings.STRIPE_SECRET_KEY and settings.PAYMENT_LINK_STRIPE_WEBHOOK_SECRET:
        enabled['stripe'] = CURRENCIES['stripe']
    if settings.FLUTTERWAVE_SECRET_KEY and _flutterwave_webhook_secret():
        enabled['flutterwave'] = CURRENCIES['flutterwave']
    return enabled


def _flutterwave(method, path, **kwargs):
    try:
        response = requests.request(
            method, FLUTTERWAVE_API + path,
            headers={'Authorization': f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}'},
            timeout=(4, 12), allow_redirects=False, **kwargs,
        )
        response.raise_for_status()
        body = response.json()
        if body.get('status') != 'success':
            raise GatewayError
        return body.get('data')
    except (requests.RequestException, ValueError, AttributeError):
        raise GatewayError from None


def _checkout_url(value, host):
    parsed = urlsplit(str(value or ''))
    if parsed.scheme != 'https' or parsed.netloc != host or not parsed.path:
        raise GatewayError
    return parsed.geturl()


def create_checkout(attempt, return_url):
    link = attempt.link
    reference = attempt.reference.hex
    try:
        if link.gateway == 'stripe':
            metadata = {'payment_link_attempt': reference}
            session = stripe_payload(stripe.checkout.Session.create(
                api_key=settings.STRIPE_SECRET_KEY,
                idempotency_key=f'rukkies-payment-link-{reference}',
                mode='payment',
                payment_method_types=['card'],
                customer_email=link.customer_email,
                client_reference_id=reference,
                metadata=metadata,
                payment_intent_data={'metadata': metadata},
                expires_at=int(attempt.expires_at.timestamp()),
                success_url=return_url,
                cancel_url=return_url,
                line_items=[{
                    'price_data': {
                        'currency': link.currency.lower(),
                        'unit_amount': int(link.amount * 100),
                        'product_data': {'name': link.description},
                    },
                    'quantity': 1,
                }],
            ))
            session_id = str(session.get('id') or '')
            if not session_id.startswith('cs_'):
                raise GatewayError
            return session_id, _checkout_url(session.get('url'), 'checkout.stripe.com')

        # Standard closes its hosted checkout after success. A lost create response
        # is left reserved, because v3 does not promise an idempotency header here.
        expires = attempt.expires_at.astimezone(UTC)
        data = _flutterwave('POST', '/payments', json={
            'tx_ref': f'pl-{reference}',
            'amount': str(link.amount),
            'currency': link.currency,
            'redirect_url': return_url,
            'customer': {'email': link.customer_email, 'name': link.customer_name},
            'customizations': {'title': 'De-Rukkies Collections', 'description': link.description},
            'payment_options': 'card',
            'link_expiration': expires.isoformat(),
            'configurations': {
                'session_duration': max(1, int((expires - timezone.now()).total_seconds()) // 60),
                'max_retry_attempt': 3,
            },
        })
        return '', _checkout_url(data.get('link'), 'checkout.flutterwave.com')
    except (stripe.StripeError, AttributeError, TypeError, ValueError):
        raise GatewayError from None


def _stripe_verification(attempt, hint):
    link = attempt.link
    session_id = attempt.provider_session or hint
    if not session_id or not session_id.startswith('cs_'):
        return Verification()
    session = stripe_payload(stripe.checkout.Session.retrieve(session_id, api_key=settings.STRIPE_SECRET_KEY))
    reference = attempt.reference.hex
    if (
        session.get('id') != session_id
        or session.get('client_reference_id') != reference
        or (session.get('metadata') or {}).get('payment_link_attempt') != reference
        or session.get('mode') != 'payment'
        or session.get('amount_total') != int(link.amount * 100)
        or (session.get('currency') or '').upper() != link.currency
    ):
        raise GatewayError
    if session.get('status') == 'expired' and session.get('payment_status') == 'unpaid':
        return Verification('failed', session_id)
    if session.get('status') != 'complete' or session.get('payment_status') != 'paid':
        return Verification()

    intent_id = str(session.get('payment_intent') or '')
    if not intent_id.startswith('pi_'):
        raise GatewayError
    intent = stripe_payload(stripe.PaymentIntent.retrieve(intent_id, api_key=settings.STRIPE_SECRET_KEY))
    if (
        intent.get('id') != intent_id
        or (intent.get('metadata') or {}).get('payment_link_attempt') != reference
        or intent.get('amount_received') != int(link.amount * 100)
        or (intent.get('currency') or '').upper() != link.currency
        or intent.get('status') != 'succeeded'
    ):
        raise GatewayError
    return Verification('paid', intent_id)


def _flutterwave_verification(attempt, hint):
    link = attempt.link
    reference = f'pl-{attempt.reference.hex}'
    if hint and hint.isascii() and hint.isdecimal():
        data = _flutterwave('GET', f'/transactions/{hint}/verify')
    else:
        data = _flutterwave('GET', '/transactions/verify_by_reference', params={'tx_ref': reference})
    txn_id = str(data.get('id') or '')
    if (
        not txn_id.isascii() or not txn_id.isdecimal()
        or (hint and hint != txn_id)
        or data.get('tx_ref') != reference
        or str(data.get('currency') or '').upper() != link.currency
        or Decimal(str(data.get('amount'))) != link.amount
    ):
        raise GatewayError
    state = str(data.get('status') or '').lower()
    if state == 'successful':
        return Verification('paid', txn_id)
    if state in ('failed', 'cancelled') and attempt.checkout_url and timezone.now() >= attempt.expires_at + timedelta(minutes=2):
        # A failed charge while Standard is still open can be retried there. Only
        # release the reservation once the old checkout has been disabled.
        disabled = _flutterwave('POST', '/payments/link/disable', json={'link': attempt.checkout_url})
        if disabled is not True:
            raise GatewayError
        final = _flutterwave('GET', '/transactions/verify_by_reference', params={'tx_ref': reference})
        final_id = str(final.get('id') or '')
        if final.get('tx_ref') != reference or Decimal(str(final.get('amount'))) != link.amount or final.get('currency') != link.currency:
            raise GatewayError
        if not final_id.isascii() or not final_id.isdecimal():
            raise GatewayError
        final_status = str(final.get('status') or '').lower()
        if final_status == 'successful':
            return Verification('paid', final_id)
        if final_status in ('failed', 'cancelled'):
            return Verification('failed', final_id)
    return Verification()


def verify_checkout(attempt, hint=''):
    try:
        if attempt.link.gateway == 'stripe':
            return _stripe_verification(attempt, hint)
        return _flutterwave_verification(attempt, hint)
    except (stripe.StripeError, InvalidOperation, AttributeError, TypeError, ValueError):
        raise GatewayError from None


def _flutterwave_webhook_secret():
    return settings.PAYMENT_LINK_FLUTTERWAVE_WEBHOOK_SECRET or settings.FLUTTERWAVE_WEBHOOK_SECRET


def valid_flutterwave_signature(request):
    secret = _flutterwave_webhook_secret()
    if not secret:
        return False
    signature = request.headers.get('flutterwave-signature', '')
    if signature:
        digest = hmac.new(secret.encode(), request.body, hashlib.sha256).digest()
        return hmac.compare_digest(signature.encode(), base64.b64encode(digest))
    legacy = request.headers.get('verif-hash', '')
    return bool(legacy) and hmac.compare_digest(legacy.encode(), secret.encode())
