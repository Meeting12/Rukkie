from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import (
    Product, Cart, CartItem, Order, OrderItem, ShippingMethod, Address, Category,
    ContactMessage, NewsletterSubscription, PaymentTransaction, HomeHeroSlide, Wishlist, ProductReview, AssistantPolicy,
    UserNotification, UserMailboxMessage, Page,
)
from django.db.models import Count, Q, Avg
from .serializers import (
    ProductSerializer, CartSerializer, CartItemSerializer, OrderSerializer,
    ShippingMethodSerializer, AddressSerializer, CategorySerializer, HomeHeroSlideSerializer, ProductReviewSerializer,
    UserNotificationSerializer, UserMailboxMessageSerializer, _resolve_image_url,
)
from django.db import transaction
from decimal import Decimal, InvalidOperation
import stripe
from django.conf import settings
import requests
import paypalrestsdk
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import AnonymousUser
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.core.cache import cache
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from django.shortcuts import redirect
import json
import hmac
import hashlib
import logging
import re
from uuid import uuid4
from django.views.decorators.csrf import csrf_exempt
from ipaddress import ip_address
from .email_react import get_public_site_url, render_react_email_html

logger = logging.getLogger(__name__)
STOREFRONT_THEME_PAGE_SLUG = 'storefront-theme-preset'
STOREFRONT_THEME_PAGE_TITLE = 'Storefront Theme Preset'
STOREFRONT_THEME_DEFAULT = 'default'
STOREFRONT_THEME_LUXURY = 'luxury-beauty'
STOREFRONT_THEME_OBSIDIAN = 'obsidian-gold'
STOREFRONT_THEME_CHOICES = {STOREFRONT_THEME_DEFAULT, STOREFRONT_THEME_LUXURY, STOREFRONT_THEME_OBSIDIAN}
PAID_ORDER_STATUSES = (
    Order.STATUS_PAID,
    Order.STATUS_PROCESSING,
    Order.STATUS_SHIPPED,
    Order.STATUS_DELIVERED,
)


def _get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR') or 'unknown'


def _is_private_or_local_ip(ip):
    try:
        addr = ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
    except Exception:
        return False


def _lookup_location_by_ip(ip):
    if not ip or ip == 'unknown' or _is_private_or_local_ip(ip):
        return 'Local/Private Network'

    try:
        resp = requests.get(f'https://ipapi.co/{ip}/json/', timeout=3)
        if resp.ok:
            data = resp.json() or {}
            parts = [data.get('city'), data.get('region'), data.get('country_name')]
            location = ', '.join([p for p in parts if p])
            if location:
                return location
    except Exception:
        logger.info('IP geolocation lookup failed for %s', ip)

    return 'Unknown Location'


def _get_device_name(request):
    ua = request.META.get('HTTP_USER_AGENT', '') or 'Unknown Device'
    return ua[:240]


def _get_storefront_theme_value():
    page = Page.objects.filter(slug=STOREFRONT_THEME_PAGE_SLUG).only('content').first()
    raw_value = (getattr(page, 'content', '') or '').strip().lower()
    if raw_value in STOREFRONT_THEME_CHOICES:
        return raw_value
    return STOREFRONT_THEME_DEFAULT


def _set_storefront_theme_value(theme_value: str) -> str:
    normalized = (str(theme_value or '').strip().lower() or STOREFRONT_THEME_DEFAULT)
    if normalized not in STOREFRONT_THEME_CHOICES:
        normalized = STOREFRONT_THEME_DEFAULT
    page, created = Page.objects.get_or_create(
        slug=STOREFRONT_THEME_PAGE_SLUG,
        defaults={
            'title': STOREFRONT_THEME_PAGE_TITLE,
            'content': normalized,
            'seo_description': 'Global storefront theme preset.',
            'seo_keywords': 'storefront,theme,preset',
        },
    )
    if not created and page.content != normalized:
        page.content = normalized
        if not page.title:
            page.title = STOREFRONT_THEME_PAGE_TITLE
        page.save(update_fields=['content', 'title', 'updated_at'])
    return normalized


def _safe_send_email(*, subject, message, recipient_list, event_name, html_message=None):
    recipients = [r for r in (recipient_list or []) if r]
    if not recipients:
        logger.warning('%s email skipped: no recipients', event_name)
        return False
    try:
        sent_count = send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@derukkies.com'),
            recipient_list=recipients,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info('%s email sent to=%s sent_count=%s', event_name, ','.join(recipients), sent_count)
        return sent_count > 0
    except Exception:
        logger.exception('%s email failed to=%s', event_name, ','.join(recipients))
        return False


def _create_user_notification(user, *, title, message, level='info'):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    try:
        return UserNotification.objects.create(
            user=user,
            title=str(title or '').strip()[:200] or 'Notification',
            message=str(message or '').strip(),
            level=(str(level or '').strip().lower() or UserNotification.LEVEL_INFO),
        )
    except Exception:
        logger.exception('account.notification create_failed user_id=%s title=%s', getattr(user, 'id', None), title)
        return None


def _create_user_mailbox_message(user, *, subject, body, category='general'):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    try:
        return UserMailboxMessage.objects.create(
            user=user,
            subject=str(subject or '').strip()[:255] or 'Message',
            body=str(body or '').strip(),
            category=(str(category or '').strip().lower() or UserMailboxMessage.CATEGORY_GENERAL),
        )
    except Exception:
        logger.exception('account.mailbox create_failed user_id=%s subject=%s', getattr(user, 'id', None), subject)
        return None


def _send_verification_email(request, user):
    if not user.email:
        logger.warning('register.verify_email skipped user=%s reason=no_email', user.username)
        return

    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verify_path = reverse('auth-verify-email', kwargs={'uidb64': uidb64, 'token': token})
    verify_url = request.build_absolute_uri(verify_path)

    subject = 'Verify your De-Rukkies account'
    message = (
        f'Hi {user.username},\n\n'
        'Thanks for registering. Please verify your email to activate your account:\n\n'
        f'{verify_url}\n\n'
        'If you did not create this account, please ignore this email.'
    )
    _safe_send_email(
        subject=subject,
        message=message,
        recipient_list=[user.email],
        event_name='register.verify_email',
        html_message=render_react_email_html(
            'SignupVerificationEmail',
            {
                'userName': user.get_full_name() or user.username,
                'verificationUrl': verify_url,
                'siteName': 'De-Rukkies Collections',
                'supportEmail': _contact_recipient(),
                'expiresText': 'This verification link expires automatically. If it fails, request a new link from the login page.',
            },
        ),
    )
    _create_user_mailbox_message(
        user,
        subject=subject,
        body=message,
        category=UserMailboxMessage.CATEGORY_ACCOUNT,
    )
    _create_user_notification(
        user,
        title='Verify your email',
        message='A verification link has been sent to your email address.',
        level=UserNotification.LEVEL_INFO,
    )


def _send_login_security_notification(user, request):
    ip = _get_client_ip(request)
    location = _lookup_location_by_ip(ip)
    device_name = _get_device_name(request)
    logged_in_at = timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')

    subject = 'Security Alert: New Login Detected'
    message = (
        f'Hello {user.username},\n\n'
        'A new login to your account was detected.\n\n'
        f'IP Address: {ip}\n'
        f'Location: {location}\n'
        f'Device: {device_name}\n'
        f'Time: {logged_in_at}\n\n'
        'If this was you, no action is needed.\n'
        'If this was NOT you, change your password immediately and review account activity.'
    )
    if user.email:
        site_root = get_public_site_url(request)
        _safe_send_email(
            subject=subject,
            message=message,
            recipient_list=[user.email],
            event_name='auth.login_alert',
            html_message=render_react_email_html(
                'LoginWarningEmail',
                {
                    'userName': user.get_full_name() or user.username,
                    'loginTime': logged_in_at,
                    'device': device_name,
                    'ipAddress': ip,
                    'location': location,
                    'accountUrl': f'{site_root}/account',
                    'resetPasswordUrl': f'{site_root}/forgot-password',
                    'siteName': 'De-Rukkies Collections',
                    'supportEmail': _contact_recipient(),
                },
            ),
        )
    else:
        logger.warning('auth.login_alert email skipped user=%s reason=no_email', user.username)
    _create_user_mailbox_message(
        user,
        subject=subject,
        body=message,
        category=UserMailboxMessage.CATEGORY_SECURITY,
    )
    _create_user_notification(
        user,
        title='New login detected',
        message=f'New login from {location} ({ip}). If this was not you, change your password now.',
        level=UserNotification.LEVEL_WARNING,
    )


def _contact_recipient():
    return getattr(settings, 'CONTACT_RECIPIENT_EMAIL', '') or getattr(settings, 'DEFAULT_FROM_EMAIL', '')


def _send_order_created_notifications(order, contact_email=None):
    recipient_email = ''
    if order.user and order.user.email:
        recipient_email = order.user.email
    elif contact_email:
        recipient_email = contact_email

    if recipient_email:
        site_root = get_public_site_url()
        shipping_text = ''
        tax_text = ''
        subtotal_text = ''
        order_items_summary = []
        try:
            items_qs = order.items.select_related('product').all()
            for item in items_qs:
                try:
                    qty = int(item.quantity or 0)
                except Exception:
                    qty = 0
                unit_price = Decimal(str(item.price or 0)).quantize(Decimal("0.01"))
                line_total = (unit_price * Decimal(str(qty or 0))).quantize(Decimal("0.01"))
                order_items_summary.append(
                    {
                        'name': str(getattr(item.product, 'name', '') or 'Product').strip(),
                        'quantity': qty,
                        'unitPriceText': f'${unit_price}',
                        'lineTotalText': f'${line_total}',
                        'imageUrl': '',
                    }
                )
                try:
                    first_image = item.product.images.first()
                    image_url = ''
                    if first_image and getattr(first_image, 'image', None):
                        image_url = _resolve_image_url(getattr(first_image, 'image', None), request=None) or ''
                        image_url = str(image_url).strip()
                        if image_url.startswith('//'):
                            image_url = f'https:{image_url}'
                        elif image_url.startswith('/'):
                            image_url = f'{site_root}{image_url}'
                        # Email clients are inconsistent with modern formats like WebP/AVIF.
                        # Prefer a JPEG Cloudinary transformation for transactional email thumbnails.
                        if 'res.cloudinary.com/' in image_url and '/image/upload/' in image_url and '/f_jpg' not in image_url:
                            image_url = image_url.replace('/image/upload/', '/image/upload/f_jpg,q_auto/', 1)
                    if image_url:
                        order_items_summary[-1]['imageUrl'] = image_url
                except Exception:
                    pass
            subtotal = sum((Decimal(str(item.price or 0)) * Decimal(str(item.quantity or 0))) for item in items_qs)
            subtotal_text = f'${subtotal.quantize(Decimal("0.01"))}'
        except Exception:
            subtotal_text = ''
            order_items_summary = []
        try:
            if getattr(order, 'shipping_method', None):
                shipping_text = f'${Decimal(str(order.shipping_method.price or 0)).quantize(Decimal("0.01"))}'
        except Exception:
            shipping_text = ''
        try:
            if subtotal_text:
                subtotal_value = Decimal(subtotal_text.replace('$', ''))
                total_value = Decimal(str(order.total or 0)).quantize(Decimal('0.01'))
                shipping_value = Decimal(shipping_text.replace('$', '')) if shipping_text else Decimal('0.00')
                tax_value = (total_value - subtotal_value - shipping_value).quantize(Decimal('0.01'))
                tax_text = f'${tax_value}'
        except Exception:
            tax_text = ''
        address_text = ''
        try:
            addr = order.shipping_address or order.billing_address
            if addr:
                parts = [addr.full_name, addr.line1, getattr(addr, 'line2', ''), addr.city, addr.postal_code, addr.country]
                address_text = '\n'.join([str(p).strip() for p in parts if p])
        except Exception:
            address_text = ''
        customer_message = (
            f'Thank you for your order.\n\n'
            f'Order Number: {order.order_number}\n'
            f'Status: {order.status}\n'
            f'Total: ${order.total}\n\n'
            'We are processing your order and will notify you when payment is confirmed and the order advances.'
        )
        _safe_send_email(
            subject=f'Order Received: {order.order_number}',
            message=customer_message,
            recipient_list=[recipient_email],
            event_name='order.created.customer',
            html_message=render_react_email_html(
                'OrderConfirmationEmail',
                {
                    'userName': (order.user.get_full_name() or order.user.username) if order.user else '',
                    'orderNumber': order.order_number,
                    'statusText': order.status,
                    'totalText': f'${order.total}',
                    'subtotalText': subtotal_text,
                    'shippingText': shipping_text,
                    'taxText': tax_text,
                    'items': order_items_summary,
                    'addressText': address_text,
                    'orderUrl': f'{site_root}/account',
                    'siteName': 'De-Rukkies Collections',
                    'supportEmail': _contact_recipient(),
                },
            ),
        )
        if order.user_id:
            _create_user_mailbox_message(
                order.user,
                subject=f'Order received: {order.order_number}',
                body=customer_message,
                category=UserMailboxMessage.CATEGORY_ORDER,
            )
            _create_user_notification(
                order.user,
                title='Order created',
                message=f'Order {order.order_number} has been created and is currently {order.status}.',
                level=UserNotification.LEVEL_INFO,
            )

    ops_email = _contact_recipient()
    if ops_email:
        _safe_send_email(
            subject=f'New Order Created: {order.order_number}',
            message=(
                f'Order Number: {order.order_number}\n'
                f'Order ID: {order.id}\n'
                f'User: {(order.user.username if order.user else "guest")}\n'
                f'Total: ${order.total}\n'
                f'Status: {order.status}\n'
            ),
            recipient_list=[ops_email],
            event_name='order.created.ops',
        )


def _send_order_paid_notifications(order, provider='unknown'):
    latest_txn = order.transactions.filter(success=True).order_by('-created_at', '-id').first()
    recipient_email = order.user.email if order.user and order.user.email else ''
    if not recipient_email and latest_txn and getattr(latest_txn, 'payer_email', ''):
        recipient_email = str(latest_txn.payer_email).strip()
    if recipient_email:
        site_root = get_public_site_url()
        payment_date = ''
        payment_method = provider
        transaction_id = ''
        if latest_txn:
            transaction_id = (latest_txn.provider_txn_id or '').strip()
            payment_method = latest_txn.provider or provider
            try:
                payment_date = timezone.localtime(latest_txn.created_at).strftime('%Y-%m-%d %H:%M:%S %Z')
            except Exception:
                payment_date = str(latest_txn.created_at)
        customer_message = (
            f'Payment for order {order.order_number} has been confirmed.\n\n'
            f'Payment Provider: {provider}\n'
            f'Current Status: {order.status}\n'
            f'Total: ${order.total}\n\n'
            'Thank you for shopping with De-Rukkies Collections.'
        )
        _safe_send_email(
            subject=f'Payment Confirmed: {order.order_number}',
            message=customer_message,
            recipient_list=[recipient_email],
            event_name='order.paid.customer',
            html_message=render_react_email_html(
                'PaymentConfirmationEmail',
                {
                    'userName': (order.user.get_full_name() or order.user.username) if order.user else '',
                    'orderNumber': order.order_number,
                    'amountText': f'${order.total}',
                    'provider': provider,
                    'paymentMethod': payment_method,
                    'paymentDate': payment_date,
                    'transactionId': transaction_id,
                    'statusText': 'Successful',
                    'orderUrl': f'{site_root}/account',
                    'siteName': 'De-Rukkies Collections',
                    'supportEmail': _contact_recipient(),
                },
            ),
        )
        _create_user_mailbox_message(
            order.user,
            subject=f'Payment confirmed: {order.order_number}',
            body=customer_message,
            category=UserMailboxMessage.CATEGORY_PAYMENT,
        )
        _create_user_notification(
            order.user,
            title='Payment successful',
            message=f'Payment for order {order.order_number} is confirmed.',
            level=UserNotification.LEVEL_SUCCESS,
        )

    ops_email = _contact_recipient()
    if ops_email:
        _safe_send_email(
            subject=f'Order Paid: {order.order_number}',
            message=(
                f'Order Number: {order.order_number}\n'
                f'Order ID: {order.id}\n'
                f'Provider: {provider}\n'
                f'Total: ${order.total}\n'
                f'Status: {order.status}\n'
            ),
            recipient_list=[ops_email],
            event_name='order.paid.ops',
        )


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True)
        params = self.request.query_params
        category_slug = params.get('category')
        featured = params.get('featured')
        if category_slug:
            qs = qs.filter(categories__slug=category_slug)
        if featured is not None:
            if str(featured).lower() in ['1', 'true', 'yes']:
                qs = qs.filter(is_featured=True)
            else:
                qs = qs.filter(is_featured=False)
        return qs


