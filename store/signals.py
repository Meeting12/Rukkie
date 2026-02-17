from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import logging
from .models import ProductImage, Category
from .media_layout import ensure_category_media_structure

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Category)
def category_post_save_create_media_structure(sender, instance, created, **kwargs):
    """
    Keep media folders predictable for uploads/imports:
    media/categories/<slug> and media/products/categories/<slug>/{raw,processed,archive}.
    """
    try:
        ensure_category_media_structure(instance.slug or instance.name)
    except Exception:
        logger.exception(
            'category media structure creation failed category_id=%s slug=%s',
            getattr(instance, 'id', None),
            getattr(instance, 'slug', ''),
        )


@receiver(post_save, sender=ProductImage)
def product_image_post_save(sender, instance, created, **kwargs):
    """
    On image save, generate conservative metadata and auto-apply to the parent Product.
    This overwrites product `name`, `slug`, `description`, `features`, `benefits`, and `tags` when inferred.
    """
    try:
        product = instance.product
    except Exception:
        return

    img_file = getattr(instance, 'image', None)
    if not img_file:
        return

    # Run sync in local/dev by default; use async when explicitly enabled.
    try:
        from .tasks import analyze_and_apply_image
        if getattr(settings, 'STORE_METADATA_ASYNC', False):
            analyze_and_apply_image.delay(instance.id)
        else:
            analyze_and_apply_image(instance.id)
    except Exception:
        logger.exception('metadata signal processing failed product_id=%s image_id=%s', product.id, instance.id)
        return
