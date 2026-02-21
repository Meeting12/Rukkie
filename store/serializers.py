from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.conf import settings
import os
import re
from urllib.parse import urlparse, quote, unquote
from .models import (
    Product,
    ProductImage,
    Category,
    HomeHeroSlide,
    Cart,
    CartItem,
    Order,
    OrderItem,
    ShippingMethod,
    Address,
    Wishlist,
    Page,
    PaymentTransaction,
    ProductReview,
    UserNotification,
    UserMailboxMessage,
)

User = get_user_model()


def _cloudinary_cloud_name():
    def _clean_cloud_name(value: str) -> str:
        candidate = str(value or '').strip()
        if not candidate:
            return ''
        lowered = unquote(candidate).strip().lower()
        if '<' in lowered or '>' in lowered:
            return ''
        if lowered in {'cloud_name', 'your_cloud_name', 'replace_me'}:
            return ''
        return candidate

    storage_cfg = getattr(settings, 'CLOUDINARY_STORAGE', {}) or {}
    cloud_name = _clean_cloud_name(storage_cfg.get('CLOUD_NAME'))
    if cloud_name:
        return cloud_name
    cloudinary_url = str(os.environ.get('CLOUDINARY_URL') or '').strip().strip('"').strip("'")
    if cloudinary_url.lower().startswith('cloudinary_url='):
        cloudinary_url = cloudinary_url.split('=', 1)[1].strip().strip('"').strip("'")
    if not cloudinary_url:
        return ''
    try:
        parsed = urlparse(cloudinary_url)
        if parsed.scheme == 'cloudinary':
            return _clean_cloud_name(parsed.hostname)
    except Exception:
        return ''
    return ''


def _extract_cloudinary_public_id(path: str) -> str:
    path = str(path or '').replace('\\', '/')
    marker = '/image/upload/'
    lowered = path.lower()
    if marker in lowered:
        idx = lowered.find(marker)
        tail = path[idx + len(marker):].lstrip('/')
    else:
        segments = [seg for seg in path.split('/') if seg]
        tail = '/'.join(segments[1:]) if len(segments) > 1 else ''

    if tail.startswith('v') and '/' in tail:
        version, remainder = tail.split('/', 1)
        if version[1:].isdigit():
            tail = remainder
    return unquote(tail).lstrip('/')


def _normalize_cloudinary_delivery_url(url: str) -> str:
    cleaned = str(url or '').strip()
    if not cleaned:
        return ''
    try:
        parsed = urlparse(cleaned)
    except Exception:
        return cleaned
    if 'res.cloudinary.com' not in str(parsed.netloc or '').lower():
        return cleaned

    path = (parsed.path or '').replace('\\', '/')
    # Some legacy rows were saved as "media/products/..." while Cloudinary public_id is "products/...".
    path = re.sub(r'(?i)/image/upload/v1/media/', '/image/upload/', path)
    path = re.sub(r'(?i)/image/upload/media/', '/image/upload/', path)
    path = re.sub(r'(?i)/image/upload/v1/(products|categories|hero)/', r'/image/upload/\1/', path)
    path_segments = [seg for seg in path.split('/') if seg]
    current_cloud_name = unquote(path_segments[0]).strip() if path_segments else ''
    cloud_name = _cloudinary_cloud_name()
    is_placeholder_cloud = (
        (not current_cloud_name)
        or ('<' in current_cloud_name or '>' in current_cloud_name)
        or (current_cloud_name.lower() in {'cloud_name', 'your_cloud_name', 'replace_me'})
    )
    if is_placeholder_cloud:
        public_id = _extract_cloudinary_public_id(path)
        if cloud_name and public_id:
            return f'https://res.cloudinary.com/{cloud_name}/image/upload/{quote(public_id, safe="/")}'
        if public_id:
            if public_id.startswith('media/'):
                public_id = public_id[len('media/'):]
            return f'/media/{public_id}'
        return ''

    try:
        return parsed._replace(path=path).geturl()
    except Exception:
        return cleaned


