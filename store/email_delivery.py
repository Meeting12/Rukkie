"""Compose mail with images that travel with the HTML body."""
import re
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from functools import lru_cache
from io import BytesIO
from time import monotonic
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.mail import EmailMultiAlternatives
from PIL import Image, ImageDraw, ImageOps


LOGO_CONTENT_ID = 'rukkies-logo@rukkies.com'
WELCOME_BANNER_CONTENT_ID = 'welcome-banner@rukkies.com'
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_PIXELS = 12_000_000


@lru_cache(maxsize=1)
def _logo_png():
    # Render the package mark from the existing email header as a raster image.
    icon = Image.new('RGBA', (96, 96))
    draw = ImageDraw.Draw(icon)
    gold = '#F2DDAB'
    draw.line([(48, 9), (84, 29), (84, 67), (48, 87), (12, 67), (12, 29), (48, 9)],
              fill=gold, width=7, joint='curve')
    draw.line([(12, 29), (48, 49), (84, 29)], fill=gold, width=7, joint='curve')
    draw.line([(48, 49), (48, 87)], fill=gold, width=7)
    draw.line([(31, 19), (67, 39)], fill=gold, width=7)
    output = BytesIO()
    icon.save(output, 'PNG')
    return output.getvalue()


@lru_cache(maxsize=1)
def _welcome_banner():
    return (settings.BASE_DIR / 'frontend' / 'src' / 'assets' / 'hero-banner.jpg').read_bytes()


class StoreEmail(EmailMultiAlternatives):
    def __init__(self, subject, body, from_email, to, *, html=None, inline_images=None):
        super().__init__(subject, body, from_email, to)
        self.inline_images = {}
        if html:
            self.attach_alternative(html, 'text/html')
            self.inline_images.update(
                (key, image) for key, image in (inline_images or {}).items() if f'cid:{key}' in html
            )
            if f'cid:{LOGO_CONTENT_ID}' in html:
                self.inline_images[LOGO_CONTENT_ID] = ('png', _logo_png())
            if f'cid:{WELCOME_BANNER_CONTENT_ID}' in html:
                self.inline_images[WELCOME_BANNER_CONTENT_ID] = ('jpeg', _welcome_banner())

    def _create_alternatives(self, message):
        message = super()._create_alternatives(message)
        if not self.inline_images or not self.alternatives:
            return message

        # Keep plain text and HTML as alternatives, with images related to HTML only.
        alternatives = message.get_payload()
        related = MIMEMultipart('related', type='text/html')
        related.attach(alternatives[-1])
        for content_id, (subtype, data) in self.inline_images.items():
            image = MIMEImage(data, _subtype=subtype)
            image.add_header('Content-ID', f'<{content_id}>')
            image.add_header('Content-Disposition', 'inline')
            related.attach(image)
        alternatives[-1] = related
        return message


def _cloudinary_image_urls(url):
    source = urlsplit(url)
    cloud, marker, path = source.path.partition('/image/upload/')
    if source.scheme != 'https' or source.netloc != 'res.cloudinary.com' or not marker or not path:
        return
    prefix = f'https://res.cloudinary.com{cloud}{marker}c_fill,w_160,h_160,f_jpg/'
    yield prefix + path
    # Some legacy uploads are stored with a media/ namespace, others without it.
    public_id = re.sub(r'^v\d+/', '', path)
    if public_id.startswith('media/products/'):
        yield prefix + public_id.removeprefix('media/')
    elif public_id.startswith('products/'):
        yield prefix + 'v1/media/' + public_id


def _download_image(url, deadline):
    time_left = deadline - monotonic()
    if time_left <= 0:
        return b''
    try:
        with requests.get(url, stream=True, allow_redirects=False,
                          timeout=(min(0.5, time_left), min(0.6, time_left))) as response:
            if response.status_code != 200 or not response.headers.get('Content-Type', '').startswith('image/'):
                return b''
            data = bytearray()
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data) > MAX_IMAGE_BYTES or monotonic() >= deadline:
                    return b''
            return bytes(data)
    except requests.RequestException:
        return b''


def _jpeg_thumbnail(data):
    if not data or len(data) > MAX_IMAGE_BYTES:
        return b''
    try:
        with Image.open(BytesIO(data)) as original:
            if original.width * original.height > MAX_IMAGE_PIXELS:
                return b''
            image = ImageOps.fit(ImageOps.exif_transpose(original).convert('RGB'), (160, 160))
            output = BytesIO()
            image.save(output, 'JPEG', quality=82)
            return output.getvalue()
    except (OSError, ValueError, Image.DecompressionBombError):
        return b''


def product_email_thumbnail(field, url, deadline):
    if isinstance(field.storage, FileSystemStorage) and field.name.startswith('products/'):
        try:
            with field.storage.open(field.name, 'rb') as image:
                thumbnail = _jpeg_thumbnail(image.read(MAX_IMAGE_BYTES + 1))
                if thumbnail:
                    return thumbnail
        except OSError:
            pass

    # Only fetch the known public CDN. Keep other hosts as display URLs in the HTML.
    for candidate in _cloudinary_image_urls(url):
        thumbnail = _jpeg_thumbnail(_download_image(candidate, deadline))
        if thumbnail:
            return thumbnail
    return b''
