import json
from uuid import UUID

import stripe
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import PaymentLink, PaymentLinkAttempt
from .payment_link_gateways import GatewayError, available_gateways, create_checkout, stripe_payload, valid_flutterwave_signature
from .payment_link_serializers import PaymentLinkCreateSerializer
from .payment_links import (
    audit, can_send_invitation, create_payment_link, display_status, enqueue_notice,
    payment_origin, rate_limit, reconcile, reconcile_link, reserve_attempt, token_reference,
)


def _payload(request):
    if request.content_type != 'application/json':
        return {}
    try:
        body = json.loads(request.body)
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _staff(request, permission):
    user = request.user
    if not (request.is_secure() and user.is_active and user.is_staff and user.has_perm(f'store.{permission}_paymentlink')):
        raise PermissionDenied


def _public_link(request):
    if not request.is_secure():
        return None, JsonResponse({'status': 'invalid'}, status=404)
    reference = token_reference(_payload(request).get('token'))
    link = PaymentLink.objects.filter(reference=reference).first() if reference else None
    if not link:
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        if not rate_limit('invalid_public', ip, 60):
            return None, _limited()
        return None, JsonResponse({'status': 'invalid'}, status=404)
    if not rate_limit('public', reference, 90):
        return None, _limited()
    return link, None


def _limited():
    return JsonResponse({'detail': 'Too many requests. Try again shortly.'}, status=429)


@never_cache
@ensure_csrf_cookie
@require_GET
def payment_page(request, token=None):
    if not request.is_secure():
        return HttpResponse(status=404)
    return render(request, 'payment_link_page.html')


@never_cache
@ensure_csrf_cookie
@require_GET
def staff_config(request):
    _staff(request, 'add')
    return JsonResponse({'gateways': available_gateways()})


@never_cache
@require_POST
@csrf_protect
def staff_create(request):
    _staff(request, 'add')
    if not rate_limit('staff_create', request.user.pk, 15):
        return _limited()
    serializer = PaymentLinkCreateSerializer(data=_payload(request))
    if not serializer.is_valid():
        return JsonResponse({'errors': serializer.errors}, status=400)
    try:
        link, url = create_payment_link(actor=request.user, **serializer.validated_data)
    except ValueError:
        return JsonResponse({'detail': 'The payment link URL is not configured.'}, status=503)
    return JsonResponse({
        'reference': str(link.reference), 'url': url, 'email_queued': serializer.validated_data['send_email'],
    }, status=201)


@never_cache
@require_GET
def staff_detail(request, reference):
    _staff(request, 'view')
    link = get_object_or_404(PaymentLink, reference=reference)
    return JsonResponse({
        'reference': str(link.reference), 'status': display_status(link), 'gateway': link.gateway,
        'amount': str(link.amount), 'currency': link.currency, 'expires_at': link.expires_at,
    })


@never_cache
@require_POST
@csrf_protect
def staff_revoke(request, reference):
    _staff(request, 'change')
    if not rate_limit('staff_revoke', request.user.pk, 20):
        return _limited()
    with transaction.atomic():
        link = get_object_or_404(PaymentLink.objects.select_for_update(), reference=reference)
        if display_status(link) not in (PaymentLink.Status.PENDING, PaymentLink.Status.FAILED):
            return JsonResponse({'detail': 'Only unused links without a checkout in progress can be revoked.'}, status=409)
        link.status = PaymentLink.Status.REVOKED
        link.save(update_fields=('status',))
        audit(link, 'revoked', request.user)
    return JsonResponse({'status': link.status})


@never_cache
@require_POST
@csrf_protect
def staff_send(request, reference):
    _staff(request, 'change')
    if not rate_limit('staff_send', request.user.pk, 12) or not rate_limit('invitation', reference, 2):
        return _limited()
    with transaction.atomic():
        link = get_object_or_404(PaymentLink.objects.select_for_update(), reference=reference)
        if not can_send_invitation(link):
            return JsonResponse({'detail': 'This link is unavailable for sending.'}, status=409)
        enqueue_notice(link, 'invitation', link.customer_email)
        audit(link, 'invitation_queued', request.user)
    return JsonResponse({'email_queued': True})


