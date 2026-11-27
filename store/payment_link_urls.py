from django.urls import path

from . import payment_link_views as views


urlpatterns = [
    path('public/detail/', views.public_detail, name='payment-link-detail'),
    path('public/start/', views.public_start, name='payment-link-start'),
    path('admin/config/', views.staff_config, name='payment-link-admin-config'),
    path('admin/create/', views.staff_create, name='payment-link-admin-create'),
    path('admin/<uuid:reference>/', views.staff_detail, name='payment-link-admin-detail'),
    path('admin/<uuid:reference>/revoke/', views.staff_revoke, name='payment-link-admin-revoke'),
    path('admin/<uuid:reference>/send/', views.staff_send, name='payment-link-admin-send'),
    path('webhook/stripe/', views.stripe_webhook, name='payment-link-stripe-webhook'),
    path('webhook/flutterwave/', views.flutterwave_webhook, name='payment-link-flutterwave-webhook'),
]
