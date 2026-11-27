"""Payment-link state transitions shared by the admin and public endpoints."""
import hashlib
import hmac
import logging
from datetime import timedelta
from urllib.parse import urlsplit
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.db.models import Case, CharField, F, Value, When
from django.urls import reverse
from django.utils import timezone

from .models import PaymentLink, PaymentLinkAttempt, PaymentLinkAudit, PaymentLinkNotice, PaymentLinkThrottle, PaymentTransaction
from .payment_link_gateways import GatewayError, verify_checkout


logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3
THROTTLE_WINDOW = timedelta(minutes=1)
STRIPE_MIN_TIME = timedelta(minutes=31)


def payment_origin():
    origin = settings.PAYMENT_LINK_ORIGIN
    url = urlsplit(origin)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment or url.path:
        raise ValueError('PAYMENT_LINK_ORIGIN must be a bare HTTPS origin.')
    return origin


def _token_signature(reference):
    return hmac.new(
        settings.PAYMENT_LINK_SIGNING_KEY.encode(),
        f'rukkies:payment-link:v1:{reference.hex}'.encode(),
        hashlib.sha256,
    ).hexdigest()


def payment_url(link):
    if len(settings.PAYMENT_LINK_SIGNING_KEY) < 32:
        raise ValueError('PAYMENT_LINK_SIGNING_KEY is missing.')
    token = f'{link.reference.hex}.{_token_signature(link.reference)}'
    return payment_origin() + reverse('payment-link-page', kwargs={'token': token})


def token_reference(token):
    if not isinstance(token, str) or not token.isascii() or len(token) != 97 or len(settings.PAYMENT_LINK_SIGNING_KEY) < 32:
        return None
    reference_hex, separator, signature = token.partition('.')
    if not separator or len(reference_hex) != 32 or len(signature) != 64:
        return None
    try:
        reference = UUID(hex=reference_hex)
    except ValueError:
        return None
    if reference.hex != reference_hex or not hmac.compare_digest(signature, _token_signature(reference)):
        return None
    return reference


def with_display_status(queryset):
    return queryset.annotate(display_status=Case(
        When(status__in=(PaymentLink.Status.PENDING, PaymentLink.Status.FAILED), expires_at__lte=timezone.now(),
             then=Value(PaymentLink.Status.EXPIRED)),
        default=F('status'), output_field=CharField(),
    ))


def display_status(link):
    if link.status in (PaymentLink.Status.PENDING, PaymentLink.Status.FAILED) and link.expires_at <= timezone.now():
        return PaymentLink.Status.EXPIRED
    return link.status


def can_send_invitation(link):
    return link.expires_at > timezone.now() and link.status in (
        PaymentLink.Status.PENDING, PaymentLink.Status.PROCESSING, PaymentLink.Status.FAILED,
    )


def rate_limit(scope, identity, limit):
    key = hashlib.sha256(f'{scope}:{identity}'.encode()).hexdigest()
    now = timezone.now()
    with transaction.atomic():
        bucket, _ = PaymentLinkThrottle.objects.select_for_update().get_or_create(
            key=key, defaults={'window_start': now},
        )
        if bucket.window_start <= now - THROTTLE_WINDOW:
            bucket.hits = 0
            bucket.window_start = now
        if bucket.hits >= limit:
            return False
        bucket.hits += 1
        bucket.save(update_fields=('hits', 'window_start'))
    return True


def audit(link, action, actor=None):
    PaymentLinkAudit.objects.create(link=link, action=action, actor=actor)


def enqueue_notice(link, kind, recipient):
    if not recipient:
        return
    from .tasks import deliver_payment_link_notice

    if kind == 'invitation':
        notice = PaymentLinkNotice.objects.create(link=link, kind=kind, recipient=recipient)
    else:
        notice, _ = PaymentLinkNotice.objects.get_or_create(link=link, kind=kind, defaults={'recipient': recipient})
    transaction.on_commit(lambda: deliver_payment_link_notice.delay(notice.pk), robust=True)


