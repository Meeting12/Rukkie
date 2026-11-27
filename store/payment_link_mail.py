from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

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
    description = f'{link.description}\n{link.currency} {link.amount}\nReference: {link.reference}'
    text = f'{intro}\n\n{description}'
    if url:
        text += f'\n\nPay securely: {url}\nExpires: {link.expires_at:%Y-%m-%d %H:%M %Z}'
    message = EmailMultiAlternatives(
        title, text, settings.DEFAULT_FROM_EMAIL, [notice.recipient],
    )
    message.attach_alternative(render_to_string('payment_link_email.html', {
        'title': title, 'intro': intro, 'kind': notice.kind, 'link': link, 'url': url,
        'support': settings.CONTACT_RECIPIENT_EMAIL,
    }), 'text/html')
    if notice.kind == 'receipt':
        receipt = render_to_string('payment_link_receipt.html', {'link': link})
        message.attach(f'rukkies-receipt-{link.reference.hex}.html', receipt, 'text/html')
    return message.send(fail_silently=False)
