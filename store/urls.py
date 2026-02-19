from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet,
    cart_detail,
    cart_add,
    cart_update,
    cart_remove,
    cart_clear,
    checkout_create,
    stripe_create_payment_intent,
    stripe_confirm_checkout_session,
    flutterwave_confirm_payment,
    paypal_confirm_payment,
    paypal_client_config,
    paypal_create_order,
    paypal_capture_order,
    payment_verify_mark_paid,
    get_shipping_methods,
    auth_status,
    login_view,
    logout_view,
    wishlist_detail,
    wishlist_add,
    wishlist_remove,
    wishlist_clear,
    home_content,
    order_tracking,
    user_orders,
    page_detail,
    pages_list,
    user_profile,
    user_profile_update,
    user_addresses,
    user_address_create,
    user_address_detail,
    user_notifications,
    user_notification_mark_read,
    user_notification_mark_all_read,
    user_mailbox,
    user_mailbox_mark_read,
    user_mailbox_mark_all_read,
    product_by_slug,
    flutterwave_create_payment,
    paypal_create_payment,
    register_view,
    stripe_webhook,
    flutterwave_webhook,
    paypal_webhook,
    chat_assistant,
    assistant_chat,
    verify_email_view,
    contact_submit,
    newsletter_subscribe,
    product_reviews,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
# Register categories to expose GET /api/categories/
from .views import CategoryViewSet
router.register(r'categories', CategoryViewSet, basename='category')

urlpatterns = [
    path('', include(router.urls)),
    # Auth endpoints for session-based auth checks
    path('auth/status/', auth_status, name='auth-status'),
    path('auth/login/', login_view, name='auth-login'),
    path('auth/logout/', logout_view, name='auth-logout'),
    # Cart endpoints
    path('cart/', cart_detail, name='cart-detail'),
    path('cart/add/', cart_add, name='cart-add'),
    path('cart/update/', cart_update, name='cart-update'),
    path('cart/remove/', cart_remove, name='cart-remove'),
    path('cart/clear/', cart_clear, name='cart-clear'),
    # Wishlist endpoints
    path('wishlist/', wishlist_detail, name='wishlist-detail'),
    path('wishlist/add/', wishlist_add, name='wishlist-add'),
    path('wishlist/remove/', wishlist_remove, name='wishlist-remove'),
    path('wishlist/clear/', wishlist_clear, name='wishlist-clear'),
    path('home/content/', home_content, name='home-content'),
    # Checkout & Payment endpoints
    path('checkout/', checkout_create, name='checkout-create'),
    path('payments/stripe/create/', stripe_create_payment_intent, name='stripe-create'),
    path('payments/stripe/confirm/', stripe_confirm_checkout_session, name='stripe-confirm'),
    path('payments/flutterwave/create/', flutterwave_create_payment, name='flutterwave-create'),
    path('payments/flutterwave/confirm/', flutterwave_confirm_payment, name='flutterwave-confirm'),
    path('payments/paypal/create/', paypal_create_payment, name='paypal-create'),
    path('payments/paypal/confirm/', paypal_confirm_payment, name='paypal-confirm'),
    # PayPal Checkout (JS SDK / Smart Buttons)
    path('paypal/config/', paypal_client_config, name='paypal-config'),
    path('paypal/create-order/', paypal_create_order, name='paypal-create-order'),
    path('paypal/capture-order/', paypal_capture_order, name='paypal-capture-order'),
    path('payments/verify/', payment_verify_mark_paid, name='payment-verify'),
    # Webhook endpoints (configure these URLs in provider dashboards)
    path('payments/webhook/stripe/', stripe_webhook, name='stripe-webhook'),
    path('payments/webhook/flutterwave/', flutterwave_webhook, name='flutterwave-webhook'),
    path('payments/webhook/paypal/', paypal_webhook, name='paypal-webhook'),
    path('paypal/webhook/', paypal_webhook, name='paypal-webhook-v2'),
    # Auth register
    path('auth/register/', register_view, name='auth-register'),
    path('auth/verify-email/<str:uidb64>/<str:token>/', verify_email_view, name='auth-verify-email'),
    # Order endpoints
    path('orders/track/', order_tracking, name='order-track'),
    path('orders/', user_orders, name='user-orders'),
    # Shipping
    path('shipping/methods/', get_shipping_methods, name='shipping-methods'),
    # Contact and newsletter
    path('contact/', contact_submit, name='contact-submit'),
    path('newsletter/subscribe/', newsletter_subscribe, name='newsletter-subscribe'),
    # Chat assistant
    path('chat/', chat_assistant, name='chat-assistant'),
    path('assistant/chat/', assistant_chat, name='assistant-chat'),
    # Product by slug helper
    path('products/slug/<slug:slug>/', product_by_slug, name='product-by-slug'),
    path('products/slug/<slug:slug>/reviews/', product_reviews, name='product-reviews'),
    # Pages (static content: About, Contact, FAQ, etc.)
    path('pages/', pages_list, name='pages-list'),
    path('pages/<slug:slug>/', page_detail, name='page-detail'),
    # User Account endpoints
    path('account/profile/', user_profile, name='user-profile'),
    path('account/profile/update/', user_profile_update, name='user-profile-update'),
    path('account/addresses/', user_addresses, name='user-addresses'),
    path('account/addresses/create/', user_address_create, name='user-address-create'),
    path('account/addresses/<int:address_id>/', user_address_detail, name='user-address-detail'),
    path('account/notifications/', user_notifications, name='user-notifications'),
    path('account/notifications/<int:notification_id>/read/', user_notification_mark_read, name='user-notification-mark-read'),
    path('account/notifications/mark-all-read/', user_notification_mark_all_read, name='user-notification-mark-all-read'),
    path('account/mailbox/', user_mailbox, name='user-mailbox'),
    path('account/mailbox/<int:message_id>/read/', user_mailbox_mark_read, name='user-mailbox-mark-read'),
    path('account/mailbox/mark-all-read/', user_mailbox_mark_all_read, name='user-mailbox-mark-all-read'),
]