def _fallback_image_url_from_name(name: str, upload_prefix: str = '') -> str:
    cleaned = str(name or '').strip().replace('\\', '/').lstrip('/')
    prefix = str(upload_prefix or '').strip().replace('\\', '/').lstrip('/')
    if prefix and not prefix.endswith('/'):
        prefix = f'{prefix}/'
    if not cleaned:
        return ''
    if cleaned.startswith('https:/') and not cleaned.startswith('https://'):
        cleaned = cleaned.replace('https:/', 'https://', 1)
    if cleaned.startswith('http:/') and not cleaned.startswith('http://'):
        cleaned = cleaned.replace('http:/', 'http://', 1)
    if cleaned.startswith('http://') or cleaned.startswith('https://') or cleaned.startswith('data:'):
        if 'res.cloudinary.com/' in cleaned:
            repaired = _normalize_cloudinary_delivery_url(cleaned)
            if repaired:
                cleaned = repaired
            if cleaned.startswith('/'):
                return cleaned
        # If a Cloudinary URL was stored without `/image/upload/`, normalize it.
        if 'res.cloudinary.com/' in cleaned and '/image/upload/' not in cleaned:
            try:
                parsed = urlparse(cleaned)
                parts = [p for p in parsed.path.split('/') if p]
                # /<cloud_name>/<public_id...>
                if len(parts) >= 2:
                    cloud_name = parts[0]
                    public_id = quote('/'.join(parts[1:]), safe='/')
                    return f'{parsed.scheme}://{parsed.netloc}/{cloud_name}/image/upload/{public_id}'
            except Exception:
                pass
        return _normalize_cloudinary_delivery_url(cleaned)
    if cleaned.startswith('media/'):
        cloud_name = _cloudinary_cloud_name()
        media_relative = cleaned[len('media/'):]
        if cloud_name and media_relative.startswith(('products/', 'categories/', 'hero/')):
            return f'https://res.cloudinary.com/{cloud_name}/image/upload/{quote(cleaned, safe="/")}'
        return f'/{cleaned}' 
            
    if cleaned.startswith(('products/', 'categories/', 'hero/')):
        cloud_name = _cloudinary_cloud_name()
        if cloud_name:
            return f'https://res.cloudinary.com/{cloud_name}/image/upload/{quote(cleaned, safe="/")}'
        return f'/media/{cleaned}'
    if cleaned.startswith('res.cloudinary.com/'):
        candidate = _normalize_cloudinary_delivery_url(f'https://{cleaned}')
        if candidate.startswith('/'):
            return candidate
        if candidate:
            cleaned = candidate
        candidate = f'https://{cleaned}'
        if '/image/upload/' not in candidate:
            try:
                parsed = urlparse(candidate)
                parts = [p for p in parsed.path.split('/') if p]
                if len(parts) >= 2:
                    cloud_name = parts[0]
                    public_id = quote('/'.join(parts[1:]), safe='/')
                    return f'https://{parsed.netloc}/{cloud_name}/image/upload/{public_id}'
            except Exception:
                pass
        return candidate

    # Cloudinary often stores a public_id in the field value; construct delivery URL.
    if prefix and '/' not in cleaned and cleaned.lower().endswith(
        ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.svg', '.avif')
    ):
        cleaned = f'{prefix}{cleaned}'
    cloud_name = _cloudinary_cloud_name()
    if cloud_name:
        return f'https://res.cloudinary.com/{cloud_name}/image/upload/{quote(cleaned, safe="/")}'
    if prefix and '/' not in cleaned:
        cleaned = f'{prefix}{cleaned}'
    return f'/media/{cleaned}'


def _resolve_image_url(field_file, request=None) -> str:
    if not field_file:
        return ''

    upload_prefix = ''
    try:
        upload_prefix = str(
            getattr(getattr(field_file, 'field', None), 'upload_to', '') or ''
        ).strip()
    except Exception:
        upload_prefix = ''

    raw_url = ''
    try:
        raw_url = str(field_file.url or '').strip()
    except Exception:
        raw_url = ''

    # ==============================
    # 🔥 CORRECTION ADDED HERE
    # If Cloudinary already returned a FULL absolute URL,
    # return it immediately and DO NOT pass through fallback.
    # This prevents rewriting Cloudinary URLs like:
    # https://res.cloudinary.com/...
    # ==============================
    if raw_url.startswith('http://') or raw_url.startswith('https://'):
        return raw_url
    # ==============================

    url = _fallback_image_url_from_name(
        raw_url, upload_prefix=upload_prefix
    ) if raw_url else ''

    if not url:
        url = _fallback_image_url_from_name(
            getattr(field_file, 'name', ''),
            upload_prefix=upload_prefix
        )

    if not url:
        return ''

    if request and url.startswith('/'):
        return request.build_absolute_uri(url)

    return url

class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        request = self.context.get('request')
        return _resolve_image_url(getattr(obj, 'image', None), request)

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'image_url', 'alt', 'order']


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        request = self.context.get('request')
        return _resolve_image_url(getattr(obj, 'image', None), request)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'image_url', 'parent', 'is_active', 'product_count']


class HomeHeroSlideSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        request = self.context.get('request')
        return _resolve_image_url(getattr(obj, 'image', None), request)

    class Meta:
        model = HomeHeroSlide
        fields = [
            'id',
            'badge',
            'title',
            'title_accent',
            'description',
            'image',
            'image_url',
            'cta_text',
            'cta_link',
            'secondary_cta_text',
            'secondary_cta_link',
            'promo',
            'sort_order',
            'is_active',
        ]


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'original_price', 'stock', 'rating', 'review_count',
            'is_active', 'is_featured', 'is_flash_sale', 'is_digital', 'created_at', 'images', 'categories',
            'features', 'benefits', 'tags'
        ]


class ProductReviewSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    verified = serializers.SerializerMethodField()

    def get_display_name(self, obj):
        if obj.reviewer_name:
            return obj.reviewer_name
        if obj.user_id and getattr(obj.user, 'username', None):
            return obj.user.username
        return 'Anonymous'

    def get_verified(self, obj):
        return bool(obj.user_id)

    class Meta:
        model = ProductReview
        fields = ['id', 'product', 'display_name', 'reviewer_name', 'reviewer_email', 'rating', 'comment', 'verified', 'created_at']
        read_only_fields = ['id', 'product', 'display_name', 'verified', 'created_at']


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'subtotal']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'session_key', 'items', 'total']


class ShippingMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingMethod
        fields = ['id', 'name', 'price', 'delivery_days', 'active']


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'price', 'subtotal']


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = [
            'id',
            'provider',
            'paypal_order_id',
            'provider_transaction_id',
            'status',
            'amount',
            'currency',
            'payer_email',
            'success',
            'created_at',
            'updated_at',
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = AddressSerializer(read_only=True)
    billing_address = AddressSerializer(read_only=True)
    transactions = PaymentTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'user', 'status', 'shipping_method', 'shipping_address', 'billing_address', 'total', 'items', 'transactions', 'created_at']


class WishlistSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'user', 'products', 'created_at', 'updated_at']


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ['id', 'title', 'slug', 'content', 'seo_description', 'seo_keywords', 'created_at']


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']


class UserNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotification
        fields = ['id', 'title', 'message', 'level', 'is_read', 'read_at', 'created_at', 'updated_at']


class UserMailboxMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMailboxMessage
        fields = ['id', 'subject', 'body', 'category', 'is_read', 'read_at', 'created_at', 'updated_at']