@api_view(['GET'])
@permission_classes([AllowAny])
def product_by_slug(request, slug):
    """Return product by slug."""
    product = get_object_or_404(Product, slug=slug, is_active=True)
    serializer = ProductSerializer(product, context={'request': request})
    return Response(serializer.data)


def _refresh_product_review_stats(product):
    stats = ProductReview.objects.filter(product=product, is_approved=True).aggregate(
        avg_rating=Avg('rating'),
        review_total=Count('id'),
    )
    total = int(stats.get('review_total') or 0)
    avg_value = stats.get('avg_rating')
    product.review_count = total
    if avg_value is None:
        product.rating = Decimal('0.00')
    else:
        product.rating = Decimal(str(avg_value)).quantize(Decimal('0.01'))
    product.save(update_fields=['review_count', 'rating'])


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def product_reviews(request, slug):
    """List approved reviews or create a new review for a product."""
    product = get_object_or_404(Product, slug=slug, is_active=True)

    if request.method == 'GET':
        reviews = ProductReview.objects.filter(product=product, is_approved=True).select_related('user').order_by('-created_at')
        serializer = ProductReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    reviewer_name = (request.data.get('reviewer_name') or request.data.get('name') or '').strip()
    reviewer_email = (request.data.get('reviewer_email') or request.data.get('email') or '').strip().lower()
    comment = (request.data.get('comment') or '').strip()
    rating_raw = request.data.get('rating')

    try:
        rating = int(str(rating_raw).strip())
    except Exception:
        return Response({'error': 'invalid_rating', 'detail': 'Rating must be an integer between 1 and 5.'}, status=400)

    if rating < 1 or rating > 5:
        return Response({'error': 'invalid_rating', 'detail': 'Rating must be between 1 and 5.'}, status=400)
    if not comment:
        return Response({'error': 'comment_required', 'detail': 'Comment is required.'}, status=400)

    user = request.user if getattr(request.user, 'is_authenticated', False) else None
    if user and not reviewer_name:
        reviewer_name = user.get_full_name() or user.get_username()
    if not reviewer_name:
        return Response({'error': 'name_required', 'detail': 'Reviewer name is required.'}, status=400)

    review = ProductReview.objects.create(
        product=product,
        user=user,
        reviewer_name=reviewer_name[:120],
        reviewer_email=reviewer_email,
        rating=rating,
        comment=comment,
        is_approved=True,
    )

    _refresh_product_review_stats(product)
    serializer = ProductReviewSerializer(review)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    # annotate product_count with only active products
    queryset = Category.objects.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    )
    serializer_class = CategorySerializer
    lookup_field = 'slug'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


