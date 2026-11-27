from io import BytesIO
from time import monotonic
from unittest.mock import Mock, patch

from django.core import mail
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image

from .email_delivery import LOGO_CONTENT_ID, WELCOME_BANNER_CONTENT_ID, StoreEmail, product_email_thumbnail
from .email_react import _render_builtin_email_html
from .models import Order, OrderItem, Product, ProductImage
from .views import _send_order_created_notifications


def sample_photo():
    data = BytesIO()
    Image.new('RGB', (320, 180), 'blue').save(data, 'PNG')
    return data.getvalue()


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CONTACT_RECIPIENT_EMAIL='operations@example.test',
    STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}},
)
class OrderEmailImagesTests(TestCase):
    def test_order_email_embeds_the_product_image_and_brand_mark(self):
        product = Product.objects.create(name='Sample Bag', price='25.00')
        photo = ProductImage.objects.create(product=product, image='products/bag.png')
        order = Order.objects.create(total='25.00')
        OrderItem.objects.create(order=order, product=product, price='25.00')
        with (
            patch('store.views.render_react_email_html', side_effect=_render_builtin_email_html),
            patch('store.email_delivery.FileSystemStorage.open', return_value=BytesIO(sample_photo())),
        ):
            _send_order_created_notifications(order, contact_email='buyer@example.test')

        customer_email = mail.outbox[0].message()
        plain, related = customer_email.get_payload()
        self.assertEqual(plain.get_content_type(), 'text/plain')
        self.assertEqual(related.get_content_type(), 'multipart/related')
        body, *images = related.get_payload()
        html = body.get_payload(decode=True).decode()
        product_id = f'product-{photo.pk}@rukkies.com'
        self.assertIn(f'src="cid:{product_id}"', html)
        self.assertIn(f'src="cid:{LOGO_CONTENT_ID}"', html)
        self.assertEqual({part['Content-ID'] for part in images}, {f'<{product_id}>', f'<{LOGO_CONTENT_ID}>'})
        self.assertTrue(all(part.get_content_disposition() == 'inline' for part in images))
        with Image.open(BytesIO(images[0].get_payload(decode=True))) as thumbnail:
            self.assertEqual(thumbnail.format, 'JPEG')
            self.assertEqual(thumbnail.size, (160, 160))


class SharedEmailImagesTests(SimpleTestCase):
    def test_welcome_banner_and_brand_are_packaged_with_html(self):
        html = _render_builtin_email_html('WelcomeEmail', {'userName': 'Customer'})
        message = StoreEmail('Welcome', 'Welcome', 'store@example.test', ['buyer@example.test'], html=html)
        related = message.message().get_payload(1)
        self.assertEqual(related.get_content_type(), 'multipart/related')
        for content_id in (LOGO_CONTENT_ID, WELCOME_BANNER_CONTENT_ID):
            self.assertIn(f'src="cid:{content_id}"', html)
            self.assertTrue(any(part['Content-ID'] == f'<{content_id}>' for part in related.walk()))

    @patch('store.email_delivery.requests.get')
    def test_cloudinary_thumbnail_recovers_legacy_media_paths(self, get):
        missing = Mock(status_code=404)
        success = Mock(status_code=200, headers={'Content-Type': 'image/png'})
        success.iter_content.return_value = [sample_photo()]
        get.return_value.__enter__.side_effect = [missing, success]

        field = Mock(storage=object())
        source = 'https://res.cloudinary.com/example/image/upload/v1/products/bag.png'
        self.assertTrue(product_email_thumbnail(field, source, monotonic() + 2))
        self.assertIn('/v1/media/products/bag.png', get.call_args.args[0])
        self.assertFalse(get.call_args.kwargs['allow_redirects'])

    @patch('store.email_delivery.requests.get')
    def test_external_image_url_does_not_trigger_a_server_request(self, get):
        field = Mock(storage=object())
        self.assertFalse(product_email_thumbnail(field, 'https://other.example.test/photo.jpg', monotonic() + 2))
        get.assert_not_called()
