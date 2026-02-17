from celery import shared_task
from django.conf import settings
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