@transaction.atomic
def create_payment_link(*, actor, send_email=False, **fields):
    link = PaymentLink.objects.create(created_by=actor, **fields)
    url = payment_url(link)
    audit(link, 'created', actor)
    if send_email:
        enqueue_notice(link, 'invitation', link.customer_email)
        audit(link, 'invitation_queued', actor)
    return link, url


def reserve_attempt(reference):
    """Commit the reservation before making a provider call."""
    with transaction.atomic():
        link = PaymentLink.objects.select_for_update().get(reference=reference)
        state = display_status(link)
        if state not in (PaymentLink.Status.PENDING, PaymentLink.Status.FAILED):
            return None, state
        if link.attempts.count() >= MAX_ATTEMPTS:
            return None, 'attempt_limit'
        now = timezone.now()
        minimum = STRIPE_MIN_TIME if link.gateway == PaymentLink.Gateway.STRIPE else timedelta(minutes=2)
        if link.expires_at <= now + minimum:
            return None, 'too_late'
        session_length = timedelta(hours=23) if link.gateway == PaymentLink.Gateway.FLUTTERWAVE else timedelta(hours=2)
        attempt = PaymentLinkAttempt.objects.create(link=link, expires_at=min(link.expires_at, now + session_length))
        link.status = PaymentLink.Status.PROCESSING
        link.save(update_fields=('status',))
        audit(link, 'checkout_reserved')
        return attempt, link.status


def apply_verification(attempt, verified):
    if verified.state not in ('paid', 'failed') or not verified.transaction_id:
        return
    with transaction.atomic():
        # Every link-level transition takes locks in the same order.
        link = PaymentLink.objects.select_for_update().get(pk=attempt.link_id)
        attempt = PaymentLinkAttempt.objects.select_for_update().get(pk=attempt.pk)
        if attempt.status != PaymentLinkAttempt.Status.ACTIVE or link.status != PaymentLink.Status.PROCESSING:
            if verified.state == 'paid' and attempt.status != PaymentLinkAttempt.Status.PAID:
                logger.error('payment_link unexpected_capture attempt_id=%s', attempt.pk)
            return
        if verified.state == 'failed':
            attempt.status = PaymentLinkAttempt.Status.FAILED
            if not attempt.provider_session:
                attempt.provider_session = verified.transaction_id
            link.status = PaymentLink.Status.FAILED
            attempt.save(update_fields=('status', 'provider_session'))
            link.save(update_fields=('status',))
            audit(link, 'provider_confirmed_failure')
            return

        PaymentTransaction.objects.create(
            payment_link=link, provider=link.gateway, provider_transaction_id=verified.transaction_id,
            amount=link.amount, currency=link.currency, status='completed', success=True,
        )
        attempt.status = PaymentLinkAttempt.Status.PAID
        attempt.save(update_fields=('status',))
        link.status = PaymentLink.Status.PAID
        link.paid_at = timezone.now()
        link.save(update_fields=('status', 'paid_at'))
        audit(link, 'provider_confirmed_payment')
        enqueue_notice(link, 'confirmation', link.customer_email)
        enqueue_notice(link, 'receipt', link.customer_email)
        enqueue_notice(link, 'admin_payment', settings.PAYMENT_LINK_ADMIN_EMAIL)


def reconcile(attempt, hint='', *, throttle=True):
    if attempt.status != PaymentLinkAttempt.Status.ACTIVE:
        return
    if throttle:
        now = timezone.now()
        updated = PaymentLinkAttempt.objects.filter(pk=attempt.pk, status=PaymentLinkAttempt.Status.ACTIVE).filter(
            last_checked_at__isnull=True,
        ).update(last_checked_at=now)
        if not updated:
            updated = PaymentLinkAttempt.objects.filter(
                pk=attempt.pk, status=PaymentLinkAttempt.Status.ACTIVE,
                last_checked_at__lte=now - timedelta(seconds=15),
            ).update(last_checked_at=now)
        if not updated:
            return
    verified = verify_checkout(attempt, hint)
    apply_verification(attempt, verified)


def reconcile_link(link):
    attempt = link.attempts.filter(status=PaymentLinkAttempt.Status.ACTIVE).first()
    if attempt:
        try:
            reconcile(attempt)
        except GatewayError:
            return
        link.refresh_from_db()
