from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from .models import PaymentLink
from .payment_link_gateways import available_gateways
from .payment_link_serializers import PaymentLinkCreateSerializer
from .payment_links import audit, can_send_invitation, create_payment_link, payment_url, rate_limit, with_display_status


class PaymentLinkAdminForm(forms.Form):
    customer_name = forms.CharField(label='Customer full name', max_length=160)
    customer_email = forms.EmailField(max_length=254)
    amount = forms.DecimalField(label='Payment amount', max_digits=10, decimal_places=2, min_value=1)
    gateway = forms.ChoiceField(label='Payment gateway')
    currency = forms.ChoiceField()
    description = forms.CharField(label='Payment description', max_length=240, widget=forms.Textarea(attrs={'rows': 3}))
    expires_at = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    order_reference = forms.CharField(max_length=64, required=False)
    send_email = forms.BooleanField(label='Send payment link via email', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gateways = available_gateways()
        self.fields['gateway'].choices = [
            (gateway, PaymentLink.Gateway(gateway).label) for gateway in self.gateways
        ]
        currencies = dict.fromkeys(currency for supported in self.gateways.values() for currency in supported)
        self.fields['currency'].choices = [(currency, currency) for currency in currencies]
        self.fields['expires_at'].label = f'Expires at ({timezone.get_current_timezone_name()})'

    def clean(self):
        values = super().clean()
        if self.errors:
            return values
        serializer = PaymentLinkCreateSerializer(data=values)
        if serializer.is_valid():
            return serializer.validated_data
        for field, errors in serializer.errors.items():
            for error in errors:
                self.add_error(field if field in self.fields else None, str(error))
        return self.cleaned_data


class PaymentLinkStatusFilter(admin.SimpleListFilter):
    title = 'payment status'
    parameter_name = 'payment_status'

    def lookups(self, request, model_admin):
        return PaymentLink.Status.choices

    def queryset(self, request, queryset):
        if self.value() in PaymentLink.Status.values:
            return queryset.filter(display_status=self.value())
        return queryset


@admin.register(PaymentLink)
class PaymentLinkAdmin(admin.ModelAdmin):
    change_list_template = 'admin/store/paymentlink/change_list.html'
    list_display = (
        'reference', 'customer_name', 'customer_email', 'amount', 'currency', 'gateway',
        'created_at', 'expires_at', 'payment_status', 'created_by',
    )
    list_display_links = ('reference',)
    list_filter = (PaymentLinkStatusFilter, 'gateway', 'currency', 'created_at')
    search_fields = ('reference', 'customer_name', 'customer_email', 'order_reference', 'created_by__username')
    list_per_page = 25
    actions = None

    def get_queryset(self, request):
        return with_display_status(super().get_queryset(request).select_related('created_by'))

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(ordering='display_status', description='Payment status')
    def payment_status(self, link):
        return format_html('<span class="payment-links-badge" data-status="{}">{}</span>',
                           link.display_status, PaymentLink.Status(link.display_status).label)

    def get_list_display(self, request):
        can_manage = request.user.has_perm('store.change_paymentlink')

        @admin.display(description='Actions')
        def actions_column(link):
            detail = reverse('admin:store_paymentlink_details', args=[link.pk])
            links = [format_html('<a href="{}">Transaction details</a>', detail)]
            try:
                url = payment_url(link)
            except ValueError:
                url = ''
            if url:
                links.extend([
                    format_html('<button type="button" data-payment-link-action="copy" data-url="{}">Copy link</button>', url),
                    format_html('<a href="{}?preview=1" target="_blank" rel="noopener noreferrer">Preview</a>', url),
                ])
            if can_manage and can_send_invitation(link):
                links.append(format_html(
                    '<button type="button" data-payment-link-action="send" data-reference="{}">Send or resend</button>', link.reference,
                ))
            if can_manage and link.display_status in ('pending', 'failed'):
                links.append(format_html(
                    '<button type="button" data-payment-link-action="revoke" data-reference="{}">Revoke</button>', link.reference,
                ))
            if link.status == 'paid':
                links.append(format_html('<a href="{}">Download receipt</a>', reverse('admin:store_paymentlink_receipt', args=[link.pk])))
            return format_html('<div class="payment-links-row-actions">{}</div>', format_html_join('', '{}', ((item,) for item in links)))

        return (*self.list_display, actions_column)

    def changelist_view(self, request, extra_context=None):
        queryset = self.get_queryset(request)
        counts = queryset.aggregate(
            total=Count('pk'), pending=Count('pk', filter=Q(display_status='pending')),
            paid=Count('pk', filter=Q(display_status='paid')), expired=Count('pk', filter=Q(display_status='expired')),
        )
        revenue = queryset.filter(status='paid').order_by().values('currency').annotate(total=Sum('amount')).order_by('currency')
        context = {
            **(extra_context or {}),
            'payment_link_counts': counts,
            'payment_link_revenue': revenue,
            'can_generate_payment_link': self.has_add_permission(request),
        }
        return super().changelist_view(request, extra_context=context)

    def add_view(self, request, form_url='', extra_context=None):
        if not self.has_add_permission(request):
            raise PermissionDenied
        context = {
            **self.admin_site.each_context(request),
            **(extra_context or {}),
            'title': 'Generate Payment Link',
            'can_view_links': self.has_view_permission(request),
        }
        template = 'admin/store/paymentlink/generate.html'
        if not request.is_secure():
            return TemplateResponse(
                request, template, {**context, 'requires_https': True},
                status=200 if request.method in ('GET', 'HEAD') else 403,
            )

        submitting = request.method == 'POST'
        form = PaymentLinkAdminForm(request.POST if submitting else None)
        context['form'] = form
        status = 200
        if submitting and not rate_limit('staff_create', request.user.pk, 15):
            form.add_error(None, 'Too many requests. Try again shortly.')
            status = 429
        elif submitting and form.is_valid():
            try:
                link, url = create_payment_link(actor=request.user, **form.cleaned_data)
            except ValueError:
                form.add_error(None, 'The payment link URL is not configured.')
                status = 503
            else:
                self.log_addition(request, link, 'Generated payment link.')
                context.update(payment_url=url, email_queued=form.cleaned_data['send_email'])
        return TemplateResponse(request, template, context, status=status)

    def get_urls(self):
        return [
            path('<int:object_id>/receipt/', self.admin_site.admin_view(self.receipt), name='store_paymentlink_receipt'),
            path('<int:object_id>/details/', self.admin_site.admin_view(self.details), name='store_paymentlink_details'),
            *super().get_urls(),
        ]

    def _link(self, request, object_id):
        if not request.is_secure() or not request.user.has_perm('store.view_paymentlink'):
            raise Http404
        try:
            pk = int(object_id)
        except (TypeError, ValueError):
            raise Http404 from None
        return get_object_or_404(self.get_queryset(request), pk=pk)

    def details(self, request, object_id):
        link = self._link(request, object_id)
        try:
            url = payment_url(link)
        except ValueError:
            url = ''
        can_manage = request.user.has_perm('store.change_paymentlink')
        return TemplateResponse(request, 'admin/store/paymentlink/details.html', {
            **self.admin_site.each_context(request),
            'title': 'Payment link details', 'link': link, 'url': url,
            'attempts': link.attempts.order_by('-created_at'), 'transactions': link.transactions.order_by('-created_at'),
            'audit_entries': link.audit.select_related('actor'),
            'receipt_url': reverse('admin:store_paymentlink_receipt', args=[link.pk]) if link.status == 'paid' else '',
            'can_send': can_manage and can_send_invitation(link),
            'can_revoke': can_manage and link.display_status in ('pending', 'failed'),
        })

    def receipt(self, request, object_id):
        link = self._link(request, object_id)
        if request.method != 'GET' or link.status != PaymentLink.Status.PAID:
            raise Http404
        audit(link, 'receipt_downloaded', request.user)
        response = TemplateResponse(request, 'payment_link_receipt.html', {'link': link})
        response['Content-Disposition'] = f'attachment; filename="rukkies-receipt-{link.reference.hex}.html"'
        return response

    def change_view(self, request, object_id, form_url='', extra_context=None):
        return self.details(request, object_id)
