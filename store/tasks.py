from celery import shared_task
from datetime import timedelta
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from .models import ProductImage, PendingMetadata
from .utils.image_meta import generate_product_json_from_image
from decimal import Decimal, ROUND_HALF_UP
import random


@shared_task(bind=True)
def analyze_and_apply_image(self, product_image_id: int):
    try:
        img = ProductImage.objects.select_related('product').get(pk=product_image_id)
    except ProductImage.DoesNotExist:
        return {'status': 'missing'}

    product = img.product
    generated = generate_product_json_from_image(img.image)
    confidence = float(generated.get('confidence', 0.0))

    # always persist pending metadata for audit / review
    pending = PendingMetadata.objects.create(product=product, metadata=generated, confidence=confidence)

    # auto-apply if confidence >= threshold
    threshold = getattr(settings, 'STORE_AUTO_APPLY_CONFIDENCE', 0.85)
    applied = False
    if confidence >= threshold:
        # map conservative fields
        if generated.get('title') and generated.get('title_source') == 'filename':
            product.name = generated.get('title')
        if generated.get('slug') and generated.get('title_source') == 'filename':
            product.slug = generated.get('slug')
        if generated.get('description'):
            product.description = generated.get('description')
        if generated.get('features'):
            product.features = generated.get('features')
        if generated.get('benefits'):
            product.benefits = generated.get('benefits')
        if generated.get('suggested_tags'):
            product.tags = generated.get('suggested_tags')
        # Seed social proof values when metadata is generated from admin button.
        product.review_count = random.randint(20, 300)
        product.rating = Decimal(str(random.uniform(3.0, 5.0))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        product.save()
        pending.applied = True
        pending.save()
        applied = True

    return {'status': 'ok', 'applied': applied, 'confidence': confidence}


@shared_task(bind=True, max_retries=4, ignore_result=True)
def deliver_payment_link_notice(self, notice_id):
    from .models import PaymentLinkNotice
    from .payment_link_mail import send_payment_link_notice
    from .payment_links import audit, can_send_invitation

    now = timezone.now()
    queue = PaymentLinkNotice.objects.filter(pk=notice_id, sent_at__isnull=True, cancelled_at__isnull=True)
    if not queue.filter(Q(claimed_at__isnull=True) | Q(claimed_at__lt=now - timedelta(minutes=10))).update(claimed_at=now):
        return
    notice = queue.select_related('link').get()
    if notice.kind == 'invitation' and not can_send_invitation(notice.link):
        queue.update(cancelled_at=timezone.now())
        return
    try:
        if send_payment_link_notice(notice) != 1:
            raise RuntimeError('Mail backend returned no delivery.')
    except Exception:
        queue.update(claimed_at=None)
        raise self.retry(countdown=60 * (self.request.retries + 1), exc=RuntimeError('Payment link email delivery failed.')) from None
    queue.update(sent_at=timezone.now())
    audit(notice.link, f'{notice.kind}_sent')


@shared_task(ignore_result=True)
def maintain_payment_links():
    from .models import PaymentLinkAttempt, PaymentLinkNotice, PaymentLinkThrottle
    from .payment_link_gateways import GatewayError
    from .payment_links import reconcile

    now = timezone.now()
    notices = PaymentLinkNotice.objects.filter(
        sent_at__isnull=True, cancelled_at__isnull=True, created_at__gte=now - timedelta(days=7),
    ).filter(Q(claimed_at__isnull=True) | Q(claimed_at__lt=now - timedelta(minutes=10))).order_by('created_at')
    for notice_id in notices.values_list('pk', flat=True)[:100]:
        deliver_payment_link_notice.delay(notice_id)

    attempts = PaymentLinkAttempt.objects.select_related('link').filter(status='active').filter(
        Q(last_checked_at__isnull=True) | Q(last_checked_at__lt=now - timedelta(minutes=2)),
    ).order_by('last_checked_at', 'pk')
    for attempt in attempts[:20]:
        try:
            reconcile(attempt)
        except GatewayError:
            continue
    PaymentLinkThrottle.objects.filter(window_start__lt=now - timedelta(days=1)).delete()