def _resumable_attempt(request, link):
    attempt_id = request.session.get('payment_link_attempt')
    if attempt_id:
        return link.attempts.filter(
            pk=attempt_id, status=PaymentLinkAttempt.Status.ACTIVE, expires_at__gt=timezone.now(),
        ).exclude(checkout_url='').first()
    return None


@never_cache
@require_POST
@csrf_protect
def public_detail(request):
    link, error = _public_link(request)
    if error:
        return error
    if link.status == PaymentLink.Status.PROCESSING:
        reconcile_link(link)
    status = display_status(link)
    response = {'status': status, 'support': settings.CONTACT_RECIPIENT_EMAIL}
    if status in (PaymentLink.Status.PENDING, PaymentLink.Status.FAILED, PaymentLink.Status.PROCESSING):
        response.update({
            'reference': str(link.reference), 'name': link.customer_name, 'description': link.description,
            'amount': str(link.amount), 'currency': link.currency,
            'can_resume': status == PaymentLink.Status.PROCESSING and bool(_resumable_attempt(request, link)),
        })
    return JsonResponse(response)


@never_cache
@require_POST
@csrf_protect
def public_start(request):
    link, error = _public_link(request)
    if error:
        return error
    if not rate_limit('start', link.reference, 8):
        return _limited()
    if link.gateway not in available_gateways():
        return JsonResponse({'detail': 'Checkout is temporarily unavailable.'}, status=503)
    if link.status == PaymentLink.Status.PROCESSING:
        reconcile_link(link)
        if link.status == PaymentLink.Status.PROCESSING:
            attempt = _resumable_attempt(request, link)
            if attempt:
                return JsonResponse({'status': 'processing', 'checkout_url': attempt.checkout_url})
    attempt, state = reserve_attempt(link.reference)
    if not attempt:
        return JsonResponse({'status': state}, status=409)
    request.session['payment_link_attempt'] = attempt.pk
    try:
        session, url = create_checkout(attempt, payment_origin() + reverse('payment-link-return'))
    except (GatewayError, ValueError):
        return JsonResponse({'status': 'processing', 'detail': 'Checkout is awaiting confirmation. Contact support if it stays here.'}, status=202)
    recorded = PaymentLinkAttempt.objects.filter(pk=attempt.pk, status=PaymentLinkAttempt.Status.ACTIVE).update(
        provider_session=session, checkout_url=url,
    )
    if not recorded:
        link.refresh_from_db()
        return JsonResponse({'status': link.status}, status=409)
    return JsonResponse({'status': 'processing', 'checkout_url': url})


def _attempt(gateway, reference):
    try:
        reference = UUID(str(reference))
    except (ValueError, TypeError):
        return None
    return PaymentLinkAttempt.objects.select_related('link').filter(reference=reference, link__gateway=gateway).first()


def _handle_event(attempt, hint):
    if attempt:
        try:
            reconcile(attempt, hint, throttle=False)
        except GatewayError:
            return HttpResponse(status=503)
    return HttpResponse(status=200)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    secret = settings.PAYMENT_LINK_STRIPE_WEBHOOK_SECRET
    if not request.is_secure() or not secret:
        return HttpResponse(status=503)
    try:
        event = stripe_payload(stripe.Webhook.construct_event(request.body, request.headers.get('Stripe-Signature', ''), secret))
        data = event['data']['object']
        reference = (data.get('metadata') or {}).get('payment_link_attempt')
    except (ValueError, stripe.StripeError, KeyError, TypeError, AttributeError):
        return HttpResponse(status=400)
    if event.get('type') not in ('checkout.session.completed', 'checkout.session.expired', 'checkout.session.async_payment_succeeded'):
        return HttpResponse(status=200)
    return _handle_event(_attempt('stripe', reference), str(data.get('id') or ''))


@csrf_exempt
@require_POST
def flutterwave_webhook(request):
    if not request.is_secure() or not valid_flutterwave_signature(request):
        return HttpResponse(status=400)
    payload = _payload(request)
    if (payload.get('event') or payload.get('type')) != 'charge.completed':
        return HttpResponse(status=200)
    data = payload.get('data')
    if not isinstance(data, dict):
        return HttpResponse(status=400)
    reference = str(data.get('tx_ref') or '')
    attempt = _attempt('flutterwave', reference[3:]) if reference.startswith('pl-') else None
    return _handle_event(attempt, str(data.get('id') or ''))