@api_view(['GET'])
@permission_classes([AllowAny])
def home_content(request):
    hero_slides = HomeHeroSlide.objects.filter(is_active=True).order_by('sort_order', 'id')
    categories = (
        Category.objects
        .filter(is_active=True)
        .annotate(product_count=Count('products', filter=Q(products__is_active=True)))
        .order_by('name')
    )
    return Response({
        'hero_slides': HomeHeroSlideSerializer(hero_slides, many=True, context={'request': request}).data,
        'categories': CategorySerializer(categories, many=True, context={'request': request}).data,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_shipping_methods(request):
    methods = ShippingMethod.objects.filter(active=True)
    serializer = ShippingMethodSerializer(methods, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def chat_assistant(request):
    """
    Backward-compatible endpoint for existing frontend integrations.
    """
    return _assistant_chat_response(request, bucket='chat_assistant')


_ASSISTANT_INTENT_SUGGESTIONS = {
    'order_tracking': ['Track my order', 'Where is my package?', 'Check payment status'],
    'shipping': ['Shipping methods', 'Delivery timelines', 'Do you ship internationally?'],
    'payment': ['Payment options', 'Card payment', 'Checkout support'],
    'product_search': ['Show featured products', 'Find skincare products', 'Search by category'],
    'returns': ['Return policy', 'How to request refund', 'Exchange options'],
    'general': ['Track my order', 'Shipping information', 'Find products'],
}

_ASSISTANT_ORDER_TOKEN_RE = re.compile(r'\b[A-Z0-9][A-Z0-9-]{5,31}\b', flags=re.IGNORECASE)


def _assistant_policy_text(key, fallback):
    policy = AssistantPolicy.objects.filter(key=key, is_active=True).order_by('-updated_at').first()
    if policy and (policy.content or '').strip():
        return policy.content.strip()
    return fallback


def _assistant_detect_intent(message):
    text = str(message or '').strip().lower()
    if not text:
        return 'general'

    if any(word in text for word in ['track', 'tracking', 'where is', 'where\'s', 'status']) and any(
        word in text for word in ['order', 'package', 'shipment', 'delivery', 'transaction', 'payment']
    ):
        return 'order_tracking'
    if any(word in text for word in ['order number', 'tracking id', 'tracking number']):
        return 'order_tracking'
    if any(word in text for word in ['shipping', 'delivery', 'ship', 'dispatch', 'courier']):
        return 'shipping'
    if any(word in text for word in ['payment', 'pay', 'card', 'stripe', 'paypal', 'flutterwave', 'checkout']):
        return 'payment'
    if any(word in text for word in ['return', 'refund', 'exchange', 'cancel order']):
        return 'returns'
    if any(word in text for word in ['find', 'search', 'show', 'looking for', 'do you have', 'product', 'category']):
        return 'product_search'
    if len(text) >= 2 and Product.objects.filter(is_active=True, name__icontains=text).exists():
        return 'product_search'
    return 'general'


def _assistant_extract_search_query(message):
    text = str(message or '').strip()
    if not text:
        return ''
    lowered = text.lower()
    patterns = [
        r'(?:find|search|show|looking for|look for|do you have)\s+(.+)$',
        r'(?:product|products|category|categories)\s+(?:for|about|named)?\s*(.+)$',
    ]
    for pattern in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            candidate = re.sub(r'[^a-zA-Z0-9\s-]+', '', match.group(1)).strip()
            if candidate:
                return candidate
    candidate = re.sub(r'[^a-zA-Z0-9\s-]+', '', lowered).strip()
    generic_terms = {'products', 'product', 'items', 'item', 'category', 'categories'}
    if candidate in generic_terms:
        return ''
    return candidate


def _assistant_extract_order_token(message, context):
    if isinstance(context, dict):
        for key in ('order_number', 'tracking_id', 'transaction_id', 'order'):
            value = str(context.get(key) or '').strip()
            if value and _ASSISTANT_ORDER_TOKEN_RE.search(value):
                return value.upper()

    text = str(message or '').strip()
    explicit = re.search(r'(?:order|tracking|track|txn|transaction)[\s#:=\-]*([A-Z0-9-]{6,32})', text, flags=re.IGNORECASE)
    if explicit:
        return explicit.group(1).upper()

    tokens = _ASSISTANT_ORDER_TOKEN_RE.findall(text)
    if tokens:
        return tokens[0].upper()
    return ''


def _assistant_lookup_order(token):
    if not token:
        return None, None

    order = Order.objects.filter(order_number__iexact=token).first()
    if not order and token.isdigit():
        order = Order.objects.filter(id=int(token)).first()
    if order:
        return order, order.transactions.order_by('-created_at').first()

    txn = (
        PaymentTransaction.objects
        .select_related('order')
        .filter(Q(provider_transaction_id__iexact=token) | Q(paypal_order_id__iexact=token))
        .order_by('-created_at')
        .first()
    )
    if txn:
        return txn.order, txn
    return None, None


def _assistant_order_tracking_reply(message, context):
    token = _assistant_extract_order_token(message, context)
    if not token:
        return (
            "Please share your order number or tracking ID to check status. "
            "You can find the order number in your order confirmation email and account orders page."
        )

    order, txn = _assistant_lookup_order(token)
    if not order:
        return (
            f"I could not find an order with '{token}'. "
            "Please confirm the order number or tracking ID from your confirmation email."
        )

    status_label = order.get_status_display() if hasattr(order, 'get_status_display') else str(order.status)
    parts = [f"Order {order.order_number} is currently {status_label.lower()}."]
    if txn:
        provider = (txn.provider or 'payment gateway').title()
        parts.append(f"Latest payment status: {txn.status} via {provider}.")
    return " ".join(parts)


def _assistant_shipping_reply():
    policy_text = _assistant_policy_text(
        'shipping',
        'Shipping details are available at checkout after address confirmation.',
    )
    methods = ShippingMethod.objects.filter(active=True).order_by('price')[:3]
    if not methods:
        return policy_text
    lines = [f"- {m.name}: ${m.price} ({m.delivery_days or 'delivery time varies'})" for m in methods]
    return f"{policy_text}\n\nAvailable shipping methods:\n" + "\n".join(lines)


def _assistant_payment_reply():
    policy_text = _assistant_policy_text(
        'payment',
        'Available payment methods are shown securely at checkout.',
    )
    providers = []
    if settings.STRIPE_SECRET_KEY and settings.STRIPE_PUBLISHABLE_KEY:
        providers.append('Stripe')
    if settings.FLUTTERWAVE_SECRET_KEY:
        providers.append('Flutterwave')
    if settings.PAYPAL_CLIENT_ID and settings.PAYPAL_SECRET:
        providers.append('PayPal')
    if providers:
        return f"{policy_text}\n\nCurrently available methods: {', '.join(providers)}."
    return policy_text


def _assistant_returns_reply():
    return _assistant_policy_text(
        'returns',
        'For returns or refunds, please contact support with your order number.',
    )


def _assistant_product_search_reply(message):
    search_query = _assistant_extract_search_query(message)
    if not search_query:
        return "Please tell me what product name or category you want to find."

    matches = (
        Product.objects
        .filter(
            is_active=True,
        )
        .filter(
            Q(name__icontains=search_query)
            | Q(slug__icontains=search_query)
            | Q(categories__name__icontains=search_query)
            | Q(categories__slug__icontains=search_query)
        )
        .distinct()
        .order_by('-is_featured', 'name')[:5]
    )
    if not matches:
        return f"I could not find products matching '{search_query}'. Try another keyword or category."

    lines = []
    for product in matches:
        stock_label = 'In stock' if int(product.stock or 0) > 0 else 'Out of stock'
        lines.append(f"- {product.name} - ${product.price} ({stock_label})")
    return f"Top matches for '{search_query}':\n" + "\n".join(lines)


def _assistant_general_reply():
    return (
        "I can help with order tracking, shipping information, payment options, "
        "product search, and returns."
    )


def _assistant_build_response(message, context):
    intent = _assistant_detect_intent(message)
    if intent == 'order_tracking':
        reply = _assistant_order_tracking_reply(message, context)
    elif intent == 'shipping':
        reply = _assistant_shipping_reply()
    elif intent == 'payment':
        reply = _assistant_payment_reply()
    elif intent == 'product_search':
        reply = _assistant_product_search_reply(message)
    elif intent == 'returns':
        reply = _assistant_returns_reply()
    else:
        reply = _assistant_general_reply()
    suggestions = _ASSISTANT_INTENT_SUGGESTIONS.get(intent, _ASSISTANT_INTENT_SUGGESTIONS['general'])
    return intent, reply, suggestions


def _assistant_chat_response(request, bucket='assistant_chat'):
    if not _rate_limit_allow(
        request,
        bucket=bucket,
        limit=getattr(settings, 'RATE_LIMIT_CHAT_LIMIT', 45),
        window_seconds=getattr(settings, 'RATE_LIMIT_CHAT_WINDOW_SECONDS', 60),
    ):
        logger.warning('assistant.chat rate_limited ip=%s', _get_client_ip(request))
        return _rate_limit_response('Too many assistant requests. Please wait a moment and try again.')

    message = str(request.data.get('message', '')).strip()
    if not message:
        return Response({'error': 'message_required', 'detail': 'Message is required.'}, status=status.HTTP_400_BAD_REQUEST)

    session_id = str(request.data.get('session_id') or '').strip()[:64] or uuid4().hex
    context = request.data.get('context')
    if not isinstance(context, dict):
        context = {}

    intent, reply, suggestions = _assistant_build_response(message, context)
    logger.info('assistant.chat received message=%s ip=%s intent=%s', message[:240], _get_client_ip(request), intent)

    return Response(
        {
            'reply': reply,
            'suggestions': suggestions,
            'intent': intent,
            'session_id': session_id,
        }
    )


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def assistant_chat(request):
    return _assistant_chat_response(request, bucket='assistant_chat')


@api_view(['POST'])
@permission_classes([AllowAny])
def contact_submit(request):
    if not _rate_limit_allow(
        request,
        bucket='contact_submit',
        limit=getattr(settings, 'RATE_LIMIT_CONTACT_LIMIT', 8),
        window_seconds=getattr(settings, 'RATE_LIMIT_CONTACT_WINDOW_SECONDS', 300),
    ):
        logger.warning('contact.submit rate_limited ip=%s', _get_client_ip(request))
        return _rate_limit_response('Too many contact requests. Please try again in a few minutes.')

    full_name = (request.data.get('name') or '').strip()
    email = (request.data.get('email') or '').strip().lower()
    subject = (request.data.get('subject') or '').strip()
    message = (request.data.get('message') or '').strip()
    client_ip = _get_client_ip(request)
    logger.info('contact.submit received email=%s ip=%s subject=%s', email or 'missing', client_ip, subject or 'missing')

    if not full_name or not email or not subject or not message:
        logger.warning('contact.submit validation_failed ip=%s reason=missing_fields', client_ip)
        return Response({'error': 'name, email, subject and message are required'}, status=400)
    if '@' not in email:
        logger.warning('contact.submit validation_failed ip=%s reason=invalid_email email=%s', client_ip, email)
        return Response({'error': 'invalid_email'}, status=400)

    user_agent = _get_device_name(request)

    contact = ContactMessage.objects.create(
        full_name=full_name,
        email=email,
        subject=subject,
        message=message,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    logger.info('contact.submit stored id=%s email=%s ip=%s', contact.id, email, client_ip)

    recipient = _contact_recipient()
    if recipient:
        inbound_subject = f'New Contact Message: {subject}'
        inbound_body = (
            f'Name: {full_name}\n'
            f'Email: {email}\n'
            f'IP: {client_ip}\n'
            f'Device: {user_agent}\n\n'
            f'Message:\n{message}\n'
        )
        _safe_send_email(
            subject=inbound_subject,
            message=inbound_body,
            recipient_list=[recipient],
            event_name='contact.inbound',
        )

    ack_subject = 'We received your message'
    ack_body = (
        f'Hi {full_name},\n\n'
        'Thanks for contacting De-Rukkies Collections. '
        'Our team has received your message and will respond shortly.\n\n'
        f'Reference ID: CONTACT-{contact.id}\n\n'
        'If this was not you, please ignore this email.'
    )
    _safe_send_email(
        subject=ack_subject,
        message=ack_body,
        recipient_list=[email],
        event_name='contact.acknowledgement',
    )

    logger.info('contact.submit completed id=%s email=%s', contact.id, email)
    return Response({'ok': True, 'message': 'Message received.'})


@api_view(['POST'])
@permission_classes([AllowAny])
def newsletter_subscribe(request):
    email = (request.data.get('email') or '').strip().lower()
    if not _rate_limit_allow(
        request,
        bucket='newsletter_subscribe',
        limit=getattr(settings, 'RATE_LIMIT_NEWSLETTER_LIMIT', 10),
        window_seconds=getattr(settings, 'RATE_LIMIT_NEWSLETTER_WINDOW_SECONDS', 300),
        identifier=email,
    ):
        logger.warning('newsletter.subscribe rate_limited ip=%s email=%s', _get_client_ip(request), email or 'missing')
        return _rate_limit_response('Too many subscribe attempts. Please try again shortly.')

    source = (request.data.get('source') or '').strip()[:50]
    client_ip = _get_client_ip(request)
    logger.info('newsletter.subscribe received email=%s source=%s ip=%s', email or 'missing', source or 'unknown', client_ip)
    if not email:
        logger.warning('newsletter.subscribe validation_failed ip=%s reason=missing_email', client_ip)
        return Response({'error': 'email required'}, status=400)
    if '@' not in email:
        logger.warning('newsletter.subscribe validation_failed ip=%s reason=invalid_email email=%s', client_ip, email)
        return Response({'error': 'invalid_email'}, status=400)

    user_agent = _get_device_name(request)

    subscriber, created = NewsletterSubscription.objects.get_or_create(
        email=email,
        defaults={
            'is_active': True,
            'source': source or 'unknown',
            'ip_address': client_ip,
            'user_agent': user_agent,
        }
    )

    already_subscribed = (not created) and subscriber.is_active
    if not created and not subscriber.is_active:
        subscriber.is_active = True
        subscriber.source = source or subscriber.source
        subscriber.ip_address = client_ip
        subscriber.user_agent = user_agent
        subscriber.save(update_fields=['is_active', 'source', 'ip_address', 'user_agent', 'updated_at'])
        logger.info('newsletter.subscribe reactivated email=%s source=%s', email, source or subscriber.source)

    if created or not already_subscribed:
        site_root = get_public_site_url()
        _safe_send_email(
            subject='You are subscribed to De-Rukkies updates',
            message=(
                'Thanks for subscribing to De-Rukkies Collections.\n\n'
                'You will receive updates on new arrivals, special offers, and promotions.'
            ),
            recipient_list=[email],
            event_name='newsletter.confirmation',
            html_message=render_react_email_html(
                'SubscriptionEmail',
                {
                    'userName': '',
                    'shopUrl': f'{site_root}/products',
                    'promoCode': 'SUBSCRIBED10',
                    'siteName': 'De-Rukkies Collections',
                    'supportEmail': _contact_recipient(),
                },
            ),
        )
    logger.info(
        'newsletter.subscribe completed email=%s created=%s already_subscribed=%s source=%s',
        email, created, already_subscribed, source or 'unknown'
    )

    return Response({'ok': True, 'already_subscribed': already_subscribed})


def _get_or_create_cart(request):
    session = request.session
    cart_id = session.get('cart_id')
    if cart_id:
        cart = Cart.objects.filter(id=cart_id).first()
        if cart:
            updated_fields = []
            if request.user.is_authenticated and cart.user_id != request.user.id:
                cart.user = request.user
                updated_fields.append('user')
            if not cart.session_key and session.session_key:
                cart.session_key = session.session_key
                updated_fields.append('session_key')
            if updated_fields:
                cart.save(update_fields=updated_fields)
            return cart

    if request.user.is_authenticated:
        existing_user_cart = Cart.objects.filter(user=request.user).order_by('-updated_at').first()
        if existing_user_cart:
            if not existing_user_cart.session_key and session.session_key:
                existing_user_cart.session_key = session.session_key
                existing_user_cart.save(update_fields=['session_key'])
            session['cart_id'] = existing_user_cart.id
            session.save()
            return existing_user_cart

    cart = Cart.objects.create(
        session_key=session.session_key,
        user=request.user if request.user.is_authenticated else None,
    )
    session['cart_id'] = cart.id
    session.save()
    return cart


@api_view(['GET'])
def cart_detail(request):
    cart = _get_or_create_cart(request)
    serializer = CartSerializer(cart, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
def cart_add(request):
    product_id = request.data.get('product_id')
    try:
        quantity = int(request.data.get('quantity', 1))
    except Exception:
        return Response({'error': 'invalid_quantity'}, status=status.HTTP_400_BAD_REQUEST)
    if quantity <= 0:
        return Response({'error': 'invalid_quantity'}, status=status.HTTP_400_BAD_REQUEST)

    product = get_object_or_404(Product, id=product_id)
    if not product.is_active:
        return Response({'error': 'product_inactive'}, status=status.HTTP_400_BAD_REQUEST)
    cart = _get_or_create_cart(request)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    next_qty = quantity if created else item.quantity + quantity
    if not product.is_digital and next_qty > product.stock:
        return Response(
            {
                'error': 'insufficient_stock',
                'detail': f'Only {product.stock} item(s) available.',
                'available_stock': product.stock,
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    item.quantity = next_qty
    item.save()
    logger.info('cart.add success cart_id=%s product_id=%s quantity=%s', cart.id, product.id, item.quantity)
    return Response({'ok': True}, status=status.HTTP_200_OK)


@api_view(['POST'])
def cart_update(request):
    item_id = request.data.get('item_id')
    try:
        quantity = int(request.data.get('quantity', 1))
    except Exception:
        return Response({'error': 'invalid_quantity'}, status=status.HTTP_400_BAD_REQUEST)
    item = get_object_or_404(CartItem, id=item_id)
    # ensure the item belongs to the current session/user cart
    cart = _get_or_create_cart(request)
    if item.cart_id != cart.id:
        return Response({'error': 'not found'}, status=status.HTTP_404_NOT_FOUND)
    if quantity <= 0:
        item.delete()
    else:
        if not item.product.is_digital and quantity > item.product.stock:
            return Response(
                {
                    'error': 'insufficient_stock',
                    'detail': f'Only {item.product.stock} item(s) available.',
                    'available_stock': item.product.stock,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        item.quantity = quantity
        item.save()
    logger.info('cart.update success cart_id=%s item_id=%s quantity=%s', cart.id, item_id, quantity)
    return Response({'ok': True})


@api_view(['POST'])
def cart_remove(request):
    item_id = request.data.get('item_id')
    item = get_object_or_404(CartItem, id=item_id)
    cart = _get_or_create_cart(request)
    if item.cart_id != cart.id:
        return Response({'error': 'not found'}, status=status.HTTP_404_NOT_FOUND)
    item.delete()
    logger.info('cart.remove success cart_id=%s item_id=%s', cart.id, item_id)
    return Response({'ok': True})


@api_view(['POST'])
def cart_clear(request):
    cart = _get_or_create_cart(request)
    deleted_count, _ = cart.items.all().delete()
    logger.info('cart.clear success cart_id=%s deleted_items=%s', cart.id, deleted_count)
    return Response({'ok': True, 'deleted_items': deleted_count})


@api_view(['POST'])
def checkout_create(request):
    """Create an Order from the current cart and return order summary."""
    cart = _get_or_create_cart(request)
    logger.info('checkout.create started cart_id=%s user=%s', cart.id, request.user.id if request.user.is_authenticated else 'anonymous')
    if not cart.items.exists():
        logger.warning('checkout.create failed cart_id=%s reason=empty_cart', cart.id)
        return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

    data = request.data
    shipping_method_id = data.get('shipping_method')
    shipping_address_data = data.get('shipping_address')
    billing_address_data = data.get('billing_address')
    shipping_address_id = data.get('shipping_address_id')
    billing_address_id = data.get('billing_address_id')
    contact_email = (data.get('contact_email') or '').strip().lower()

    required_addr_fields = ['full_name', 'line1', 'city', 'postal_code', 'country']
    allowed_addr_fields = ['full_name', 'line1', 'line2', 'city', 'state', 'postal_code', 'country', 'phone']

    def _normalize_addr(data):
        if not isinstance(data, dict):
            return {}
        return {field: data.get(field, '') for field in allowed_addr_fields}

    def _validate_addr(payload):
        missing = [f for f in required_addr_fields if not payload or not str(payload.get(f, '')).strip()]
        return missing

    def _resolve_checkout_address(addr_id, addr_payload, role):
        if addr_id not in (None, ''):
            if not request.user.is_authenticated:
                logger.warning('checkout.create failed cart_id=%s reason=%s_id_for_anonymous', cart.id, role)
                return None, Response(
                    {'error': 'authentication_required_for_saved_address', 'field': f'{role}_address_id'},
                    status=status.HTTP_403_FORBIDDEN
                )
            address = Address.objects.filter(id=addr_id, user=request.user).first()
            if not address:
                logger.warning(
                    'checkout.create failed cart_id=%s reason=invalid_%s_address_id value=%s user=%s',
                    cart.id, role, addr_id, request.user.id
                )
                return None, Response(
                    {'error': f'invalid_{role}_address_id', 'field': f'{role}_address_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return address, None

        normalized = _normalize_addr(addr_payload)
        missing = _validate_addr(normalized)
        if missing:
            logger.warning(
                'checkout.create failed cart_id=%s reason=missing_%s_fields fields=%s',
                cart.id, role, ','.join(missing)
            )
            return None, Response(
                {'error': f'missing_{role}_fields', 'fields': missing},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            address = Address.objects.create(
                user=request.user if request.user.is_authenticated else None,
                **normalized,
            )
        except Exception as e:
            logger.exception('checkout.create failed cart_id=%s reason=invalid_%s_address', cart.id, role)
            return None, Response({'error': f'invalid_{role}_address', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return address, None

    with transaction.atomic():
        cart_items = list(cart.items.select_related('product'))
        product_ids = [i.product_id for i in cart_items]
        locked_products = {
            p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids)
        }
        if not cart_items:
            logger.warning('checkout.create failed cart_id=%s reason=empty_cart_post_lock', cart.id)
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        for item in cart_items:
            product = locked_products.get(item.product_id)
            if not product or not product.is_active:
                logger.warning('checkout.create failed cart_id=%s reason=product_unavailable product_id=%s', cart.id, item.product_id)
                return Response({'error': 'product_unavailable', 'product_id': item.product_id}, status=status.HTTP_400_BAD_REQUEST)
            if not product.is_digital and item.quantity > product.stock:
                logger.warning(
                    'checkout.create failed cart_id=%s reason=insufficient_stock product_id=%s requested=%s available=%s',
                    cart.id, product.id, item.quantity, product.stock
                )
                return Response(
                    {
                        'error': 'insufficient_stock',
                        'product_id': product.id,
                        'available_stock': product.stock,
                        'requested_quantity': item.quantity,
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        shipping_method = ShippingMethod.objects.filter(id=shipping_method_id).first()
        shipping_address, shipping_error = _resolve_checkout_address(shipping_address_id, shipping_address_data, 'shipping')
        if shipping_error:
            return shipping_error

        if billing_address_id in (None, '') and not billing_address_data:
            billing_address = shipping_address
        else:
            billing_address, billing_error = _resolve_checkout_address(billing_address_id, billing_address_data, 'billing')
            if billing_error:
                return billing_error

        if request.user.is_authenticated and contact_email and not request.user.email:
            request.user.email = contact_email
            request.user.save(update_fields=['email'])

        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            shipping_method=shipping_method,
            shipping_address=shipping_address,
            billing_address=billing_address,
            total=Decimal('0.00'),
        )

        for item in cart_items:
            product = locked_products.get(item.product_id) or item.product
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item.quantity,
                price=product.price,
            )
        subtotal = sum(Decimal(str(i.product.price)) * Decimal(i.quantity) for i in cart_items)
        subtotal = subtotal.quantize(Decimal('0.01'))

        if shipping_method:
            shipping_amount = Decimal(str(shipping_method.price or 0)).quantize(Decimal('0.01'))
        else:
            free_threshold = Decimal(str(getattr(settings, 'CHECKOUT_FREE_SHIPPING_THRESHOLD', 100)))
            flat_shipping = Decimal(str(getattr(settings, 'CHECKOUT_FLAT_SHIPPING', 9.99))).quantize(Decimal('0.01'))
            shipping_amount = Decimal('0.00') if subtotal >= free_threshold else flat_shipping

        tax_rate = Decimal(str(getattr(settings, 'CHECKOUT_TAX_RATE', 0.08)))
        tax_amount = (subtotal * tax_rate).quantize(Decimal('0.01'))
        order_total = (subtotal + shipping_amount + tax_amount).quantize(Decimal('0.01'))

        order.total = order_total
        order.save(update_fields=['total'])
        # Keep cart until payment is confirmed successful.
        # Stock is finalized when order payment is marked paid.
        # Track recent checkout orders in session so guest payment endpoints can authorize access.
        checkout_order_ids = request.session.get('checkout_order_ids') or []
        checkout_order_ids = [str(v) for v in checkout_order_ids if str(v).strip()]
        checkout_order_ids.append(str(order.id))
        request.session['checkout_order_ids'] = checkout_order_ids[-25:]
        request.session.modified = True

    logger.info('checkout.create success order_id=%s order_number=%s cart_id=%s', order.id, order.order_number, cart.id)
    _send_order_created_notifications(order, contact_email=contact_email)
    serializer = OrderSerializer(order, context={'request': request})
    return Response(serializer.data)


def _order_is_payable(order: Order) -> bool:
    return order.status == Order.STATUS_PENDING


def _parse_decimal_amount(value):
    if value is None or str(value).strip() == '':
        return None
    try:
        return Decimal(str(value)).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _amount_matches_order_total(order: Order, amount) -> bool:
    parsed = _parse_decimal_amount(amount)
    if parsed is None:
        return False
    expected = Decimal(str(order.total)).quantize(Decimal('0.01'))
    # 1 cent tolerance
    return abs(parsed - expected) <= Decimal('0.01')


def _record_payment_attempt(
    order,
    provider,
    provider_txn_id='',
    amount=None,
    raw_response=None,
    *,
    status='pending',
    currency='USD',
    payer_email='',
    paypal_order_id='',
):
    txn_id = (provider_txn_id or '').strip()
    effective_currency = str(currency or 'USD').upper()
    effective_status = str(status or 'pending').strip().lower()
    effective_paypal_order_id = str(paypal_order_id or '').strip()
    if provider == 'paypal' and not effective_paypal_order_id:
        effective_paypal_order_id = txn_id
    resolved_amount = _parse_decimal_amount(amount) if amount is not None else None
    defaults = {
        'user': order.user if getattr(order, 'user_id', None) else None,
        'paypal_order_id': effective_paypal_order_id,
        'amount': resolved_amount if resolved_amount is not None else order.total,
        'currency': effective_currency,
        'payer_email': str(payer_email or '').strip(),
        'status': effective_status,
        'success': False,
        'raw_response': raw_response or {},
    }
    if txn_id:
        txn, created = PaymentTransaction.objects.get_or_create(
            order=order,
            provider=provider,
            provider_transaction_id=txn_id,
            defaults=defaults,
        )
        if not created:
            updated_fields = []
            if raw_response and txn.raw_response != raw_response:
                txn.raw_response = raw_response
                updated_fields.append('raw_response')
            if resolved_amount is not None and Decimal(str(txn.amount)) != resolved_amount:
                txn.amount = resolved_amount
                updated_fields.append('amount')
            if effective_currency and (txn.currency or '').upper() != effective_currency:
                txn.currency = effective_currency
                updated_fields.append('currency')
            if effective_status and txn.status != effective_status:
                txn.status = effective_status
                updated_fields.append('status')
            if effective_paypal_order_id and txn.paypal_order_id != effective_paypal_order_id:
                txn.paypal_order_id = effective_paypal_order_id
                updated_fields.append('paypal_order_id')
            if payer_email and txn.payer_email != str(payer_email).strip():
                txn.payer_email = str(payer_email).strip()
                updated_fields.append('payer_email')
            if getattr(order, 'user_id', None) and txn.user_id != order.user_id:
                txn.user = order.user
                updated_fields.append('user')
            if updated_fields:
                txn.save(update_fields=updated_fields)
        return txn

    return PaymentTransaction.objects.create(
        user=order.user if getattr(order, 'user_id', None) else None,
        order=order,
        provider=provider,
        paypal_order_id=effective_paypal_order_id,
        provider_transaction_id='',
        amount=resolved_amount if resolved_amount is not None else order.total,
        currency=effective_currency,
        payer_email=str(payer_email or '').strip(),
        status=effective_status,
        success=False,
        raw_response=raw_response or {},
    )


def _paypal_mode():
    configured = (getattr(settings, 'PAYPAL_ENV', '') or getattr(settings, 'PAYPAL_MODE', '') or '').strip().lower()
    if configured in ('live', 'sandbox'):
        return configured
    return 'live' if settings.DEBUG is False else 'sandbox'


def _paypal_base_url():
    return 'https://api-m.paypal.com' if _paypal_mode() == 'live' else 'https://api-m.sandbox.paypal.com'


def _paypal_credentials():
    client_id = (getattr(settings, 'PAYPAL_CLIENT_ID', '') or '').strip()
    client_secret = (
        getattr(settings, 'PAYPAL_CLIENT_SECRET', '')
        or getattr(settings, 'PAYPAL_SECRET', '')
        or ''
    ).strip()
    return client_id, client_secret


def _paypal_config_issue():
    client_id, client_secret = _paypal_credentials()
    if not client_id or not client_secret:
        return 'Missing PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET.'

    if _paypal_mode() == 'live':
        if 'sandbox' in client_id.lower() or 'sandbox' in client_secret.lower():
            return 'PAYPAL_ENV is set to live but sandbox PayPal credentials were detected.'
    return ''


def _paypal_access_token():
    client_id, client_secret = _paypal_credentials()
    if not client_id or not client_secret:
        raise ValueError('paypal_not_configured')

    cache_key = f'paypal_access_token:{_paypal_mode()}:{client_id[:10]}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    resp = requests.post(
        f'{_paypal_base_url()}/v1/oauth2/token',
        data={'grant_type': 'client_credentials'},
        auth=(client_id, client_secret),
        headers={'Accept': 'application/json', 'Accept-Language': 'en_US'},
        timeout=20,
    )
    if resp.status_code >= 400:
        raise RuntimeError(resp.text or 'paypal_oauth_failed')

    data = resp.json() if resp.content else {}
    access_token = data.get('access_token')
    expires_in = int(data.get('expires_in') or 0)
    if not access_token:
        raise RuntimeError('paypal_oauth_missing_access_token')

    ttl = max(60, expires_in - 60) if expires_in else 540
    cache.set(cache_key, access_token, ttl)
    return access_token


def _paypal_api_request(method, path, *, payload=None, extra_headers=None):
    token = _paypal_access_token()
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    if extra_headers:
        headers.update(extra_headers)
    url = f'{_paypal_base_url()}{path}'
    resp = requests.request(method.upper(), url, json=payload, headers=headers, timeout=25)
    text = resp.text or ''
    try:
        data = resp.json() if text else {}
    except Exception:
        data = {'raw': text}
    return resp.status_code, data, text


def _paypal_rate_limit_allow(request, bucket, limit=30, window_seconds=60):
    return _rate_limit_allow(request, bucket=bucket, limit=limit, window_seconds=window_seconds)


def _rate_limit_allow(request, bucket, limit=30, window_seconds=60, *, identifier=''):
    try:
        effective_limit = int(limit)
    except Exception:
        effective_limit = 30
    if effective_limit <= 0:
        return True

    try:
        effective_window = int(window_seconds)
    except Exception:
        effective_window = 60
    effective_window = max(1, effective_window)

    ip = _get_client_ip(request)
    id_part = str(identifier or '').strip().lower()[:120]
    key = f'ratelimit:{bucket}:{ip}:{id_part}' if id_part else f'ratelimit:{bucket}:{ip}'
    current = cache.get(key, 0)
    if current >= effective_limit:
        return False
    cache.set(key, current + 1, effective_window)
    return True


def _rate_limit_response(detail='Too many requests. Please try again shortly.'):
    return Response({'error': 'rate_limited', 'detail': detail}, status=status.HTTP_429_TOO_MANY_REQUESTS)


def _ensure_order_access(request, order):
    if getattr(order, 'user_id', None):
        if not getattr(request.user, 'is_authenticated', False) or request.user.id != order.user_id:
            raise PermissionDenied('You are not allowed to access this order.')
        return

    # Guest order fallback: only allow sessions that created the order.
    session_allowed = request.session.get('checkout_order_ids') or []
    allowed_ids = {str(v) for v in session_allowed if str(v).strip()}
    if str(order.id) not in allowed_ids:
        raise PermissionDenied('You are not allowed to access this guest order.')


def _build_paypal_purchase_unit(order, currency='USD'):
    effective_currency = str(currency or 'USD').upper()
    item_rows = []
    item_total = Decimal('0.00')
    for item in order.items.select_related('product'):
        unit_price = Decimal(str(item.price)).quantize(Decimal('0.01'))
        quantity = max(1, int(item.quantity))
        line_total = (unit_price * Decimal(quantity)).quantize(Decimal('0.01'))
        item_total += line_total
        item_rows.append({
            'name': (item.product.name or f'Product {item.product_id}')[:127],
            'unit_amount': {'currency_code': effective_currency, 'value': f'{unit_price:.2f}'},
            'quantity': str(quantity),
            'category': 'DIGITAL_GOODS' if getattr(item.product, 'is_digital', False) else 'PHYSICAL_GOODS',
        })

    order_total = Decimal(str(order.total)).quantize(Decimal('0.01'))
    if not item_rows:
        raise ValueError('order_has_no_line_items')

    # Keep server-authoritative total. If order.total includes tax/shipping, carry it as shipping in breakdown.
    extra_total = (order_total - item_total).quantize(Decimal('0.01'))
    if extra_total < Decimal('0.00'):
        extra_total = Decimal('0.00')

    breakdown = {
        'item_total': {'currency_code': effective_currency, 'value': f'{item_total:.2f}'},
    }
    if extra_total > Decimal('0.00'):
        breakdown['shipping'] = {'currency_code': effective_currency, 'value': f'{extra_total:.2f}'}

    return {
        'reference_id': f'order-{order.id}',
        'custom_id': str(order.id),
        'invoice_id': str(order.order_number or order.id),
        'description': f'Order {order.id}',
        'amount': {
            'currency_code': effective_currency,
            'value': f'{order_total:.2f}',
            'breakdown': breakdown,
        },
        'items': item_rows,
    }


@api_view(['POST'])
def stripe_create_payment_intent(request):
    order_id = request.data.get('order_id')
    order = get_object_or_404(Order, id=order_id)
    try:
        _ensure_order_access(request, order)
    except PermissionDenied as exc:
        return Response({'error': 'forbidden', 'detail': str(exc)}, status=403)
    if not order.items.exists():
        logger.warning('stripe.checkout_session blocked order_id=%s reason=no_order_items', order.id)
        return Response({'error': 'order_has_no_line_items'}, status=400)
    if not _order_is_payable(order):
        logger.warning('stripe.checkout_session blocked order_id=%s status=%s', order.id, order.status)
        return Response({'error': 'order_not_payable', 'detail': f'Order status is {order.status}'}, status=409)
    if PaymentTransaction.objects.filter(order=order, success=True).exists():
        logger.info('stripe.checkout_session skipped order_id=%s reason=already_paid', order.id)
        return Response({'error': 'order_already_paid'}, status=409)

    redirect_root = (request.data.get('redirect_url') or '').rstrip('/')
    if not redirect_root:
        redirect_root = request.build_absolute_uri('/').rstrip('/')
    stripe_secret = (settings.STRIPE_SECRET_KEY or '').strip()
    stripe_mode = (getattr(settings, 'STRIPE_MODE', 'LIVE') or 'LIVE').strip().upper()
    logger.info(
        'stripe.checkout_session start order_id=%s mode=%s secret_present=%s',
        order.id,
        stripe_mode,
        bool(stripe_secret),
    )

    if not stripe_secret:
        logger.warning('stripe.checkout_session failed order_id=%s reason=missing_secret', order.id)
        return Response(
            {
                'error': 'stripe_not_configured',
                'detail': 'Missing Stripe secret key. Set STRIPE_SECRET_KEY (or STRIPE_API_KEY).'
            },
            status=500
        )

    if not re.match(r'^sk_(test|live)_', stripe_secret):
        logger.warning('stripe.checkout_session failed order_id=%s reason=invalid_secret_format', order.id)
        return Response(
            {
                'error': 'stripe_invalid_key_format',
                'detail': 'Stripe secret key must start with sk_test_ or sk_live_.'
            },
            status=500
        )

    if stripe_mode == 'LIVE' and stripe_secret.startswith('sk_test_'):
        logger.warning('stripe.checkout_session failed order_id=%s reason=test_key_in_live_mode', order.id)
        return Response(
            {
                'error': 'stripe_live_mode_requires_live_key',
                'detail': 'STRIPE_MODE is LIVE but STRIPE_SECRET_KEY is a test key.'
            },
            status=500
        )

    if stripe_mode == 'TEST' and stripe_secret.startswith('sk_live_'):
        logger.warning('stripe.checkout_session failed order_id=%s reason=live_key_in_test_mode', order.id)
        return Response(
            {
                'error': 'stripe_test_mode_requires_test_key',
                'detail': 'STRIPE_MODE is TEST but STRIPE_SECRET_KEY is a live key.'
            },
            status=500
        )

    stripe.api_key = stripe_secret
    try:
        line_items = []
        line_items_total_cents = 0
        for item in order.items.select_related('product'):
            unit_amount = int(Decimal(str(item.price)) * 100)
            qty = int(item.quantity)
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': item.product.name},
                    'unit_amount': unit_amount,
                },
                'quantity': qty,
            })
            line_items_total_cents += unit_amount * qty

        if order.shipping_method and float(order.shipping_method.price or 0) > 0:
            shipping_cents = int(Decimal(str(order.shipping_method.price)) * 100)
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': f'Shipping - {order.shipping_method.name}'},
                    'unit_amount': shipping_cents,
                },
                'quantity': 1,
            })
            line_items_total_cents += shipping_cents
        if not line_items:
            logger.warning('stripe.checkout_session failed order_id=%s reason=no_line_items', order.id)
            return Response({'error': 'order_has_no_line_items'}, status=400)

        expected_total_cents = int(Decimal(str(order.total)) * 100)
        if expected_total_cents > line_items_total_cents:
            balance_cents = expected_total_cents - line_items_total_cents
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': 'Tax & Fees'},
                    'unit_amount': balance_cents,
                },
                'quantity': 1,
            })
            line_items_total_cents += balance_cents
        elif expected_total_cents < line_items_total_cents:
            logger.warning(
                'stripe.checkout_session failed order_id=%s reason=line_items_exceed_total expected=%s computed=%s',
                order.id, expected_total_cents, line_items_total_cents
            )
            return Response({'error': 'invalid_order_total'}, status=400)

        session = stripe.checkout.Session.create(
            mode='payment',
            line_items=line_items,
            success_url=f'{redirect_root}/?payment=success&provider=stripe&order={order.id}&session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{redirect_root}/checkout?payment=cancelled&provider=stripe&order={order.id}',
            metadata={'order_id': str(order.id)},
        )
        _record_payment_attempt(
            order=order,
            provider='stripe',
            provider_txn_id=session.id,
            amount=order.total,
            raw_response={'event': 'checkout_session_created', 'session_id': session.id, 'payment_status': getattr(session, 'payment_status', None)},
        )
        logger.info('stripe.checkout_session created order_id=%s session_id=%s', order.id, session.id)
        return Response({'checkout_url': session.url})
    except stripe.error.AuthenticationError as e:
        logger.warning('stripe.checkout_session auth_failed order_id=%s', order.id)
        return Response({'error': 'stripe_auth_error', 'detail': str(e)}, status=500)
    except stripe.error.StripeError as e:
        logger.warning('stripe.checkout_session stripe_error order_id=%s', order.id)
        return Response({'error': 'stripe_error', 'detail': str(e)}, status=400)
    except Exception as e:
        logger.exception('stripe.checkout_session failed order_id=%s', order.id)
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_confirm_checkout_session(request):
    """
    Fallback confirmation for return-url flow when webhook is delayed/unreachable.
    Verifies Stripe Checkout Session server-side before marking order paid.
    """
    order_id = request.data.get('order_id')
    session_id = (request.data.get('session_id') or '').strip()
    if not order_id or not session_id:
        return Response({'error': 'order_id_and_session_id_required'}, status=400)

    order = get_object_or_404(Order, id=order_id)
    try:
        _ensure_order_access(request, order)
    except PermissionDenied as exc:
        return Response({'error': 'forbidden', 'detail': str(exc)}, status=403)
    if not _order_is_payable(order) and order.status != Order.STATUS_PAID:
        return Response({'error': 'order_not_payable', 'detail': f'Order status is {order.status}'}, status=409)

    stripe_secret = (settings.STRIPE_SECRET_KEY or '').strip()
    if not stripe_secret:
        return Response({'error': 'stripe_not_configured'}, status=500)
    stripe.api_key = stripe_secret

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError as e:
        logger.warning('stripe.confirm_session failed order_id=%s session_id=%s detail=%s', order.id, session_id, str(e))
        return Response({'error': 'stripe_error', 'detail': str(e)}, status=400)
    except Exception as e:
        logger.exception('stripe.confirm_session unexpected_error order_id=%s session_id=%s', order.id, session_id)
        return Response({'error': 'stripe_error', 'detail': str(e)}, status=400)

    metadata = getattr(session, 'metadata', {}) or {}
    session_order_id = str(metadata.get('order_id') or '')
    if session_order_id and str(session_order_id) != str(order.id):
        logger.warning('stripe.confirm_session mismatch order_id=%s metadata_order_id=%s', order.id, session_order_id)
        return Response({'error': 'order_mismatch'}, status=400)

    payment_status = str(getattr(session, 'payment_status', '') or '').lower()
    if payment_status not in ('paid', 'no_payment_required'):
        return Response({'ok': True, 'paid': False, 'status': order.status, 'payment_status': payment_status})

    amount_total = getattr(session, 'amount_total', None)
    amount_decimal = Decimal(str(amount_total)) / Decimal('100') if amount_total is not None else None
    if amount_decimal is not None and not _amount_matches_order_total(order, amount_decimal):
        logger.warning(
            'stripe.confirm_session amount_mismatch order_id=%s session_id=%s provided=%s expected=%s',
            order.id, session_id, amount_decimal, order.total
        )
        _record_payment_attempt(
            order=order,
            provider='stripe',
            provider_txn_id=session_id,
            amount=amount_decimal,
            raw_response={'event': 'confirm_session_amount_mismatch', 'session_id': session_id},
        )
        return Response({'error': 'amount_mismatch'}, status=400)

    provider_txn_id = getattr(session, 'payment_intent', None) or session_id
    customer_details = getattr(session, 'customer_details', None) or {}
    payer_email = ''
    try:
        payer_email = str((customer_details.get('email') if isinstance(customer_details, dict) else None) or getattr(session, 'customer_email', None) or '').strip()
    except Exception:
        payer_email = ''
    txn, created = _record_transaction(
        order,
        'stripe',
        provider_txn_id,
        amount_decimal,
        {'session_id': session_id, 'payment_status': payment_status},
        status='completed',
        currency=str(getattr(session, 'currency', '') or 'USD').upper(),
        payer_email=payer_email,
    )
    if created:
        became_paid = _mark_order_paid_and_finalize(order, provider='stripe', provider_txn_id=provider_txn_id or '')
        if became_paid:
            logger.info('stripe.confirm_session marked_paid order_id=%s session_id=%s', order.id, session_id)
            _send_order_paid_notifications(order, provider='stripe')

    order.refresh_from_db()
    return Response({'ok': True, 'paid': order.status in (Order.STATUS_PAID, Order.STATUS_PROCESSING, Order.STATUS_SHIPPED, Order.STATUS_DELIVERED), 'status': order.status, 'transaction_id': txn.id})


@api_view(['POST'])
def flutterwave_create_payment(request):
    order_id = request.data.get('order_id')
    redirect_url = request.data.get('redirect_url')
    order = get_object_or_404(Order, id=order_id)
    try:
        _ensure_order_access(request, order)
    except PermissionDenied as exc:
        return Response({'error': 'forbidden', 'detail': str(exc)}, status=403)
    if not order.items.exists():
        logger.warning('flutterwave.create_payment blocked order_id=%s reason=no_order_items', order.id)
        return Response({'error': 'order_has_no_line_items'}, status=400)
    if not _order_is_payable(order):
        logger.warning('flutterwave.create_payment blocked order_id=%s status=%s', order.id, order.status)
        return Response({'error': 'order_not_payable', 'detail': f'Order status is {order.status}'}, status=409)
    if PaymentTransaction.objects.filter(order=order, success=True).exists():
        logger.info('flutterwave.create_payment skipped order_id=%s reason=already_paid', order.id)
        return Response({'error': 'order_already_paid'}, status=409)

    flw_secret = (settings.FLUTTERWAVE_SECRET_KEY or '').strip()
    flw_mode = (getattr(settings, 'FLUTTERWAVE_MODE', 'LIVE') or 'LIVE').strip().upper()
    flw_base_url = (getattr(settings, 'FLUTTERWAVE_BASE_URL', 'https://api.flutterwave.com/v3') or 'https://api.flutterwave.com/v3').rstrip('/')
    logger.info(
        'flutterwave.create_payment start order_id=%s mode=%s base_url=%s secret_present=%s',
        order.id,
        flw_mode,
        flw_base_url,
        bool(flw_secret),
    )
    if not flw_secret:
        logger.warning('flutterwave.create_payment failed order_id=%s reason=missing_secret', order.id)
        return Response(
            {
                'error': 'flutterwave_not_configured',
                'detail': (
                    'Missing Flutterwave secret key. Set one of: '
                    'FLUTTERWAVE_SECRET_KEY, FLW_SECRET_KEY, FLW_SECRET, FLUTTERWAVE_SECRET.'
                )
            },
            status=500
        )
    if not re.match(r'^FLWSECK[-_]', flw_secret, flags=re.IGNORECASE):
        logger.warning('flutterwave.create_payment failed order_id=%s reason=invalid_secret_format', order.id)
        return Response(
            {
                'error': 'flutterwave_invalid_key_format',
                'detail': 'Flutterwave secret key must start with FLWSECK- or FLWSECK_.'
            },
            status=500
        )

    if flw_mode == 'LIVE' and 'TEST' in flw_secret.upper():
        logger.warning('flutterwave.create_payment failed order_id=%s reason=test_key_in_live_mode', order.id)
        return Response(
            {
                'error': 'flutterwave_live_mode_requires_live_key',
                'detail': 'FLUTTERWAVE_MODE is LIVE but the provided key appears to be a TEST key.'
            },
            status=500
        )

    if flw_mode == 'TEST' and 'LIVE' in flw_secret.upper():
        logger.warning('flutterwave.create_payment failed order_id=%s reason=live_key_in_test_mode', order.id)
        return Response(
            {
                'error': 'flutterwave_test_mode_requires_test_key',
                'detail': 'FLUTTERWAVE_MODE is TEST but the provided key appears to be a LIVE key.'
            },
            status=500
        )

    tx_ref = f'order-{order.id}-{uuid4().hex[:8]}'
    headers = {
        'Authorization': f'Bearer {flw_secret}',
        'Content-Type': 'application/json'
    }
    payload = {
        'tx_ref': tx_ref,
        'amount': str(order.total),
        'currency': 'USD',
        'redirect_url': redirect_url,
        'customer': {
            'email': request.user.email if request.user.is_authenticated else 'guest@example.com',
            'name': request.user.get_full_name() if request.user.is_authenticated else 'Guest'
        },
        'customizations': {
            'title': 'De-Rukkies Checkout',
            'description': f'Payment for order {order.order_number or order.id}',
        },
        'meta': {
            'order_id': str(order.id),
            'order_number': str(order.order_number or ''),
        },
    }
    try:
        resp = requests.post(f'{flw_base_url}/payments', json=payload, headers=headers, timeout=20)
    except requests.RequestException as exc:
        logger.exception('flutterwave.create_payment failed order_id=%s reason=request_exception', order.id)
        return Response(
            {'error': 'flutterwave_unreachable', 'detail': str(exc)},
            status=502
        )

    if resp.status_code not in (200, 201):
        logger.warning('flutterwave.create_payment failed order_id=%s status=%s', order.id, resp.status_code)
        return Response({'error': 'flutterwave error', 'detail': resp.text}, status=400)

    try:
        data = resp.json()
    except ValueError:
        logger.warning('flutterwave.create_payment failed order_id=%s reason=invalid_json', order.id)
        return Response({'error': 'flutterwave error', 'detail': 'Invalid response from Flutterwave'}, status=400)

    link = data.get('data', {}).get('link')
    if not link:
        logger.warning('flutterwave.create_payment failed order_id=%s reason=missing_link', order.id)
        return Response({'error': 'flutterwave error', 'detail': data}, status=400)
    _record_payment_attempt(
        order=order,
        provider='flutterwave',
        provider_txn_id=tx_ref,
        amount=order.total,
        raw_response={'event': 'payment_link_created', 'tx_ref': tx_ref, 'link': link},
    )
    logger.info('flutterwave.create_payment success order_id=%s', order.id)
    return Response({'link': link})


@api_view(['POST'])
@permission_classes([AllowAny])
def flutterwave_confirm_payment(request):
    """
    Confirm Flutterwave payment from return URL flow when webhook is delayed/unreachable.
    """
    order_id = request.data.get('order_id')
    transaction_id = str(request.data.get('transaction_id') or '').strip()
    tx_ref = str(request.data.get('tx_ref') or '').strip()
    redirect_status = str(request.data.get('status') or '').strip().lower()

    if not order_id:
        return Response({'error': 'order_id_required'}, status=400)

    order = get_object_or_404(Order, id=order_id)
    try:
        _ensure_order_access(request, order)
    except PermissionDenied as exc:
        return Response({'error': 'forbidden', 'detail': str(exc)}, status=403)
    if order.status in PAID_ORDER_STATUSES:
        return Response({'ok': True, 'paid': True, 'status': order.status})
    if not _order_is_payable(order):
        return Response({'error': 'order_not_payable', 'detail': f'Order status is {order.status}'}, status=409)

    if redirect_status and redirect_status not in ('successful', 'completed'):
        return Response({'ok': True, 'paid': False, 'status': order.status, 'payment_status': redirect_status})

    flw_secret = (settings.FLUTTERWAVE_SECRET_KEY or '').strip()
    flw_base_url = (getattr(settings, 'FLUTTERWAVE_BASE_URL', 'https://api.flutterwave.com/v3') or 'https://api.flutterwave.com/v3').rstrip('/')
    if not flw_secret:
        return Response({'error': 'flutterwave_not_configured'}, status=500)

    headers = {'Authorization': f'Bearer {flw_secret}'}
    if transaction_id:
        verify_url = f'{flw_base_url}/transactions/{transaction_id}/verify'
    elif tx_ref:
        verify_url = f'{flw_base_url}/transactions/verify_by_reference?tx_ref={tx_ref}'
    else:
        return Response({'error': 'transaction_reference_required'}, status=400)

    try:
        resp = requests.get(verify_url, headers=headers, timeout=20)
    except requests.RequestException as exc:
        logger.warning('flutterwave.confirm failed order_id=%s reason=request_exception detail=%s', order.id, str(exc))
        return Response({'error': 'flutterwave_unreachable', 'detail': str(exc)}, status=502)

    if resp.status_code not in (200, 201):
        logger.warning('flutterwave.confirm failed order_id=%s status=%s', order.id, resp.status_code)
        return Response({'error': 'flutterwave_error', 'detail': resp.text}, status=400)

    try:
        payload = resp.json()
    except ValueError:
        return Response({'error': 'flutterwave_error', 'detail': 'Invalid response from Flutterwave'}, status=400)

    fw_data = payload.get('data') or {}
    payment_status = str(fw_data.get('status') or '').strip().lower()
    if payment_status not in ('successful', 'completed'):
        return Response({'ok': True, 'paid': False, 'status': order.status, 'payment_status': payment_status})

    effective_tx_ref = str(fw_data.get('tx_ref') or tx_ref or '').strip()
    meta_order_id = str((fw_data.get('meta') or {}).get('order_id') or '').strip()
    tx_ref_match = re.match(r'^order-(\d+)', effective_tx_ref)
    tx_ref_order_id = tx_ref_match.group(1) if tx_ref_match else ''
    if meta_order_id and str(meta_order_id) != str(order.id):
        logger.warning('flutterwave.confirm order_mismatch order_id=%s meta_order_id=%s', order.id, meta_order_id)
        return Response({'error': 'order_mismatch'}, status=400)
    if tx_ref_order_id and str(tx_ref_order_id) != str(order.id):
        logger.warning('flutterwave.confirm tx_ref_mismatch order_id=%s tx_ref_order_id=%s', order.id, tx_ref_order_id)
        return Response({'error': 'order_mismatch'}, status=400)

    amount = fw_data.get('amount')
    if amount is not None and not _amount_matches_order_total(order, amount):
        logger.warning(
            'flutterwave.confirm amount_mismatch order_id=%s provided=%s expected=%s',
            order.id, amount, order.total
        )
        _record_payment_attempt(
            order=order,
            provider='flutterwave',
            provider_txn_id=str(fw_data.get('id') or transaction_id or effective_tx_ref or ''),
            amount=_parse_decimal_amount(amount),
            raw_response={'event': 'confirm_amount_mismatch', 'payload': payload},
        )
        return Response({'error': 'amount_mismatch'}, status=400)

    provider_txn_id = str(fw_data.get('id') or transaction_id or effective_tx_ref or '')
    txn, created = _record_transaction(
        order,
        'flutterwave',
        provider_txn_id,
        amount,
        {'event': 'confirm_redirect', 'transaction_id': transaction_id, 'tx_ref': effective_tx_ref, 'payload': payload},
    )
    if created:
        became_paid = _mark_order_paid_and_finalize(order, provider='flutterwave', provider_txn_id=provider_txn_id)
        if became_paid:
            logger.info('flutterwave.confirm marked_paid order_id=%s txn_id=%s', order.id, provider_txn_id)
            _send_order_paid_notifications(order, provider='flutterwave')

    order.refresh_from_db()
    return Response({'ok': True, 'paid': order.status in PAID_ORDER_STATUSES, 'status': order.status, 'transaction_id': txn.id})


@api_view(['GET'])
@permission_classes([AllowAny])
def paypal_client_config(request):
    config_issue = _paypal_config_issue()
    if config_issue:
        return Response(
            {'error': 'paypal_not_configured', 'detail': config_issue},
            status=500,
        )
    client_id, _ = _paypal_credentials()
    return Response(
        {
            'client_id': client_id,
            'env': _paypal_mode(),
            'currency': 'USD',
            'merchant_supports_cards': True,
            'card_only_checkout': True,
        }
    )


def _extract_paypal_capture_from_response(payload):
    units = payload.get('purchase_units') or []
    capture = {}
    if units:
        payments = (units[0] or {}).get('payments') or {}
        captures = payments.get('captures') or []
        if captures:
            capture = captures[0] or {}

    amount_obj = capture.get('amount') or {}
    amount_value = amount_obj.get('value') or ''
    currency_code = (amount_obj.get('currency_code') or '').upper() or 'USD'
    capture_id = str(capture.get('id') or '').strip()
    status = str(capture.get('status') or payload.get('status') or '').strip().lower() or 'pending'
    payer_email = str((payload.get('payer') or {}).get('email_address') or '').strip()
    return {
        'capture_id': capture_id,
        'status': status,
        'amount': amount_value,
        'currency': currency_code,
        'payer_email': payer_email,
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def paypal_create_order(request):
    if not _paypal_rate_limit_allow(
        request,
        bucket='paypal_create_order',
        limit=getattr(settings, 'RATE_LIMIT_PAYPAL_CREATE_ORDER_LIMIT', 40),
        window_seconds=getattr(settings, 'RATE_LIMIT_PAYPAL_CREATE_ORDER_WINDOW_SECONDS', 60),
    ):
        return Response({'error': 'rate_limited', 'detail': 'Too many PayPal attempts. Please try again shortly.'}, status=429)

    config_issue = _paypal_config_issue()
    if config_issue:
        return Response({'error': 'paypal_not_configured', 'detail': config_issue}, status=500)

    order_id = request.data.get('order_id')
    currency = str(request.data.get('currency') or 'USD').strip().upper()
    if not order_id:
        return Response({'error': 'order_id_required'}, status=400)
    if currency != 'USD':
        return Response({'error': 'unsupported_currency', 'detail': 'Only USD is currently supported.'}, status=400)

    order = get_object_or_404(Order, id=order_id)
    try:
        _ensure_order_access(request, order)
    except PermissionDenied as exc:
        return Response({'error': 'forbidden', 'detail': str(exc)}, status=403)

    if not order.items.exists():
        return Response({'error': 'order_has_no_line_items'}, status=400)
    if not _order_is_payable(order):
        return Response({'error': 'order_not_payable', 'detail': f'Order status is {order.status}'}, status=409)
    if PaymentTransaction.objects.filter(order=order, success=True).exists():
        return Response({'error': 'order_already_paid'}, status=409)

    try:
        purchase_unit = _build_paypal_purchase_unit(order, currency=currency)
    except ValueError as exc:
        return Response({'error': str(exc)}, status=400)

    payload = {
        'intent': 'CAPTURE',
        'purchase_units': [purchase_unit],
        'application_context': {
            'brand_name': 'De-Rukkies Collections',
            'user_action': 'PAY_NOW',
            'landing_page': 'BILLING',
            'shipping_preference': 'SET_PROVIDED_ADDRESS',
        },
    }

    request_id = f'order-{order.id}-{uuid4().hex[:10]}'
    try:
        status_code, data, raw_text = _paypal_api_request(
            'POST',
            '/v2/checkout/orders',
            payload=payload,
            extra_headers={'PayPal-Request-Id': request_id},
        )
    except ValueError:
        return Response({'error': 'paypal_not_configured', 'detail': 'Missing PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET.'}, status=500)
    except Exception as exc:
        logger.exception('paypal.create_order request_failed order_id=%s', order.id)
        return Response({'error': 'paypal_unreachable', 'detail': str(exc)}, status=502)

    if status_code not in (200, 201):
        logger.warning('paypal.create_order failed order_id=%s status=%s detail=%s', order.id, status_code, raw_text[:500])
        _record_payment_attempt(
            order=order,
            provider='paypal',
            provider_txn_id='',
            amount=order.total,
            status='failed',
            currency=currency,
            raw_response={'event': 'create_order_failed', 'status_code': status_code, 'payload': data},
        )
        return Response({'error': 'paypal_create_order_failed', 'detail': data}, status=400)

    paypal_order_id = str(data.get('id') or '').strip()
    paypal_status = str(data.get('status') or 'created').strip().lower()
    _record_payment_attempt(
        order=order,
        provider='paypal',
        provider_txn_id=paypal_order_id,
        paypal_order_id=paypal_order_id,
        amount=order.total,
        status=paypal_status or 'created',
        currency=currency,
        raw_response={'event': 'paypal_order_created', 'payload': data},
    )
    logger.info('paypal.create_order success order_id=%s paypal_order_id=%s status=%s', order.id, paypal_order_id, paypal_status)
    return Response({'orderID': paypal_order_id, 'status': paypal_status or 'created'})


@api_view(['POST'])
@permission_classes([AllowAny])
def paypal_capture_order(request):
    if not _paypal_rate_limit_allow(
        request,
        bucket='paypal_capture_order',
        limit=getattr(settings, 'RATE_LIMIT_PAYPAL_CAPTURE_ORDER_LIMIT', 40),
        window_seconds=getattr(settings, 'RATE_LIMIT_PAYPAL_CAPTURE_ORDER_WINDOW_SECONDS', 60),
    ):
        return Response({'error': 'rate_limited', 'detail': 'Too many PayPal attempts. Please try again shortly.'}, status=429)

    config_issue = _paypal_config_issue()
    if config_issue:
        return Response({'error': 'paypal_not_configured', 'detail': config_issue}, status=500)

    order_id = request.data.get('order_id')
    paypal_order_id = str(request.data.get('paypal_order_id') or request.data.get('orderID') or '').strip()
    if not order_id:
        return Response({'error': 'order_id_required'}, status=400)
    if not paypal_order_id:
        return Response({'error': 'paypal_order_id_required'}, status=400)

    order = get_object_or_404(Order, id=order_id)
    try:
        _ensure_order_access(request, order)
    except PermissionDenied as exc:
        return Response({'error': 'forbidden', 'detail': str(exc)}, status=403)

    if order.status in PAID_ORDER_STATUSES:
        return Response({'ok': True, 'paid': True, 'status': order.status})
    if not _order_is_payable(order):
        return Response({'error': 'order_not_payable', 'detail': f'Order status is {order.status}'}, status=409)

    try:
        status_code, data, raw_text = _paypal_api_request('POST', f'/v2/checkout/orders/{paypal_order_id}/capture', payload={})
    except ValueError:
        return Response({'error': 'paypal_not_configured', 'detail': 'Missing PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET.'}, status=500)
    except Exception as exc:
        logger.exception('paypal.capture_order request_failed order_id=%s paypal_order_id=%s', order.id, paypal_order_id)
        return Response({'error': 'paypal_unreachable', 'detail': str(exc)}, status=502)

    if status_code not in (200, 201):
        logger.warning(
            'paypal.capture_order failed order_id=%s paypal_order_id=%s status=%s detail=%s',
            order.id, paypal_order_id, status_code, raw_text[:500]
        )
        _record_payment_attempt(
            order=order,
            provider='paypal',
            provider_txn_id=paypal_order_id,
            paypal_order_id=paypal_order_id,
            amount=order.total,
            status='failed',
            currency='USD',
            raw_response={'event': 'capture_failed', 'status_code': status_code, 'payload': data},
        )
        return Response({'error': 'paypal_capture_failed', 'detail': data}, status=400)

    capture_data = _extract_paypal_capture_from_response(data)
    capture_amount = capture_data['amount']
    capture_currency = capture_data['currency'] or 'USD'
    capture_id = capture_data['capture_id'] or paypal_order_id
    capture_status = capture_data['status']
    payer_email = capture_data['payer_email']

    if capture_currency != 'USD':
        _record_payment_attempt(
            order=order,
            provider='paypal',
            provider_txn_id=capture_id,
            paypal_order_id=paypal_order_id,
            amount=capture_amount or order.total,
            status='failed',
            currency=capture_currency,
            payer_email=payer_email,
            raw_response={'event': 'capture_currency_mismatch', 'payload': data},
        )
        return Response({'error': 'currency_mismatch', 'detail': f'Expected USD, got {capture_currency}.'}, status=400)

    if not _amount_matches_order_total(order, capture_amount):
        logger.warning(
            'paypal.capture_order amount_mismatch order_id=%s paypal_order_id=%s provided=%s expected=%s',
            order.id, paypal_order_id, capture_amount, order.total
        )
        _record_payment_attempt(
            order=order,
            provider='paypal',
            provider_txn_id=capture_id,
            paypal_order_id=paypal_order_id,
            amount=_parse_decimal_amount(capture_amount) if capture_amount else order.total,
            status='failed',
            currency='USD',
            payer_email=payer_email,
            raw_response={'event': 'capture_amount_mismatch', 'payload': data},
        )
        return Response({'error': 'amount_mismatch'}, status=400)

    txn, created = _record_transaction(
        order=order,
        provider='paypal',
        provider_txn_id=capture_id,
        paypal_order_id=paypal_order_id,
        amount=capture_amount,
        currency='USD',
        payer_email=payer_email,
        status='completed' if capture_status == 'completed' else capture_status,
        raw_response={'event': 'capture_completed', 'payload': data},
    )
    if created:
        became_paid = _mark_order_paid_and_finalize(order, provider='paypal', provider_txn_id=capture_id)
        if became_paid:
            logger.info('paypal.capture_order marked_paid order_id=%s txn_id=%s paypal_order_id=%s', order.id, capture_id, paypal_order_id)
            _send_order_paid_notifications(order, provider='paypal')

    order.refresh_from_db()
    return Response(
        {
            'ok': True,
            'paid': order.status in PAID_ORDER_STATUSES,
            'status': order.status,
            'transaction_id': txn.id,
            'payer_email': payer_email,
            'paypal_order_id': paypal_order_id,
        }
    )


@api_view(['POST'])
def paypal_create_payment(request):
    order_id = request.data.get('order_id')
    return_url = request.data.get('return_url')
    cancel_url = request.data.get('cancel_url')
    checkout_option = str(request.data.get('checkout_option') or 'paypal').strip().lower()
    if checkout_option not in ('paypal', 'card'):
        checkout_option = 'paypal'
    order = get_object_or_404(Order, id=order_id)
    try:
        _ensure_order_access(request, order)
    except PermissionDenied as exc:
        return Response({'error': 'forbidden', 'detail': str(exc)}, status=403)
    if not order.items.exists():
        logger.warning('paypal.create_payment blocked order_id=%s reason=no_order_items', order.id)
        return Response({'error': 'order_has_no_line_items'}, status=400)
    if not _order_is_payable(order):
        logger.warning('paypal.create_payment blocked order_id=%s status=%s', order.id, order.status)
        return Response({'error': 'order_not_payable', 'detail': f'Order status is {order.status}'}, status=409)
    if PaymentTransaction.objects.filter(order=order, success=True).exists():
        logger.info('paypal.create_payment skipped order_id=%s reason=already_paid', order.id)
        return Response({'error': 'order_already_paid'}, status=409)
    logger.info('paypal.create_payment start order_id=%s checkout_option=%s', order.id, checkout_option)

    paypal_client_id = (settings.PAYPAL_CLIENT_ID or '').strip()
    paypal_secret = (settings.PAYPAL_SECRET or '').strip()
    if not paypal_client_id or not paypal_secret:
        logger.warning('paypal.create_payment failed order_id=%s reason=missing_credentials', order.id)
        return Response({'error': 'paypal_not_configured', 'detail': 'Missing PAYPAL_CLIENT_ID or PAYPAL_SECRET.'}, status=500)

    paypalrestsdk.configure({
        'mode': _paypal_mode(),
        'client_id': paypal_client_id,
        'client_secret': paypal_secret,
    })

    payment = paypalrestsdk.Payment({
        'intent': 'sale',
        'payer': {'payment_method': 'paypal'},
        'redirect_urls': {
            'return_url': return_url,
            'cancel_url': cancel_url,
        },
        'transactions': [{
            'item_list': {'items': []},
            'amount': {'total': str(order.total), 'currency': 'USD'},
            'description': f'Order {order.id}'
        }]
    })

    if payment.create():
        for link in payment.links:
            if link.rel == 'approval_url':
                approval_url = str(link.href)
                if checkout_option == 'card':
                    sep = '&' if '?' in approval_url else '?'
                    approval_url = f'{approval_url}{sep}landing_page=Billing&useraction=commit'
                _record_payment_attempt(
                    order=order,
                    provider='paypal',
                    provider_txn_id=getattr(payment, 'id', '') or '',
                    amount=order.total,
                    raw_response={
                        'event': 'approval_url_created',
                        'payment_id': getattr(payment, 'id', ''),
                        'approval_url': approval_url,
                        'checkout_option': checkout_option,
                    },
                )
                logger.info('paypal.create_payment success order_id=%s checkout_option=%s', order.id, checkout_option)
                return Response({'approval_url': approval_url})
    logger.warning('paypal.create_payment failed order_id=%s', order.id)
    return Response({'error': 'paypal create failed'}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def paypal_confirm_payment(request):
    """
    Confirm PayPal payment from return URL flow when webhook is delayed/unreachable.
    """
    order_id = request.data.get('order_id')
    payment_id = str(request.data.get('payment_id') or request.data.get('paymentId') or '').strip()
    payer_id = str(request.data.get('payer_id') or request.data.get('PayerID') or '').strip()

    if not order_id:
        return Response({'error': 'order_id_required'}, status=400)
    if not payment_id:
        return Response({'error': 'payment_id_required'}, status=400)

    order = get_object_or_404(Order, id=order_id)
    try:
        _ensure_order_access(request, order)
    except PermissionDenied as exc:
        return Response({'error': 'forbidden', 'detail': str(exc)}, status=403)
    if order.status in PAID_ORDER_STATUSES:
        return Response({'ok': True, 'paid': True, 'status': order.status})
    if not _order_is_payable(order):
        return Response({'error': 'order_not_payable', 'detail': f'Order status is {order.status}'}, status=409)

    paypal_client_id = (settings.PAYPAL_CLIENT_ID or '').strip()
    paypal_secret = (settings.PAYPAL_SECRET or '').strip()
    if not paypal_client_id or not paypal_secret:
        return Response({'error': 'paypal_not_configured'}, status=500)

    paypalrestsdk.configure({
        'mode': _paypal_mode(),
        'client_id': paypal_client_id,
        'client_secret': paypal_secret,
    })

    try:
        payment = paypalrestsdk.Payment.find(payment_id)
    except Exception as e:
        logger.warning('paypal.confirm find_failed order_id=%s payment_id=%s detail=%s', order.id, payment_id, str(e))
        return Response({'error': 'paypal_error', 'detail': str(e)}, status=400)

    payment_state = str(getattr(payment, 'state', '') or '').lower()
    if payment_state not in ('approved', 'completed'):
        if not payer_id:
            return Response({'error': 'payer_id_required'}, status=400)
        try:
            executed = payment.execute({'payer_id': payer_id})
        except Exception as e:
            logger.warning('paypal.confirm execute_failed order_id=%s payment_id=%s detail=%s', order.id, payment_id, str(e))
            return Response({'error': 'paypal_error', 'detail': str(e)}, status=400)
        if not executed:
            return Response({'error': 'paypal_execute_failed', 'detail': getattr(payment, 'error', None)}, status=400)
        payment_state = str(getattr(payment, 'state', '') or '').lower()

    if payment_state not in ('approved', 'completed'):
        return Response({'ok': True, 'paid': False, 'status': order.status, 'payment_status': payment_state})

    payment_data = payment.to_dict() if hasattr(payment, 'to_dict') else {}
    transactions = payment_data.get('transactions') or []
    tx0 = transactions[0] if transactions else {}
    description = str(tx0.get('description') or '')
    desc_match = re.search(r'Order\s*(\d+)', description)
    if desc_match and str(desc_match.group(1)) != str(order.id):
        logger.warning('paypal.confirm order_mismatch order_id=%s description=%s', order.id, description)
        return Response({'error': 'order_mismatch'}, status=400)

    amount = ((tx0.get('amount') or {}).get('total') if tx0 else None)
    if amount is not None and not _amount_matches_order_total(order, amount):
        logger.warning('paypal.confirm amount_mismatch order_id=%s provided=%s expected=%s', order.id, amount, order.total)
        _record_payment_attempt(
            order=order,
            provider='paypal',
            provider_txn_id=payment_id,
            amount=_parse_decimal_amount(amount),
            raw_response={'event': 'confirm_amount_mismatch', 'payload': payment_data},
        )
        return Response({'error': 'amount_mismatch'}, status=400)

    provider_txn_id = payment_id
    related_resources = tx0.get('related_resources') or []
    for resource in related_resources:
        sale = resource.get('sale') or {}
        if sale.get('id'):
            provider_txn_id = str(sale.get('id'))
            break

    txn, created = _record_transaction(
        order,
        'paypal',
        provider_txn_id,
        amount,
        {'event': 'confirm_redirect', 'payment_id': payment_id, 'payer_id': payer_id, 'payload': payment_data},
    )
    if created:
        became_paid = _mark_order_paid_and_finalize(order, provider='paypal', provider_txn_id=provider_txn_id)
        if became_paid:
            logger.info('paypal.confirm marked_paid order_id=%s txn_id=%s', order.id, provider_txn_id)
            _send_order_paid_notifications(order, provider='paypal')

    order.refresh_from_db()
    return Response({'ok': True, 'paid': order.status in PAID_ORDER_STATUSES, 'status': order.status, 'transaction_id': txn.id})


# Note: `flutterwave_create_payment` is defined above; no duplicate placeholder needed.


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Create a new inactive user and send email verification link."""
    username = request.data.get('username')
    email = (request.data.get('email') or '').strip().lower()
    throttle_identifier = (email or username or 'unknown')[:120]
    if not _rate_limit_allow(
        request,
        bucket='auth_register',
        limit=getattr(settings, 'RATE_LIMIT_AUTH_REGISTER_LIMIT', 8),
        window_seconds=getattr(settings, 'RATE_LIMIT_AUTH_REGISTER_WINDOW_SECONDS', 600),
        identifier=throttle_identifier,
    ):
        logger.warning('auth.register rate_limited ip=%s username=%s email=%s', _get_client_ip(request), username or 'missing', email or 'missing')
        return _rate_limit_response('Too many registration attempts. Please try again later.')

    password = request.data.get('password')
    first_name = (request.data.get('first_name') or '').strip()
    last_name = (request.data.get('last_name') or '').strip()
    client_ip = _get_client_ip(request)
    logger.info('auth.register received username=%s email=%s ip=%s', username or 'missing', email or 'missing', client_ip)

    if not username or not password or not email:
        logger.warning('auth.register validation_failed ip=%s reason=missing_required_fields', client_ip)
        return Response({'error': 'username, email and password required'}, status=400)
    if User.objects.filter(username=username).exists():
        logger.warning('auth.register rejected ip=%s reason=username_taken username=%s', client_ip, username)
        return Response({'error': 'username_taken'}, status=400)
    if User.objects.filter(email=email).exists():
        logger.warning('auth.register rejected ip=%s reason=email_taken email=%s', client_ip, email)
        return Response({'error': 'email_taken'}, status=400)

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        is_active=False,
    )
    logger.info('auth.register created user_id=%s username=%s email=%s', user.id, user.username, user.email)

    _send_verification_email(request, user)
    logger.info('auth.register completed user_id=%s username=%s', user.id, user.username)
    return Response(
        {
            'ok': True,
            'username': user.get_username(),
            'message': 'Verification link sent to your email. Please verify to complete signup.',
        },
        status=201
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email_view(request, uidb64, token):
    client_ip = _get_client_ip(request)
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        user = None
        logger.warning('auth.verify failed ip=%s reason=invalid_uid uidb64=%s', client_ip, uidb64)

    if user and default_token_generator.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])
            logger.info('auth.verify activated user_id=%s username=%s ip=%s', user.id, user.username, client_ip)
            if user.email:
                subject = 'Welcome to De-Rukkies Collections'
                welcome_message = (
                    f'Hi {user.get_full_name() or user.username},\n\n'
                    'Your email has been verified successfully. Your account is now active.\n\n'
                    'Welcome to De-Rukkies Collections.'
                )
                _safe_send_email(
                    subject=subject,
                    message=welcome_message,
                    recipient_list=[user.email],
                    event_name='auth.verify.welcome',
                    html_message=render_react_email_html(
                        'WelcomeEmail',
                        {
                            'userName': user.get_full_name() or user.username,
                            'shopUrl': f'{get_public_site_url(request)}/products',
                            'promoCode': 'WELCOME15',
                            'siteName': 'De-Rukkies Collections',
                            'supportEmail': _contact_recipient(),
                        },
                    ),
                )
            _create_user_notification(
                user,
                title='Email verified',
                message='Your account is now active. You can log in and continue shopping.',
                level=UserNotification.LEVEL_SUCCESS,
            )
            _create_user_mailbox_message(
                user,
                subject='Welcome to De-Rukkies Collections',
                body='Your email has been verified successfully. Your account is now active.',
                category=UserMailboxMessage.CATEGORY_ACCOUNT,
            )
        else:
            logger.info('auth.verify already_active user_id=%s username=%s ip=%s', user.id, user.username, client_ip)
        return redirect('/account?verified=1')

    if user:
        logger.warning('auth.verify failed ip=%s reason=invalid_token user_id=%s username=%s', client_ip, user.id, user.username)
    return redirect('/account?verified=0')


@api_view(['POST'])
@permission_classes([AllowAny])
def payment_verify_mark_paid(request):
    """Simplified endpoint to mark an order paid after server-side verification.
    In production, use webhooks and verify signatures.
    """
    order_id = request.data.get('order_id')
    provider = (request.data.get('provider') or '').strip()
    provider_txn_id = request.data.get('transaction_id')
    amount = request.data.get('amount')
    logger.info('payment.verify attempt order_id=%s provider=%s txn_id=%s', order_id, provider, provider_txn_id or '')

    verify_token = (getattr(settings, 'PAYMENT_VERIFY_TOKEN', '') or '').strip()
    if not verify_token:
        logger.error('payment.verify disabled reason=missing_verify_token')
        return Response(
            {'error': 'payment_verify_disabled', 'detail': 'PAYMENT_VERIFY_TOKEN is not configured.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    provided = request.data.get('verify_token') or request.headers.get('X-VERIFY-TOKEN')
    if not provided or not hmac.compare_digest(str(provided), verify_token):
        logger.warning('payment.verify failed order_id=%s reason=invalid_verify_token', order_id)
        return Response({'error': 'verification_failed'}, status=status.HTTP_403_FORBIDDEN)

    order = get_object_or_404(Order, id=order_id)
    try:
        _ensure_order_access(request, order)
    except PermissionDenied as exc:
        return Response({'error': 'forbidden', 'detail': str(exc)}, status=403)
    if not provider:
        logger.warning('payment.verify failed order_id=%s reason=missing_provider', order.id)
        return Response({'error': 'provider_required'}, status=400)
    if not _order_is_payable(order) and order.status != Order.STATUS_PAID:
        logger.warning('payment.verify blocked order_id=%s reason=order_not_payable status=%s', order.id, order.status)
        return Response({'error': 'order_not_payable', 'detail': f'Order status is {order.status}'}, status=409)

    parsed_amount = _parse_decimal_amount(amount)
    if amount is not None and str(amount).strip() != '' and not _amount_matches_order_total(order, parsed_amount):
        logger.warning(
            'payment.verify amount_mismatch order_id=%s provider=%s txn_id=%s provided=%s expected=%s',
            order.id, provider, provider_txn_id or '', amount, order.total
        )
        _record_payment_attempt(
            order=order,
            provider=provider or 'manual',
            provider_txn_id=provider_txn_id or '',
            amount=parsed_amount if parsed_amount is not None else order.total,
            raw_response={'event': 'verify_amount_mismatch', 'payload': request.data},
        )
        return Response({'error': 'amount_mismatch'}, status=400)

    if provider_txn_id:
        existing = PaymentTransaction.objects.filter(provider_transaction_id=provider_txn_id, provider=provider).first()
        if existing:
            if existing.success:
                logger.info('payment.verify duplicate order_id=%s provider=%s txn_id=%s', order.id, provider, provider_txn_id)
                became_paid = _mark_order_paid_and_finalize(order, provider=provider or 'manual', provider_txn_id=provider_txn_id or '')
                if became_paid:
                    logger.info('payment.verify recovered_finalize order_id=%s provider=%s txn_id=%s', order.id, provider, provider_txn_id or '')
                    _send_order_paid_notifications(order, provider=provider or 'manual')
                return Response({'ok': True, 'transaction_id': existing.id, 'note': 'already_recorded'})
            existing.success = True
            parsed_amount_existing = _parse_decimal_amount(amount)
            if parsed_amount_existing is not None:
                existing.amount = parsed_amount_existing
            existing.raw_response = request.data
            existing.save(update_fields=['success', 'amount', 'raw_response'])
            became_paid = _mark_order_paid_and_finalize(order, provider=provider or 'manual', provider_txn_id=provider_txn_id or '')
            if became_paid:
                logger.info('payment.verify success order_id=%s provider=%s txn_id=%s', order.id, provider, provider_txn_id or '')
                _send_order_paid_notifications(order, provider=provider or 'manual')
            return Response({'ok': True, 'transaction_id': existing.id, 'note': 'updated_existing'})

    txn = PaymentTransaction.objects.create(
        order=order,
        provider=provider,
        provider_transaction_id=provider_txn_id or '',
        amount=parsed_amount if parsed_amount is not None else order.total,
        success=True,
        raw_response=request.data,
    )
    became_paid = _mark_order_paid_and_finalize(order, provider=provider or 'manual', provider_txn_id=provider_txn_id or '')
    if became_paid:
        logger.info('payment.verify success order_id=%s provider=%s txn_id=%s', order.id, provider, provider_txn_id or '')
        _send_order_paid_notifications(order, provider=provider or 'manual')
    else:
        logger.info('payment.verify already_paid order_id=%s provider=%s txn_id=%s', order.id, provider, provider_txn_id or '')
    return Response({'ok': True, 'transaction_id': txn.id})


def _record_transaction(
    order,
    provider,
    provider_txn_id,
    amount,
    raw_response,
    *,
    status='completed',
    currency='USD',
    payer_email='',
    paypal_order_id='',
):
    resolved_amount = _parse_decimal_amount(amount)
    effective_currency = str(currency or 'USD').upper()
    effective_status = str(status or 'completed').strip().lower()
    effective_txn_id = str(provider_txn_id or '').strip()
    effective_paypal_order_id = str(paypal_order_id or '').strip()
    if provider == 'paypal' and not effective_paypal_order_id:
        effective_paypal_order_id = effective_txn_id

    if provider_txn_id:
        existing = PaymentTransaction.objects.filter(provider_transaction_id=provider_txn_id, provider=provider).first()
        if existing:
            if existing.success:
                return existing, getattr(order, 'status', None) not in PAID_ORDER_STATUSES
            updated_fields = []
            existing.success = True
            updated_fields.append('success')
            if resolved_amount is not None:
                existing.amount = resolved_amount
                updated_fields.append('amount')
            if effective_currency and (existing.currency or '').upper() != effective_currency:
                existing.currency = effective_currency
                updated_fields.append('currency')
            if effective_status and existing.status != effective_status:
                existing.status = effective_status
                updated_fields.append('status')
            if effective_paypal_order_id and existing.paypal_order_id != effective_paypal_order_id:
                existing.paypal_order_id = effective_paypal_order_id
                updated_fields.append('paypal_order_id')
            if payer_email and existing.payer_email != str(payer_email).strip():
                existing.payer_email = str(payer_email).strip()
                updated_fields.append('payer_email')
            if getattr(order, 'user_id', None) and existing.user_id != order.user_id:
                existing.user = order.user
                updated_fields.append('user')
            if raw_response is not None:
                existing.raw_response = raw_response
                updated_fields.append('raw_response')
            existing.save(update_fields=updated_fields)
            return existing, True

    txn = PaymentTransaction.objects.create(
        user=order.user if getattr(order, 'user_id', None) else None,
        order=order,
        provider=provider,
        paypal_order_id=effective_paypal_order_id,
        provider_transaction_id=effective_txn_id,
        amount=resolved_amount if resolved_amount is not None else order.total,
        currency=effective_currency,
        payer_email=str(payer_email or '').strip(),
        status=effective_status,
        success=True,
        raw_response=raw_response,
    )
    return txn, True


def _mark_order_paid_and_finalize(order, provider='unknown', provider_txn_id=''):
    """
    Mark order paid once and apply paid-only side effects:
    - decrement product stock
    - clear paid items from authenticated user's cart
    Returns True only when order transitioned to PAID in this call.
    """
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        if locked_order.status == Order.STATUS_PAID:
            return False
        if locked_order.status in (Order.STATUS_PROCESSING, Order.STATUS_SHIPPED, Order.STATUS_DELIVERED):
            logger.info(
                'payment.finalize skipped order_id=%s reason=non_pending_status status=%s provider=%s txn_id=%s',
                locked_order.id, locked_order.status, provider, provider_txn_id or ''
            )
            return False

        for item in locked_order.items.select_related('product'):
            product = Product.objects.select_for_update().get(pk=item.product_id)
            if product.is_digital:
                continue
            next_stock = int(product.stock) - int(item.quantity)
            if next_stock < 0:
                logger.warning(
                    'payment.finalize low_stock order_id=%s product_id=%s provider=%s txn_id=%s available=%s required=%s',
                    locked_order.id, product.id, provider, provider_txn_id or '', product.stock, item.quantity
                )
                next_stock = 0
            product.stock = next_stock
            product.save(update_fields=['stock'])

        locked_order.status = Order.STATUS_PAID
        locked_order.save(update_fields=['status'])

    removed_items = 0
    if getattr(order, 'user_id', None):
        with transaction.atomic():
            for order_item in order.items.select_related('product'):
                remaining = int(order_item.quantity)
                if remaining <= 0:
                    continue
                user_cart_items = (
                    CartItem.objects
                    .select_for_update()
                    .filter(cart__user=order.user, product_id=order_item.product_id)
                    .order_by('id')
                )
                for cart_item in user_cart_items:
                    if remaining <= 0:
                        break
                    current_qty = int(cart_item.quantity)
                    if current_qty <= remaining:
                        remaining -= current_qty
                        cart_item.delete()
                        removed_items += 1
                    else:
                        cart_item.quantity = current_qty - remaining
                        cart_item.save(update_fields=['quantity'])
                        remaining = 0

    logger.info(
        'payment.finalize order_id=%s provider=%s txn_id=%s cart_items_removed=%s',
        order.id, provider, provider_txn_id or '', removed_items
    )
    return True


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    stripe_mode = (getattr(settings, 'STRIPE_MODE', 'LIVE') or 'LIVE').strip().upper()
    if stripe_mode == 'LIVE' and not webhook_secret:
        logger.error('stripe.webhook misconfigured reason=missing_webhook_secret mode=LIVE')
        return Response({'error': 'stripe_webhook_not_configured'}, status=500)
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret) if webhook_secret else json.loads(payload)
    except Exception:
        logger.exception('Invalid Stripe webhook')
        return Response({'error': 'invalid_signature'}, status=400)

    # Handle relevant event types
    evtype = event.get('type')
    data = event.get('data', {}).get('object', {})
    if evtype == 'payment_intent.succeeded' or evtype == 'checkout.session.completed':
        # Try to get order id from metadata
        order_id = None
        if data.get('metadata'):
            order_id = data['metadata'].get('order_id')
        # fallback: look for client_reference_id or description
        if not order_id:
            order_id = data.get('client_reference_id') or (data.get('description') and ''.join(filter(str.isdigit, data.get('description'))))

        if order_id:
            try:
                order = Order.objects.get(id=int(order_id))
            except Exception:
                order = None

            if order:
                if evtype == 'checkout.session.completed':
                    provider_txn_id = data.get('payment_intent') or data.get('id')
                    amount_cents = data.get('amount_total') or data.get('amount_subtotal') or data.get('amount')
                    payer_email = str(
                        ((data.get('customer_details') or {}).get('email') if isinstance(data.get('customer_details'), dict) else '')
                        or data.get('customer_email')
                        or ''
                    ).strip()
                    currency = str(data.get('currency') or 'USD').upper()
                else:
                    provider_txn_id = data.get('id') or data.get('payment_intent')
                    amount_cents = data.get('amount_received') or data.get('amount')
                    charges = (data.get('charges') or {}).get('data') or []
                    charge0 = charges[0] if charges else {}
                    payer_email = str(
                        data.get('receipt_email')
                        or ((charge0.get('billing_details') or {}).get('email') if isinstance(charge0, dict) else '')
                        or ''
                    ).strip()
                    currency = str(data.get('currency') or 'USD').upper()
                amount = (amount_cents or 0) / 100.0
                if not _amount_matches_order_total(order, amount):
                    logger.warning(
                        'stripe.webhook amount_mismatch order_id=%s txn_id=%s provided=%s expected=%s',
                        order.id, provider_txn_id or '', amount, order.total
                    )
                    _record_payment_attempt(
                        order=order,
                        provider='stripe',
                        provider_txn_id=provider_txn_id or '',
                        amount=_parse_decimal_amount(amount) if amount is not None else order.total,
                        raw_response={'event': 'webhook_amount_mismatch', 'payload': event},
                    )
                    return Response({'ok': True})
                txn, created = _record_transaction(
                    order,
                    'stripe',
                    provider_txn_id,
                    amount,
                    event,
                    status='completed',
                    currency=currency,
                    payer_email=payer_email,
                )
                if created:
                    became_paid = _mark_order_paid_and_finalize(order, provider='stripe', provider_txn_id=provider_txn_id or '')
                    if became_paid:
                        logger.info('stripe.webhook marked_paid order_id=%s txn_id=%s', order.id, provider_txn_id)
                        _send_order_paid_notifications(order, provider='stripe')

    return Response({'ok': True})


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def flutterwave_webhook(request):
    # Verify using verif-hash header.
    # Flutterwave typically sends a static secret hash in header;
    # we also support legacy HMAC style for backward compatibility.
    secret = getattr(settings, 'FLUTTERWAVE_WEBHOOK_SECRET', '')
    flw_mode = (getattr(settings, 'FLUTTERWAVE_MODE', 'LIVE') or 'LIVE').strip().upper()
    if flw_mode == 'LIVE' and not str(secret or '').strip():
        logger.error('flutterwave.webhook misconfigured reason=missing_webhook_secret mode=LIVE')
        return Response({'error': 'flutterwave_webhook_not_configured'}, status=500)
    signature = request.META.get('HTTP_VERIF_HASH')
    payload = request.body
    try:
        if secret:
            sig = (signature or '').strip()
            static_valid = hmac.compare_digest(sig, secret.strip()) if sig else False
            computed = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
            hmac_valid = hmac.compare_digest(sig, computed) if sig else False
            if not (static_valid or hmac_valid):
                logger.warning('Invalid flutterwave signature')
                return Response({'error': 'invalid_signature'}, status=400)
        data = json.loads(payload.decode('utf-8'))
    except Exception:
        return Response({'error': 'invalid_payload'}, status=400)

    # Flutterwave payload shape may include data.tx_ref and data.status
    fw = data.get('data') or {}
    tx_ref = fw.get('tx_ref')
    status_str = str(fw.get('status') or '').strip().lower()
    provider_txn_id = fw.get('id')
    amount = None
    try:
        amount = float(fw.get('amount') or 0)
    except Exception:
        amount = None

    tx_match = re.match(r'^order-(\d+)', str(tx_ref or ''))
    meta_order_id = str((fw.get('meta') or {}).get('order_id') or '').strip()
    resolved_order_id = tx_match.group(1) if tx_match else meta_order_id
    if resolved_order_id and status_str in ('successful', 'completed'):
        try:
            order_id = int(resolved_order_id)
            order = Order.objects.get(id=order_id)
            effective_txn_id = provider_txn_id or tx_ref
            if amount is not None and not _amount_matches_order_total(order, amount):
                logger.warning(
                    'flutterwave.webhook amount_mismatch order_id=%s txn_id=%s provided=%s expected=%s',
                    order.id, effective_txn_id or '', amount, order.total
                )
                _record_payment_attempt(
                    order=order,
                    provider='flutterwave',
                    provider_txn_id=effective_txn_id or '',
                    amount=_parse_decimal_amount(amount),
                    raw_response={'event': 'webhook_amount_mismatch', 'payload': data},
                )
                return Response({'ok': True})

            txn, created = _record_transaction(order, 'flutterwave', effective_txn_id, amount, data)
            if created:
                became_paid = _mark_order_paid_and_finalize(order, provider='flutterwave', provider_txn_id=effective_txn_id or '')
                if became_paid:
                    logger.info('flutterwave.webhook marked_paid order_id=%s txn_id=%s', order.id, effective_txn_id)
                    _send_order_paid_notifications(order, provider='flutterwave')
        except Exception:
            logger.exception('Failed to apply flutterwave webhook')

    return Response({'ok': True})


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def paypal_webhook(request):
    if not _paypal_rate_limit_allow(
        request,
        bucket='paypal_webhook',
        limit=getattr(settings, 'RATE_LIMIT_PAYPAL_WEBHOOK_LIMIT', 180),
        window_seconds=getattr(settings, 'RATE_LIMIT_PAYPAL_WEBHOOK_WINDOW_SECONDS', 60),
    ):
        return Response({'error': 'rate_limited'}, status=429)

    webhook_id = (getattr(settings, 'PAYPAL_WEBHOOK_ID', '') or '').strip()
    if not webhook_id:
        logger.error('paypal.webhook misconfigured reason=missing_webhook_id')
        return Response({'error': 'paypal_webhook_not_configured'}, status=500)

    body_text = request.body.decode('utf-8')
    try:
        event = json.loads(body_text)
    except Exception:
        return Response({'error': 'invalid_payload'}, status=400)

    transmission_id = request.META.get('HTTP_PAYPAL_TRANSMISSION_ID')
    transmission_time = request.META.get('HTTP_PAYPAL_TRANSMISSION_TIME')
    cert_url = request.META.get('HTTP_PAYPAL_CERT_URL')
    transmission_sig = request.META.get('HTTP_PAYPAL_TRANSMISSION_SIG')
    auth_algo = request.META.get('HTTP_PAYPAL_AUTH_ALGO')

    if not all([transmission_id, transmission_time, cert_url, transmission_sig, auth_algo]):
        logger.warning('paypal.webhook missing_signature_headers')
        return Response({'error': 'missing_signature_headers'}, status=400)

    verify_payload = {
        'transmission_id': transmission_id,
        'transmission_time': transmission_time,
        'cert_url': cert_url,
        'auth_algo': auth_algo,
        'transmission_sig': transmission_sig,
        'webhook_id': webhook_id,
        'webhook_event': event,
    }
    try:
        status_code, verify_data, _ = _paypal_api_request(
            'POST',
            '/v1/notifications/verify-webhook-signature',
            payload=verify_payload,
        )
    except Exception:
        logger.exception('paypal.webhook verification_request_failed')
        return Response({'error': 'paypal_unreachable'}, status=502)

    if status_code not in (200, 201) or str(verify_data.get('verification_status') or '').upper() != 'SUCCESS':
        logger.warning('paypal.webhook invalid_signature status=%s verification_status=%s', status_code, verify_data.get('verification_status'))
        return Response({'error': 'invalid_signature'}, status=400)

    event_type = str(event.get('event_type') or '').strip()
    resource = event.get('resource') or {}

    paypal_order_id = ''
    provider_txn_id = ''
    amount_value = None
    currency = 'USD'
    payer_email = ''
    mapped_status = 'pending'

    if event_type.startswith('PAYMENT.CAPTURE.'):
        provider_txn_id = str(resource.get('id') or '').strip()
        amount_obj = resource.get('amount') or {}
        amount_value = amount_obj.get('value')
        currency = str(amount_obj.get('currency_code') or 'USD').upper()
        payer_email = str((resource.get('payer') or {}).get('email_address') or '').strip()
        paypal_order_id = str(((resource.get('supplementary_data') or {}).get('related_ids') or {}).get('order_id') or '').strip()
        mapped_status = {
            'PAYMENT.CAPTURE.COMPLETED': 'completed',
            'PAYMENT.CAPTURE.PENDING': 'pending',
            'PAYMENT.CAPTURE.DENIED': 'failed',
            'PAYMENT.CAPTURE.REFUNDED': 'refunded',
            'PAYMENT.CAPTURE.REVERSED': 'failed',
        }.get(event_type, 'pending')
    elif event_type.startswith('CHECKOUT.ORDER.'):
        paypal_order_id = str(resource.get('id') or '').strip()
        mapped_status = str(resource.get('status') or '').strip().lower() or 'pending'
    else:
        # Ignore unrelated events.
        return Response({'ok': True})

    txn_qs = PaymentTransaction.objects.filter(provider='paypal')
    if paypal_order_id:
        txn_qs = txn_qs.filter(paypal_order_id=paypal_order_id)
    elif provider_txn_id:
        txn_qs = txn_qs.filter(provider_transaction_id=provider_txn_id)

    txn_seed = txn_qs.select_related('order').order_by('-created_at').first()
    if not txn_seed:
        logger.info('paypal.webhook unmatched_event event_type=%s paypal_order_id=%s provider_txn_id=%s', event_type, paypal_order_id, provider_txn_id)
        return Response({'ok': True})

    order = txn_seed.order
    if mapped_status == 'completed':
        if amount_value is not None and not _amount_matches_order_total(order, amount_value):
            logger.warning(
                'paypal.webhook amount_mismatch order_id=%s paypal_order_id=%s txn_id=%s provided=%s expected=%s',
                order.id, paypal_order_id, provider_txn_id, amount_value, order.total
            )
            _record_payment_attempt(
                order=order,
                provider='paypal',
                provider_txn_id=provider_txn_id or paypal_order_id,
                paypal_order_id=paypal_order_id,
                amount=_parse_decimal_amount(amount_value) if amount_value is not None else order.total,
                status='failed',
                currency=currency,
                payer_email=payer_email,
                raw_response={'event': 'webhook_amount_mismatch', 'payload': event},
            )
            return Response({'ok': True})

        txn, created = _record_transaction(
            order=order,
            provider='paypal',
            provider_txn_id=provider_txn_id or paypal_order_id,
            paypal_order_id=paypal_order_id,
            amount=amount_value if amount_value is not None else order.total,
            status='completed',
            currency=currency,
            payer_email=payer_email,
            raw_response={'event': event_type, 'payload': event},
        )
        if created:
            became_paid = _mark_order_paid_and_finalize(order, provider='paypal', provider_txn_id=(provider_txn_id or paypal_order_id))
            if became_paid:
                logger.info('paypal.webhook marked_paid order_id=%s txn_id=%s paypal_order_id=%s', order.id, provider_txn_id, paypal_order_id)
                _send_order_paid_notifications(order, provider='paypal')
        return Response({'ok': True, 'transaction_id': txn.id})

    _record_payment_attempt(
        order=order,
        provider='paypal',
        provider_txn_id=provider_txn_id or paypal_order_id,
        paypal_order_id=paypal_order_id,
        amount=_parse_decimal_amount(amount_value) if amount_value is not None else order.total,
        status=mapped_status,
        currency=currency,
        payer_email=payer_email,
        raw_response={'event': event_type, 'payload': event},
    )
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Lightweight health endpoint for platform probes."""
    return Response({'ok': True})


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def storefront_theme(request):
    """Read/update the global storefront visual theme preset."""
    if request.method == 'GET':
        return Response({
            'theme': _get_storefront_theme_value(),
            'available_themes': [STOREFRONT_THEME_DEFAULT, STOREFRONT_THEME_LUXURY, STOREFRONT_THEME_OBSIDIAN],
        })

    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not user.is_staff:
        return Response({'detail': 'Admin login required.'}, status=403)

    requested_theme = request.data.get('theme')
    applied_theme = _set_storefront_theme_value(requested_theme)
    logger.info(
        'storefront.theme updated_by=%s user_id=%s theme=%s ip=%s',
        getattr(user, 'username', 'unknown'),
        getattr(user, 'id', None),
        applied_theme,
        _get_client_ip(request),
    )
    return Response({'ok': True, 'theme': applied_theme})


@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def auth_status(request):
    """Return basic auth status for the current session."""
    user = request.user
    if user and user.is_authenticated:
        return Response({'is_authenticated': True, 'username': user.get_username()})
    return Response({'is_authenticated': False})


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    throttle_identifier = (str(username or '').strip().lower() or 'unknown')[:120]
    if not _rate_limit_allow(
        request,
        bucket='auth_login',
        limit=getattr(settings, 'RATE_LIMIT_AUTH_LOGIN_LIMIT', 12),
        window_seconds=getattr(settings, 'RATE_LIMIT_AUTH_LOGIN_WINDOW_SECONDS', 300),
        identifier=throttle_identifier,
    ):
        logger.warning('auth.login rate_limited username=%s ip=%s', username or 'missing', _get_client_ip(request))
        return _rate_limit_response('Too many login attempts. Please wait and try again.')

    password = request.data.get('password')
    client_ip = _get_client_ip(request)
    logger.info('auth.login attempt username=%s ip=%s', username or 'missing', client_ip)
    if not username or not password:
        logger.warning('auth.login validation_failed ip=%s reason=missing_credentials username=%s', client_ip, username or 'missing')
        return Response({'error': 'username and password required'}, status=400)

    user = authenticate(request, username=username, password=password)

    # Distinguish inactive-unverified accounts from invalid credentials.
    if user is None:
        existing = User.objects.filter(username=username).first()
        if existing and not existing.is_active and existing.check_password(password):
            logger.warning('auth.login blocked_unverified username=%s user_id=%s ip=%s', username, existing.id, client_ip)
            return Response(
                {'error': 'email_not_verified', 'detail': 'Please verify your email before logging in.'},
                status=403
            )
        logger.warning('auth.login failed_invalid_credentials username=%s ip=%s', username, client_ip)
        return Response({'error': 'invalid_credentials'}, status=401)

    if user is not None:
        login(request, user)
        logger.info('auth.login success user_id=%s username=%s ip=%s', user.id, user.username, client_ip)
        _send_login_security_notification(user, request)
        return Response({'ok': True, 'username': user.get_username()})
    logger.warning('auth.login unexpected_failure username=%s ip=%s', username, client_ip)
    return Response({'error': 'invalid_credentials'}, status=401)


@api_view(['POST'])
def logout_view(request):
    user_id = request.user.id if getattr(request.user, 'is_authenticated', False) else None
    username = request.user.username if getattr(request.user, 'is_authenticated', False) else 'anonymous'
    logger.info('auth.logout user_id=%s username=%s ip=%s', user_id, username, _get_client_ip(request))
    logout(request)
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wishlist_detail(request):
    """Get user's wishlist."""
    from .models import Wishlist
    from .serializers import WishlistSerializer
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    serializer = WishlistSerializer(wishlist)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wishlist_add(request):
    """Add product to wishlist."""
    from .models import Wishlist
    product_id = request.data.get('product_id')
    product = get_object_or_404(Product, id=product_id)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    wishlist.products.add(product)
    from .serializers import WishlistSerializer
    return Response(WishlistSerializer(wishlist).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wishlist_remove(request):
    """Remove product from wishlist."""
    from .models import Wishlist
    product_id = request.data.get('product_id')
    product = get_object_or_404(Product, id=product_id)
    wishlist = get_object_or_404(Wishlist, user=request.user)
    wishlist.products.remove(product)
    from .serializers import WishlistSerializer
    return Response(WishlistSerializer(wishlist).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def wishlist_clear(request):
    """Clear authenticated user's wishlist."""
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    removed_items = wishlist.products.count()
    wishlist.products.clear()
    return Response({'ok': True, 'removed_items': removed_items, 'products': []})


@api_view(['GET'])
@permission_classes([AllowAny])
def order_tracking(request):
    """Track order by order number or ID."""
    order_id = request.query_params.get('order_id')
    order_number = request.query_params.get('order_number')
    
    if order_id:
        order = get_object_or_404(
            Order.objects.select_related('shipping_address', 'billing_address').prefetch_related('items__product__images', 'transactions'),
            id=order_id
        )
    elif order_number:
        # If you have an order number field, use it
        order = get_object_or_404(
            Order.objects.select_related('shipping_address', 'billing_address').prefetch_related('items__product__images', 'transactions'),
            order_number=order_number
        )
    else:
        return Response({'error': 'order_id or order_number required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        _ensure_order_access(request, order)
    except PermissionDenied:
        # Avoid leaking whether an order exists when the requester is unauthorized.
        return Response({'error': 'order_not_found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = OrderSerializer(order, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_orders(request):
    """Get all orders for authenticated user."""
    orders = (
        Order.objects
        .filter(user=request.user)
        .select_related('shipping_address', 'billing_address')
        .prefetch_related('items__product__images', 'transactions')
        .order_by('-created_at')
    )
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def page_detail(request, slug):
    """Get static page by slug (About, Contact, FAQ, etc.)."""
    from .models import Page
    from .serializers import PageSerializer
    page = get_object_or_404(Page, slug=slug)
    serializer = PageSerializer(page)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def pages_list(request):
    """List all pages."""
    from .models import Page
    from .serializers import PageSerializer
    pages = Page.objects.all()
    serializer = PageSerializer(pages, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get authenticated user profile."""
    from .serializers import UserProfileSerializer
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def user_profile_update(request):
    """Update authenticated user profile."""
    from .serializers import UserProfileSerializer
    user = request.user
    serializer = UserProfileSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_addresses(request):
    """Get all saved addresses for user."""
    addresses = Address.objects.filter(user=request.user).order_by('-id')
    serializer = AddressSerializer(addresses, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_address_create(request):
    """Create new address for user."""
    serializer = AddressSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_address_detail(request, address_id):
    """Retrieve, update or delete a saved address for the authenticated user."""
    address = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == 'GET':
        return Response(AddressSerializer(address).data)

    if request.method == 'PUT':
        serializer = AddressSerializer(address, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    address.delete()
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_notifications(request):
    if not UserNotification.objects.filter(user=request.user).exists():
        _create_user_notification(
            request.user,
            title='Welcome to your account',
            message='You are all set. New account, order, and payment updates will appear here.',
            level=UserNotification.LEVEL_INFO,
        )
    rows = UserNotification.objects.filter(user=request.user).order_by('-created_at')[:100]
    unread_count = UserNotification.objects.filter(user=request.user, is_read=False).count()
    logger.info('account.notifications list user_id=%s unread=%s', request.user.id, unread_count)
    return Response({
        'results': UserNotificationSerializer(rows, many=True).data,
        'unread_count': unread_count,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_notification_mark_read(request, notification_id):
    row = get_object_or_404(UserNotification, id=notification_id, user=request.user)
    if not row.is_read:
        row.is_read = True
        row.read_at = timezone.now()
        row.save(update_fields=['is_read', 'read_at', 'updated_at'])
    logger.info('account.notifications mark_read user_id=%s notification_id=%s', request.user.id, row.id)
    return Response({'ok': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_notification_mark_all_read(request):
    now = timezone.now()
    updated = UserNotification.objects.filter(user=request.user, is_read=False).update(is_read=True, read_at=now, updated_at=now)
    logger.info('account.notifications mark_all_read user_id=%s updated=%s', request.user.id, updated)
    return Response({'ok': True, 'updated': updated})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_mailbox(request):
    if not UserMailboxMessage.objects.filter(user=request.user).exists():
        _create_user_mailbox_message(
            request.user,
            subject='Welcome to De-Rukkies Collections',
            body='This is your mailbox. Important account, order, payment, and security messages will be shown here.',
            category=UserMailboxMessage.CATEGORY_ACCOUNT,
        )
    rows = UserMailboxMessage.objects.filter(user=request.user).order_by('-created_at')[:100]
    unread_count = UserMailboxMessage.objects.filter(user=request.user, is_read=False).count()
    logger.info('account.mailbox list user_id=%s unread=%s', request.user.id, unread_count)
    return Response({
        'results': UserMailboxMessageSerializer(rows, many=True).data,
        'unread_count': unread_count,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_mailbox_mark_read(request, message_id):
    row = get_object_or_404(UserMailboxMessage, id=message_id, user=request.user)
    if not row.is_read:
        row.is_read = True
        row.read_at = timezone.now()
        row.save(update_fields=['is_read', 'read_at', 'updated_at'])
    logger.info('account.mailbox mark_read user_id=%s message_id=%s', request.user.id, row.id)
    return Response({'ok': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_mailbox_mark_all_read(request):
    now = timezone.now()
    updated = UserMailboxMessage.objects.filter(user=request.user, is_read=False).update(is_read=True, read_at=now, updated_at=now)
    logger.info('account.mailbox mark_all_read user_id=%s updated=%s', request.user.id, updated)
    return Response({'ok': True, 'updated': updated})
