from django.conf import settings
from django.template.loader import render_to_string

from .email_delivery import StoreEmail
from .email_react import render_payment_link_email_html
from .payment_links import payment_url


COPY = {
    'invitation': ('Your Rukkies payment link', 'Use your secure link to make this payment.'),
    'confirmation': ('Rukkies payment confirmed', 'We received and verified your payment. Thank you.'),
    'receipt': ('Your Rukkies payment receipt', 'Your receipt is attached for your records.'),
    'admin_payment': ('Rukkies payment link paid', 'A hosted checkout payment was verified. Review it in the admin dashboard.'),
}


def send_payment_link_notice(notice):
    link = notice.link
    title, intro = COPY[notice.kind]
    url = payment_url(link) if notice.kind == 'invitation' else ''
    is_admin_notice = notice.kind == 'admin_payment'
    greeting = '' if is_admin_notice else f'Hello {link.customer_name},'
    support = settings.CONTACT_RECIPIENT_EMAIL
    details = [
        ('Amount due' if url else 'Amount paid', f'{link.currency} {link.amount}'),
        ('Description', link.description),
        ('Payment reference', str(link.reference)),
        ('Order reference', link.order_reference),
        ('Customer', link.customer_name if is_admin_notice else ''),
    ]
    if url:
        details.append(('Expires', f'{link.expires_at:%Y-%m-%d %H:%M %Z}'))

    detail_text = '\n'.join(f'{label}: {value}' for label, value in details if value)
    sections = [greeting, intro, detail_text]
    if url:
        sections.append(f'Pay securely: {url}')
    if support:
        sections.append(f'Support: {support}')
    text = '\n\n'.join(section for section in sections if section)

    html = render_payment_link_email_html(
        title=title, greeting=greeting, intro=intro, details=details, url=url, support_email=support,
    )
    message = StoreEmail(title, text, settings.DEFAULT_FROM_EMAIL, [notice.recipient], html=html)
    if notice.kind == 'receipt':
        receipt = render_to_string('payment_link_receipt.html', {'link': link})
        message.attach(f'rukkies-receipt-{link.reference.hex}.html', receipt, 'text/html')
    return message.send(fail_silently=False)
