from django.contrib import admin
import csv
import io
import mimetypes
import os
import re
import tempfile
import zipfile
import time
from urllib.parse import urlparse, unquote
import base64
from django.http import HttpResponse
from datetime import datetime
from django.core.mail import send_mail
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.cache import cache
from django.conf import settings
from django import forms
from django.urls import path, reverse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.contrib import messages
from django.utils.html import format_html, format_html_join
from django.utils.text import slugify
from django.db.models import Count, Q
import logging
import requests
import uuid
from .models import (
	Category, Product, ProductImage, Cart, CartItem,
	HomeHeroSlide, PendingMetadata, ShippingMethod, Address, Order, OrderItem, PaymentTransaction, ProductReview,
	Wishlist, Page, ContactMessage, NewsletterSubscription, AssistantPolicy, UserNotification, UserMailboxMessage
)
from .media_layout import normalize_slug, ensure_category_media_structure, category_media_paths
from .tasks import analyze_and_apply_image
from .email_react import get_public_site_url, render_react_email_html

logger = logging.getLogger(__name__)
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.svg', '.avif'}


def _extract_csv_image_sources(row):
	"""Read image source values from common CSV column names."""
	sources = []
	for raw_key, raw_val in (row or {}).items():
		key = str(raw_key or '').strip().lower().replace(' ', '_')
		if not key:
			continue
		if key in {'image', 'images', 'image_url', 'image_urls', 'image_link', 'image_links'} or key.startswith('image'):
			for part in re.split(r'[\n\r,;|]+', str(raw_val or '')):
				value = part.strip()
				if value:
					sources.append(value)
	# de-duplicate while preserving order
	return list(dict.fromkeys(sources))


def _normalize_media_image_path(value):
	"""Normalize media path references from CSV to a storage-relative path."""
	cleaned = str(value or '').strip().replace('\\', '/')
	if not cleaned:
		return ''
	if cleaned.startswith('/media/'):
		cleaned = cleaned[len('/media/'):]
	elif cleaned.startswith('media/'):
		cleaned = cleaned[len('media/'):]
	elif cleaned.startswith('/'):
		cleaned = cleaned[1:]
	return cleaned


def _storage_is_cloudinary():
	try:
		backend = default_storage.__class__.__module__ + '.' + default_storage.__class__.__name__
	except Exception:
		backend = ''
	return 'cloudinary_storage' in (backend or '').lower() or bool(getattr(settings, 'USE_CLOUDINARY_MEDIA', False))


def _storage_exists_safe(name: str) -> bool:
	"""
	Cloudinary storage's exists() may do a HEAD without a timeout and can hang Gunicorn workers.
	So we NEVER call exists() on Cloudinary.
	"""
	if not name:
		return False
	if _storage_is_cloudinary():
		return False
	try:
		return bool(default_storage.exists(name))
	except Exception:
		return False


def _resolve_existing_image_path(value):
	"""
	Resolve a CSV path to an existing media file path.

	IMPORTANT:
	- On Cloudinary storage, calling default_storage.exists() can hang (requests.head without timeout),
	  causing Gunicorn WORKER TIMEOUT. So we skip remote existence checks entirely.
	- Instead, we only normalize paths here. Real uploads happen via URL download / ZIP / local file bytes.
	"""
	normalized = _normalize_media_image_path(value)
	if not normalized:
		return ''

	# If you're on Cloudinary, don't call exists() here (prevents WORKER TIMEOUT).
	# Just return normalized/candidate; later logic decides whether to attach or upload.
	if _storage_is_cloudinary():
		filename = os.path.basename(normalized)
		if filename and not normalized.startswith('products/'):
			return f'products/{filename}'
		return normalized

	# Local or safe storage: check existence
	if _storage_exists_safe(normalized):
		return normalized

	# Support bare filenames like "chair.jpg" by checking products/ folder.
	filename = os.path.basename(normalized)
	if filename:
		candidate = f'products/{filename}'
		if _storage_exists_safe(candidate):
			return candidate
	return ''


def _normalize_path_token(value):
	token = unquote(str(value or '').strip()).replace('\\', '/')
	token = re.sub(r'^[./]+', '', token)
	return token


def _build_archive_index(archive_root):
	"""Build a lookup index for extracted archive files."""
	if not archive_root:
		return None
	by_rel = {}
	by_base = {}
	for root, _, files in os.walk(archive_root):
		for name in files:
			abs_path = os.path.join(root, name)
			rel = os.path.relpath(abs_path, archive_root).replace('\\', '/')
			rel_key = _normalize_path_token(rel).lower()
			if rel_key:
				by_rel[rel_key] = abs_path
			base_key = name.lower()
			by_base.setdefault(base_key, []).append(abs_path)
	return {'by_rel': by_rel, 'by_base': by_base}


def _resolve_archive_file(source, archive_index):
	if not archive_index:
		return ''
	token = _normalize_path_token(source).lower()
	if not token:
		return ''
	by_rel = archive_index.get('by_rel', {})
	by_base = archive_index.get('by_base', {})
	if token in by_rel:
		return by_rel[token]
	base = os.path.basename(token)
	matches = by_base.get(base, [])
	if len(matches) == 1:
		return matches[0]
	if len(matches) > 1:
		# Prefer shortest path when there are duplicates.
		return sorted(matches, key=len)[0]
	return ''


def _resolve_local_filesystem_path(source, category_slugs=None):
	"""Resolve a direct filesystem path (absolute or project-relative)."""
	token = _normalize_path_token(source)
	if not token:
		return ''
	candidates = []
	# Absolute paths like C:\path\file.jpg or /var/... (if running on linux)
	if os.path.isabs(str(source or '').strip()) and os.path.isfile(str(source).strip()):
		return str(source).strip()
	# Try against project root and media root.
	base_dir = str(getattr(settings, 'BASE_DIR', ''))
	media_root = str(getattr(settings, 'MEDIA_ROOT', ''))
	if base_dir:
		candidates.append(os.path.join(base_dir, token))
	if media_root:
		candidates.append(os.path.join(media_root, token))
		candidates.append(os.path.join(media_root, 'products', os.path.basename(token)))
		candidates.append(os.path.join(media_root, 'products', '_shared', os.path.basename(token)))

		for slug in (category_slugs or []):
			try:
				paths = category_media_paths(slug)
			except Exception:
				continue
			for key in ('product_root', 'raw', 'processed', 'archive'):
				root = str(paths.get(key) or '')
				if not root:
					continue
				candidates.append(os.path.join(root, token))
				candidates.append(os.path.join(root, os.path.basename(token)))

	for candidate in candidates:
		if candidate and os.path.isfile(candidate):
			return candidate
	return ''


def _guess_image_extension(source_url, content_type):
	ext = os.path.splitext(urlparse(source_url).path)[1].lower()
	if ext in IMAGE_EXTENSIONS:
		return ext
	guessed = mimetypes.guess_extension((content_type or '').split(';')[0].strip().lower() or '')
	if guessed and guessed.lower() in IMAGE_EXTENSIONS:
		return guessed.lower()
	return '.jpg'


def _summarize_exception(exc, max_len=140):
	text = f'{exc.__class__.__name__}: {exc}'
	text = re.sub(r'\s+', ' ', str(text)).strip()
	return text[:max_len]


def _build_product_image_filename(product, ext='.jpg'):
	"""
	Build a filename that always fits ProductImage.image max_length (DB-safe).
	The DB column stores the full relative path (including upload_to prefix).
	"""
	ext = (ext or '').lower()
	if ext not in IMAGE_EXTENSIONS:
		ext = '.jpg'

	field = ProductImage._meta.get_field('image')
	max_len = int(getattr(field, 'max_length', 100) or 100)
	upload_to = getattr(field, 'upload_to', '') or ''
	if isinstance(upload_to, str):
		upload_prefix = upload_to.strip()
		if upload_prefix and not upload_prefix.endswith('/'):
			upload_prefix = f'{upload_prefix}/'
	else:
		upload_prefix = ''

	# <upload_prefix><base>-<10hex><ext>
	reserved = len(upload_prefix) + 1 + 10 + len(ext)
	max_base_len = max(8, max_len - reserved)
	# Keep Cloudinary public IDs comfortably short regardless of DB max_length.
	max_base_len = min(max_base_len, 72)
	base = slugify(product.slug or product.name) or 'product'
	if len(base) > max_base_len:
		base = base[:max_base_len].rstrip('-_')
	if not base:
		base = 'product'
	return f'{base}-{uuid.uuid4().hex[:10]}{ext}'


def _save_product_image_from_bytes(product, content, order, ext='.jpg'):
	if not content:
		raise ValueError('empty_image_content')
	filename = _build_product_image_filename(product, ext)
	image = ProductImage(product=product, alt=product.name, order=order)
	if _storage_is_cloudinary():
		# Use direct Cloudinary upload with explicit timeout to avoid hanging workers.
		from cloudinary import uploader
		public_id = os.path.splitext(filename)[0]
		upload_timeout = max(5, int(os.environ.get('CLOUDINARY_UPLOAD_TIMEOUT_SECONDS', '25') or '25'))
		result = uploader.upload(
			ContentFile(content),
			folder='products',
			public_id=public_id,
			overwrite=False,
			unique_filename=False,
			use_filename=False,
			resource_type='image',
			timeout=upload_timeout,
		)
		storage_name = str((result or {}).get('public_id') or f'products/{public_id}')
		if not storage_name:
			raise ValueError('cloudinary_upload_missing_public_id')
		image.image.name = storage_name
		image.save()
		return image

	image.image.save(filename, ContentFile(content), save=False)
	image.save()
	return image


def _try_normalize_image_content(content, fallback_ext='.jpg'):
	"""
	Best-effort normalization for strict remote storages (e.g. Cloudinary).
	Returns (normalized_content, normalized_extension) or (original_content, fallback_ext).
	"""
	fallback = (fallback_ext or '.jpg').lower()
	if fallback not in IMAGE_EXTENSIONS:
		fallback = '.jpg'
	try:
		from PIL import Image, ImageOps, ImageFile
		ImageFile.LOAD_TRUNCATED_IMAGES = True
		with Image.open(io.BytesIO(content)) as img:
			img = ImageOps.exif_transpose(img)
			has_alpha = bool(
				img.mode in ('RGBA', 'LA')
				or ('transparency' in getattr(img, 'info', {}))
			)
			out = io.BytesIO()
			if has_alpha:
				img = img.convert('RGBA')
				img.save(out, format='PNG', optimize=True)
				normalized_ext = '.png'
			else:
				img = img.convert('RGB')
				img.save(out, format='JPEG', quality=90, optimize=True)
				normalized_ext = '.jpg'
			data = out.getvalue()
			if data:
				return data, normalized_ext
	except Exception:
		return content, fallback
	return content, fallback


def _create_product_image_from_url(product, image_url, order):
	"""Download an image URL and store it under products/."""
	response = requests.get(
		image_url,
		timeout=20,
		allow_redirects=True,
		headers={'User-Agent': 'De-Rukkies CSV Importer/1.0'},
	)
	response.raise_for_status()
	content = response.content or b''
	if not content:
		raise ValueError('empty image response')
	ext = _guess_image_extension(image_url, response.headers.get('Content-Type', ''))
	return _save_product_image_from_bytes(product, content, order, ext)


def _create_product_image_from_local_path(product, file_path, order):
	"""Copy a local image file into product image storage."""
	with open(file_path, 'rb') as fh:
		content = fh.read()
	if not content:
		raise ValueError('empty_local_file')
	ext = os.path.splitext(file_path)[1].lower()
	try:
		return _save_product_image_from_bytes(product, content, order, ext)
	except Exception as primary_exc:
		# Retry with normalized bytes for strict storage backends.
		norm_content, norm_ext = _try_normalize_image_content(content, fallback_ext=ext)
		normalized_original_ext = (ext or '').lower()
		if normalized_original_ext not in IMAGE_EXTENSIONS:
			normalized_original_ext = '.jpg'
		if norm_content == content and norm_ext == normalized_original_ext:
			raise
		try:
			return _save_product_image_from_bytes(product, norm_content, order, norm_ext)
		except Exception as normalized_exc:
			raise ValueError(
				f'local_image_save_failed primary={_summarize_exception(primary_exc)}; '
				f'normalized={_summarize_exception(normalized_exc)}'
			) from normalized_exc


def _create_product_image_from_data_uri(product, data_uri, order):
	"""Create a product image from a data:image/... URI."""
	header, encoded = data_uri.split(',', 1)
	match = re.search(r'data:image/([a-zA-Z0-9.+-]+);base64', header)
	if not match:
		raise ValueError('unsupported_data_uri')
	ext = f".{match.group(1).lower().replace('jpeg', 'jpg')}"
	if ext not in IMAGE_EXTENSIONS:
		ext = '.jpg'
	content = base64.b64decode(encoded)
	if not content:
		raise ValueError('empty_data_uri')
	return _save_product_image_from_bytes(product, content, order, ext)


def _as_storage_image_name(value):
	"""
	Convert inputs (full Cloudinary URL, /media/ path, etc.) into a storage name.
	Output example: 'products/xyz.jpg'
	"""
	v = str(value or '').strip()
	if not v:
		return ''

	if v.lower().startswith(('http://', 'https://')):
		parsed = urlparse(v)
		path = (parsed.path or '').strip()

		# Cloudinary URL patterns:
		# /<cloud>/image/upload/<transformations>/v123/folder/file.jpg
		# /<cloud>/image/upload/v123/folder/file.jpg
		if '/upload/' in path:
			after = path.split('/upload/', 1)[1].lstrip('/')
			parts = [p for p in after.split('/') if p]

			# Drop transformation segments until we hit version "v123"
			while parts and not re.match(r'^v\d+$', parts[0]):
				parts.pop(0)

			# Drop version segment if present
			if parts and re.match(r'^v\d+$', parts[0]):
				parts.pop(0)

			public_name = '/'.join(parts).strip('/')
			return public_name

		# Fallback: try to use last path segment (rare)
		host = str(parsed.netloc or '').lower()
		parts = [p for p in path.split('/') if p]
		if 'res.cloudinary.com' in host and len(parts) >= 2:
			# Typical non-upload Cloudinary path: /<cloud_name>/<public_id...>
			return '/'.join(parts[1:])
		return os.path.basename(path.strip('/'))

	return _normalize_media_image_path(v)


def _is_explicit_storage_reference(source: str) -> bool:
	"""
	True when the CSV value already looks like a concrete storage key/public_id.
	Used to avoid saving unresolved local file paths as fake image names.
	"""
	value = _normalize_media_image_path(source)
	if not value:
		return False
	lowered = value.lower()
	if lowered.startswith(('products/', 'categories/', 'hero/')):
		return True
	if lowered.startswith('media/'):
		return True
	if lowered.startswith('res.cloudinary.com/'):
		return True
	if lowered.startswith(('http://', 'https://')):
		return 'res.cloudinary.com/' in lowered
	return False


def _attach_csv_images_to_product(product, image_sources, archive_index=None, category_slugs=None):
	"""
	Attach images from CSV sources.
	Returns (created_count, failed_count, skipped_existing_count, failed_samples, fail_reason_counts).
	"""
	created = 0
	failed = 0
	skipped_existing = 0
	failed_samples = []
	fail_reason_counts = {
		'data_uri_invalid': 0,
		'download_failed': 0,
		'archive_copy_failed': 0,
		'local_copy_failed': 0,
		'path_not_found': 0,
	}
	order = product.images.count()

	existing_paths = set(_as_storage_image_name(v) for v in product.images.values_list('image', flat=True))
	existing_paths.discard('')

	for source in image_sources:
		source = str(source or '').strip()
		if not source:
			continue

		if source.startswith('data:image/'):
			try:
				_create_product_image_from_data_uri(product, source, order)
				created += 1
				order += 1
			except Exception as exc:
				failed += 1
				fail_reason_counts['data_uri_invalid'] += 1
				if len(failed_samples) < 5:
					failed_samples.append(f'{source[:72]}... (invalid data URI: {_summarize_exception(exc, 80)})')
				logger.exception('csv.import image_data_uri_failed product_id=%s', product.id)
			continue

		if source.lower().startswith(('http://', 'https://')):
			# If it's already a Cloudinary URL, attach by public name (no download).
			storage_name = _as_storage_image_name(source)
			if storage_name and _storage_is_cloudinary():
				if storage_name in existing_paths:
					skipped_existing += 1
					continue
				img = ProductImage(product=product, alt=product.name, order=order)
				img.image.name = storage_name
				img.save()
				existing_paths.add(storage_name)
				created += 1
				order += 1
				continue

			# Otherwise: try download (this uploads bytes into Cloudinary via .save()).
			try:
				_create_product_image_from_url(product, source, order)
				created += 1
				order += 1
			except Exception as exc:
				failed += 1
				fail_reason_counts['download_failed'] += 1
				if len(failed_samples) < 5:
					failed_samples.append(f'{source[:120]} (download failed: {_summarize_exception(exc, 80)})')
				logger.exception('csv.import image_download_failed product_id=%s source=%s', product.id, source)
			continue

		# Non-URL: first try ZIP archive/local filesystem to UPLOAD BYTES (best for Render).
		archive_file = _resolve_archive_file(source, archive_index)
		if archive_file:
			try:
				_create_product_image_from_local_path(product, archive_file, order)
				created += 1
				order += 1
				continue
			except Exception as exc:
				failed += 1
				fail_reason_counts['archive_copy_failed'] += 1
				if len(failed_samples) < 5:
					failed_samples.append(f'{source[:120]} (archive copy failed: {_summarize_exception(exc, 80)})')
				logger.exception('csv.import image_archive_copy_failed product_id=%s source=%s', product.id, source)
				continue

		local_file = _resolve_local_filesystem_path(source, category_slugs=category_slugs)
		if local_file:
			try:
				_create_product_image_from_local_path(product, local_file, order)
				created += 1
				order += 1
				continue
			except Exception as exc:
				failed += 1
				fail_reason_counts['local_copy_failed'] += 1
				if len(failed_samples) < 5:
					failed_samples.append(f'{source[:120]} (local copy failed: {_summarize_exception(exc, 80)})')
				logger.exception('csv.import image_local_copy_failed product_id=%s source=%s', product.id, source)
				continue

		# As a LAST resort: only attach when the value already looks like a storage/public-id reference.
		if not _is_explicit_storage_reference(source):
			failed += 1
			fail_reason_counts['path_not_found'] += 1
			if len(failed_samples) < 5:
				failed_samples.append(f'{source[:120]} (path not found)')
			logger.warning('csv.import image_path_not_found product_id=%s source=%s', product.id, source)
			continue

		storage_name = _as_storage_image_name(source)
		if not storage_name:
			failed += 1
			fail_reason_counts['path_not_found'] += 1
			if len(failed_samples) < 5:
				failed_samples.append(f'{source[:120]} (path not found)')
			logger.warning('csv.import image_path_not_found product_id=%s source=%s', product.id, source)
			continue

		if storage_name in existing_paths:
			skipped_existing += 1
			continue

		# Attach without calling default_storage.exists() (prevents Cloudinary HEAD hang)
		img = ProductImage(product=product, alt=product.name, order=order)
		img.image.name = storage_name
		img.save()
		existing_paths.add(storage_name)
		created += 1
		order += 1

	return created, failed, skipped_existing, failed_samples, fail_reason_counts


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	list_display = ('name', 'slug', 'parent', 'product_count_display', 'products_link', 'image_preview', 'is_active')
	prepopulated_fields = {'slug': ('name',)}
	search_fields = ('name', 'slug', 'description')
	list_filter = ('is_active', 'parent')
	readonly_fields = ('image_preview', 'media_folder_hint')

	def get_queryset(self, request):
		qs = super().get_queryset(request)
		return qs.annotate(product_count=Count('products', filter=Q(products__is_active=True)))

	def image_preview(self, obj):
		if obj and getattr(obj, 'image', None):
			try:
				url = obj.image.url
			except Exception:
				return 'Image unavailable'
			return format_html(
				'<img src="{}" style="width:56px;height:56px;object-fit:cover;border-radius:8px;" />',
				url
			)
		return 'No image'
	image_preview.short_description = 'Image'

	def media_folder_hint(self, obj):
		if not obj:
			return ''
		paths = category_media_paths(obj.slug or obj.name)
		raw = str(paths.get('raw', ''))
		processed = str(paths.get('processed', ''))
		archive = str(paths.get('archive', ''))
		return format_html(
			'<code>{}</code><br/><code>{}</code><br/><code>{}</code>',
			raw, processed, archive
		)
	media_folder_hint.short_description = 'Media folders'

	def product_count_display(self, obj):
		return getattr(obj, 'product_count', 0)
	product_count_display.short_description = 'Products'

	def products_link(self, obj):
		url = f"{reverse('admin:store_product_changelist')}?categories__id__exact={obj.id}"
		return format_html('<a href="{}">View products</a>', url)
	products_link.short_description = 'Quick Access'


@admin.register(HomeHeroSlide)
class HomeHeroSlideAdmin(admin.ModelAdmin):
	list_display = ('title', 'badge', 'sort_order', 'is_active', 'updated_at')
	list_filter = ('is_active',)
	search_fields = ('title', 'title_accent', 'badge', 'description')
	ordering = ('sort_order', 'id')


class ProductImageInline(admin.TabularInline):
	model = ProductImage
	extra = 1


class ProductAdminForm(forms.ModelForm):
	"""Render JSON list fields as readable text inputs in admin."""
	features = forms.CharField(
		required=False,
		widget=forms.Textarea(attrs={'rows': 5}),
		help_text='Enter one feature per line.'
	)
	benefits = forms.CharField(
		required=False,
		widget=forms.Textarea(attrs={'rows': 5}),
		help_text='Enter one benefit per line.'
	)
	tags = forms.CharField(
		required=False,
		help_text='Enter tags separated by commas.'
	)

	class Meta:
		model = Product
		fields = '__all__'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		features = self.instance.features if self.instance and self.instance.pk else []
		benefits = self.instance.benefits if self.instance and self.instance.pk else []
		tags = self.instance.tags if self.instance and self.instance.pk else []

		if isinstance(features, list):
			self.initial['features'] = '\n'.join(str(v) for v in features if str(v).strip())
		if isinstance(benefits, list):
			self.initial['benefits'] = '\n'.join(str(v) for v in benefits if str(v).strip())
		if isinstance(tags, list):
			self.initial['tags'] = ', '.join(str(v) for v in tags if str(v).strip())

	def _parse_list(self, value: str):
		if not value:
			return []
		items = []
		# Support both newline and comma-separated input.
		for line in str(value).replace('\r', '\n').split('\n'):
			for part in line.split(','):
				item = part.strip()
				if item:
					items.append(item)
		# de-duplicate while preserving order
		return list(dict.fromkeys(items))

	def clean_features(self):
		return self._parse_list(self.cleaned_data.get('features', ''))

	def clean_benefits(self):
		return self._parse_list(self.cleaned_data.get('benefits', ''))

	def clean_tags(self):
		return self._parse_list(self.cleaned_data.get('tags', ''))


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	form = ProductAdminForm
	list_display = ('name', 'slug', 'category_links', 'price', 'stock', 'is_featured', 'is_flash_sale', 'is_digital', 'is_active')
	list_filter = ('is_active', 'is_featured', 'is_flash_sale', 'is_digital', 'categories')
	search_fields = ('name', 'slug', 'description')
	inlines = [ProductImageInline]
	prepopulated_fields = {'slug': ('name',)}
	actions = [
		'generate_metadata_from_images',
		'mark_selected_active',
		'mark_selected_inactive',
		'mark_selected_featured',
		'mark_selected_not_featured',
		'mark_selected_flash_sale',
		'mark_selected_not_flash_sale',
		'mark_selected_digital',
		'mark_selected_not_digital',
	]
	# no auto-metadata fields
	change_list_template = 'admin/store/product/change_list.html'

	def get_queryset(self, request):
		return super().get_queryset(request).prefetch_related('categories')

	def category_links(self, obj):
		categories = list(obj.categories.all())
		if not categories:
			return '-'
		return format_html_join(
			', ',
			'<a href="{}?categories__id__exact={}">{}</a>',
			(
				(reverse('admin:store_product_changelist'), cat.id, cat.name)
				for cat in categories
			),
		)
	category_links.short_description = 'Categories'

	class CSVUploadForm(forms.Form):
		csv_file = forms.FileField(
			required=True,
			help_text=(
				'CSV columns: name,slug,description,price,stock,categories,is_active and optional '
				'image/image_url/images (multiple values can be separated with comma, semicolon, pipe, or newline).'
			)
		)
		image_archive = forms.FileField(
			required=False,
			help_text=(
				'Optional ZIP archive containing local image files referenced by CSV paths '
				'(for example: usd_image_test_imgs\\file.jpg).'
			),
		)

	def get_urls(self):
		urls = super().get_urls()
		custom_urls = [
			path('import-csv/', self.admin_site.admin_view(self.import_csv), name='store_product_import_csv'),
			path('generate-metadata/<int:product_id>/', self.admin_site.admin_view(self.generate_metadata_for_product), name='store_product_generate_metadata'),
		]
		return custom_urls + urls

	def generate_metadata_for_product(self, request, product_id):
		from django.shortcuts import get_object_or_404
		product = get_object_or_404(Product, pk=product_id)
		img = product.images.order_by('order').first()
		if not img:
			self.message_user(request, 'No image found for this product', level=messages.WARNING)
			return redirect(request.META.get('HTTP_REFERER', '..'))
		try:
			if getattr(settings, 'STORE_METADATA_ASYNC', False):
				analyze_and_apply_image.delay(img.id)
				self.message_user(request, 'Metadata analysis enqueued for product image', level=messages.SUCCESS)
			else:
				result = analyze_and_apply_image(img.id)
				applied = bool((result or {}).get('applied'))
				confidence = float((result or {}).get('confidence', 0.0))
				threshold = float(getattr(settings, 'STORE_AUTO_APPLY_CONFIDENCE', 0.85))
				if applied:
					self.message_user(request, f'Metadata applied (confidence: {confidence:.2f})', level=messages.SUCCESS)
				else:
					self.message_user(
						request,
						f'Metadata analyzed but not applied (confidence: {confidence:.2f} < threshold: {threshold:.2f}). Check Pending Metadata.',
						level=messages.WARNING
					)
		except Exception:
			logger.exception('Metadata generation failed product_id=%s image_id=%s', product_id, getattr(img, 'id', None))
			self.message_user(request, 'Failed to enqueue or run metadata analysis', level=messages.ERROR)
			return redirect(request.META.get('HTTP_REFERER', '..'))
		# redirect back to the product change page
		return redirect(reverse('admin:store_product_change', args=[product_id]))

	def import_csv(self, request):
		if request.method == 'POST':
			form = self.CSVUploadForm(request.POST, request.FILES)
			if form.is_valid():
				f = form.cleaned_data['csv_file']
				archive = form.cleaned_data.get('image_archive')
				temp_archive_dir = None
				archive_index = None
				try:
					started_at = time.monotonic()
					csv_time_budget_seconds = max(0, int(os.environ.get('CSV_IMPORT_TIME_BUDGET_SECONDS', '90') or '90'))
					timed_out = False
					if archive:
						temp_archive_dir = tempfile.mkdtemp(prefix='csv_img_archive_')
						with zipfile.ZipFile(archive) as zf:
							zf.extractall(temp_archive_dir)
						archive_index = _build_archive_index(temp_archive_dir)

					decoded = f.read().decode('utf-8').splitlines()
					reader = csv.DictReader(decoded)
					created = 0
					updated = 0
					images_created = 0
					images_failed = 0
					images_skipped_existing = 0
					image_fail_samples = []
					image_fail_reason_totals = {
						'data_uri_invalid': 0,
						'download_failed': 0,
						'archive_copy_failed': 0,
						'local_copy_failed': 0,
						'path_not_found': 0,
					}
					for row in reader:
						if csv_time_budget_seconds and _storage_is_cloudinary():
							elapsed = time.monotonic() - started_at
							if elapsed >= csv_time_budget_seconds:
								timed_out = True
								logger.warning(
									'csv.import paused reason=time_budget_exceeded elapsed=%.2fs budget=%ss',
									elapsed,
									csv_time_budget_seconds,
								)
								break
						name = row.get('name')
						if not name:
							continue
						slug = row.get('slug') or None
						description = row.get('description') or ''
						price = row.get('price') or '0'
						stock = int(row.get('stock') or 0)
						is_active = row.get('is_active', '1')
						is_active = str(is_active).strip() not in ('0', 'false', 'False')
						categories = row.get('categories', '')
						image_sources = _extract_csv_image_sources(row)
						# create product
						prod, created_flag = Product.objects.get_or_create(name=name, defaults={
							'slug': slug or None,
							'description': description,
							'price': price,
							'stock': stock,
							'is_active': is_active,
						})
						if created_flag:
							created += 1
						else:
							updated += 1
						category_slugs = []
						# attach categories
						if categories:
							for catname in [c.strip() for c in categories.split(',') if c.strip()]:
								cat_slug = normalize_slug(catname, fallback='general')
								cat, _ = Category.objects.get_or_create(name=catname, defaults={'slug': cat_slug})
								prod.categories.add(cat)
								category_slugs.append(cat.slug)
								ensure_category_media_structure(cat.slug)
						elif prod.id:
							category_slugs = list(prod.categories.values_list('slug', flat=True))

						# For existing products, avoid repeated remote downloads when images already exist.
						should_import_images = bool(image_sources) and (created_flag or not prod.images.exists())
						if should_import_images:
							c, f_count, s, samples, fail_reasons = _attach_csv_images_to_product(
								prod,
								image_sources,
								archive_index=archive_index,
								category_slugs=category_slugs,
							)
							images_created += c
							images_failed += f_count
							images_skipped_existing += s
							for reason_key, reason_count in (fail_reasons or {}).items():
								if reason_key in image_fail_reason_totals:
									image_fail_reason_totals[reason_key] += int(reason_count or 0)
							for sample in samples:
								if len(image_fail_samples) < 5:
									image_fail_samples.append(sample)
						prod.save()

					summary = (
						f'CSV import completed. Products created: {created}, existing seen: {updated}, '
						f'images added: {images_created}.'
					)
					if images_failed:
						summary += f' Image rows failed: {images_failed}.'
						failure_labels = {
							'path_not_found': 'path not found',
							'download_failed': 'download failed',
							'archive_copy_failed': 'archive copy failed',
							'local_copy_failed': 'local copy failed',
							'data_uri_invalid': 'invalid data uri',
						}
						parts = []
						for key in ('path_not_found', 'download_failed', 'archive_copy_failed', 'local_copy_failed', 'data_uri_invalid'):
							count = int(image_fail_reason_totals.get(key, 0))
							if count > 0:
								parts.append(f'{failure_labels[key]}: {count}')
						if parts:
							summary += f' Failure breakdown: {", ".join(parts)}.'
					if images_skipped_existing:
						summary += f' Duplicate image paths skipped: {images_skipped_existing}.'
					if image_fail_samples:
						summary += f' Sample failures: {" | ".join(image_fail_samples)}.'
					if timed_out:
						summary += (
							f' Import paused after {csv_time_budget_seconds}s to prevent request timeout. '
							'Run the same CSV again to continue remaining rows.'
						)
					if images_failed:
						messages.warning(request, summary)
					elif timed_out:
						messages.warning(request, summary)
					else:
						messages.success(request, summary)
				except zipfile.BadZipFile:
					messages.error(request, 'Invalid image archive. Please upload a valid .zip file.')
					return redirect(request.path)
				finally:
					if temp_archive_dir and os.path.isdir(temp_archive_dir):
						try:
							for root, dirs, files in os.walk(temp_archive_dir, topdown=False):
								for file_name in files:
									os.remove(os.path.join(root, file_name))
								for dir_name in dirs:
									os.rmdir(os.path.join(root, dir_name))
							os.rmdir(temp_archive_dir)
						except Exception:
							logger.warning('csv.import could_not_cleanup_temp_dir path=%s', temp_archive_dir)
				return redirect('..')
		else:
			form = self.CSVUploadForm()
		context = dict(
			self.admin_site.each_context(request),
			form=form,
			title='Import products from CSV',
		)
		return TemplateResponse(request, 'admin/store/product/import_csv.html', context)

	def generate_metadata_from_images(self, request, queryset):
		"""Admin action: enqueue metadata analysis for the first image of each selected product."""
		processed = 0
		applied = 0
		no_image = 0
		for product in queryset:
			img = product.images.order_by('order').first()
			if not img:
				no_image += 1
				continue
			try:
				if getattr(settings, 'STORE_METADATA_ASYNC', False):
					analyze_and_apply_image.delay(img.id)
					processed += 1
				else:
					result = analyze_and_apply_image(img.id) or {}
					processed += 1
					if result.get('applied'):
						applied += 1
			except Exception:
				logger.exception('Metadata generation failed for product_id=%s image_id=%s', product.id, getattr(img, 'id', None))

		if getattr(settings, 'STORE_METADATA_ASYNC', False):
			message = f"Enqueued metadata analysis for {processed} product image(s)."
		else:
			message = f"Analyzed {processed} product image(s), auto-applied metadata for {applied}."
		if no_image:
			message += f" {no_image} product(s) had no images."
		self.message_user(request, message)

	generate_metadata_from_images.short_description = 'Generate metadata from product images'

	def mark_selected_active(self, request, queryset):
		updated = queryset.update(is_active=True)
		self.message_user(request, f"{updated} product(s) marked as active.")
	mark_selected_active.short_description = 'Mark selected products as Active'

	def mark_selected_inactive(self, request, queryset):
		updated = queryset.update(is_active=False)
		self.message_user(request, f"{updated} product(s) marked as inactive.")
	mark_selected_inactive.short_description = 'Mark selected products as Inactive'

	def mark_selected_featured(self, request, queryset):
		updated = queryset.update(is_featured=True)
		self.message_user(request, f"{updated} product(s) marked as featured.")
	mark_selected_featured.short_description = 'Mark selected products as Featured'

	def mark_selected_not_featured(self, request, queryset):
		updated = queryset.update(is_featured=False)
		self.message_user(request, f"{updated} product(s) removed from featured.")
	mark_selected_not_featured.short_description = 'Remove selected products from Featured'

	def mark_selected_flash_sale(self, request, queryset):
		updated = queryset.update(is_flash_sale=True)
		self.message_user(request, f"{updated} product(s) marked as flash sale.")
	mark_selected_flash_sale.short_description = 'Mark selected products as Flash Sale'

	def mark_selected_not_flash_sale(self, request, queryset):
		updated = queryset.update(is_flash_sale=False)
		self.message_user(request, f"{updated} product(s) removed from flash sale.")
	mark_selected_not_flash_sale.short_description = 'Remove selected products from Flash Sale'

	def mark_selected_digital(self, request, queryset):
		updated = queryset.update(is_digital=True)
		self.message_user(request, f"{updated} product(s) marked as digital.")
	mark_selected_digital.short_description = 'Mark selected products as Digital'

	def mark_selected_not_digital(self, request, queryset):
		updated = queryset.update(is_digital=False)
		self.message_user(request, f"{updated} product(s) marked as non-digital.")
	mark_selected_not_digital.short_description = 'Mark selected products as Non-Digital'



@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
	list_display = ('product', 'alt', 'order')


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
	list_display = ('product', 'reviewer_name', 'rating', 'is_approved', 'created_at')
	list_filter = ('is_approved', 'rating', 'created_at')
	search_fields = ('product__name', 'reviewer_name', 'reviewer_email', 'comment')


@admin.register(PendingMetadata)
class PendingMetadataAdmin(admin.ModelAdmin):
	list_display = ('product', 'confidence', 'applied', 'created_at')
	list_filter = ('applied',)
	readonly_fields = ('metadata_pretty',)

	def metadata_pretty(self, obj):
		import json
		return json.dumps(obj.metadata, indent=2)
	metadata_pretty.short_description = 'Metadata JSON'


class CartItemInline(admin.TabularInline):
	model = CartItem
	extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'session_key', 'created_at', 'updated_at')
	inlines = [CartItemInline]


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
	list_display = ('name', 'price', 'delivery_days', 'active')
	list_filter = ('active',)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
	list_display = ('full_name', 'line1', 'city', 'country', 'phone')
	search_fields = ('full_name', 'line1', 'city', 'postal_code')


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	readonly_fields = ('product', 'quantity', 'price')
	extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ('order_number', 'user', 'status', 'total', 'created_at')
	list_filter = ('status', 'created_at')
	search_fields = ('order_number', 'user__username')
	inlines = [OrderItemInline]
	readonly_fields = ('created_at', 'updated_at')
	actions = ('mark_as_processing', 'mark_as_shipped', 'export_as_csv')

	def mark_as_processing(self, request, queryset):
		updated = queryset.update(status=Order.STATUS_PROCESSING)
		self.message_user(request, f"{updated} order(s) marked as processing")
	mark_as_processing.short_description = "Mark selected orders as Processing"

	def mark_as_shipped(self, request, queryset):
		updated = queryset.update(status=Order.STATUS_SHIPPED)
		# send shipping notification emails for orders with user email
		sent = 0
		for order in queryset:
			user = order.user
			if user and getattr(user, 'email', None):
				subject = f"Your order {order.order_number} has shipped"
				name = user.get_full_name() or user.username
				body = (
					f"Hello {name},\n\n"
					f"Good news — your order {order.order_number} has been shipped.\n"
					f"Total: {order.total}\n\n"
					"You can track your order from your account.\n\n"
					"Thanks,\nThe Team"
				)
				from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER if hasattr(settings, 'EMAIL_HOST_USER') else 'no-reply@example.com')
				shipping_address = ''
				try:
					addr = getattr(order, 'shipping_address', None)
					if addr:
						shipping_address = ", ".join(
							[p for p in [addr.line1, addr.city, addr.country] if p]
						)
				except Exception:
					shipping_address = ''
				html_body = render_react_email_html(
					'ShippingEmail',
					{
						'userName': name,
						'orderNumber': order.order_number,
						'carrier': 'Courier',
						'estimatedDelivery': '',
						'deliveryAddress': shipping_address,
						'trackingNumber': '',
						'trackingUrl': '',
						'orderUrl': f"{get_public_site_url(request)}/account",
						'siteName': 'De-Rukkies Collections',
						'supportEmail': getattr(settings, 'CONTACT_RECIPIENT_EMAIL', '') or getattr(settings, 'DEFAULT_FROM_EMAIL', ''),
					}
				)
				try:
					send_mail(subject, body, from_email, [user.email], html_message=html_body, fail_silently=True)
					sent += 1
				except Exception:
					# fail silently; admin can re-send manually
					pass
		self.message_user(request, f"{updated} order(s) marked as shipped — {sent} email(s) sent")
	mark_as_shipped.short_description = "Mark selected orders as Shipped"

	def export_as_csv(self, request, queryset):
		"""Export selected orders as CSV."""
		fieldnames = ['order_number', 'user', 'status', 'total', 'created_at']
		response = HttpResponse(content_type='text/csv')
		response['Content-Disposition'] = f'attachment; filename=orders_{datetime.now().strftime("%Y%m%d%H%M%S")}.csv'
		writer = csv.writer(response)
		writer.writerow(fieldnames)
		for order in queryset:
			writer.writerow([
				order.order_number,
				order.user.username if order.user else '',
				order.status,
				str(order.total),
				order.created_at.isoformat(),
			])
		return response
	export_as_csv.short_description = "Export selected orders to CSV"


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
	list_display = (
		'id', 'order', 'user', 'provider', 'paypal_order_id', 'provider_transaction_id',
		'status', 'amount', 'currency', 'payer_email', 'success', 'created_at', 'updated_at'
	)
	list_filter = ('provider', 'status', 'success', 'currency')
	search_fields = ('provider_transaction_id', 'paypal_order_id', 'payer_email', 'order__order_number', 'order__id', 'user__username')
	change_list_template = 'admin/store/paymenttransaction/change_list.html'

	def get_urls(self):
		urls = super().get_urls()
		custom_urls = [
			path(
				'flutterwave-balance/',
				self.admin_site.admin_view(self.flutterwave_balance_view),
				name='store_paymenttransaction_flutterwave_balance',
			),
		]
		return custom_urls + urls

	def flutterwave_balance_view(self, request):
		if not self.has_view_permission(request):
			return redirect('admin:login')

		selected_currency = str(request.GET.get('currency') or '').strip().upper()
		sort_key = str(request.GET.get('sort') or 'currency').strip().lower()
		force_refresh = str(request.GET.get('refresh') or '').strip() in {'1', 'true', 'yes'}

		context = {
			**self.admin_site.each_context(request),
			'title': 'Flutterwave Balance',
			'opts': self.model._meta,
			'has_view_permission': self.has_view_permission(request),
			'secret_configured': _flutterwave_secret_present(),
			'balance_rows': [],
			'error_message': '',
			'available_currencies': [],
			'selected_currency': selected_currency,
			'sort_key': sort_key,
			'flw_mode': (getattr(settings, 'FLUTTERWAVE_MODE', 'LIVE') or 'LIVE').strip().upper(),
			'flw_base_url': (getattr(settings, 'FLUTTERWAVE_BASE_URL', 'https://api.flutterwave.com/v3') or 'https://api.flutterwave.com/v3').rstrip('/'),
			'cache_seconds': int(getattr(settings, 'FLUTTERWAVE_BALANCE_CACHE_SECONDS', 60) or 60),
		}
		try:
			data = _fetch_flutterwave_balances(force_refresh=force_refresh)
			rows = data.get('rows') or []
			currencies = sorted({str((row or {}).get('currency') or '').upper() for row in rows if (row or {}).get('currency')})
			context['available_currencies'] = currencies
			if selected_currency:
				rows = [r for r in rows if str(r.get('currency') or '').upper() == selected_currency]

			def _num(value):
				try:
					return float(value)
				except Exception:
					return float('-inf')

			if sort_key == 'available_desc':
				rows = sorted(rows, key=lambda r: _num(r.get('available_balance')), reverse=True)
			elif sort_key == 'available_asc':
				rows = sorted(rows, key=lambda r: _num(r.get('available_balance')))
			elif sort_key == 'ledger_desc':
				rows = sorted(rows, key=lambda r: _num(r.get('ledger_balance')), reverse=True)
			elif sort_key == 'ledger_asc':
				rows = sorted(rows, key=lambda r: _num(r.get('ledger_balance')))
			else:
				sort_key = 'currency'
				rows = sorted(rows, key=lambda r: str(r.get('currency') or ''))

			context['sort_key'] = sort_key
			context['balance_rows'] = rows
			context['flw_mode'] = data.get('mode') or context['flw_mode']
			context['flw_base_url'] = data.get('base_url') or context['flw_base_url']
		except Exception as exc:
			logger.exception('admin.flutterwave_balance fetch_failed')
			context['error_message'] = str(exc)
			messages.error(request, f'Could not load Flutterwave balance: {exc}')

		return TemplateResponse(request, 'admin/store/paymenttransaction/flutterwave_balance.html', context)


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
	list_display = ('user', 'created_at', 'updated_at')
	filter_horizontal = ('products',)


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
	list_display = ('title', 'slug', 'created_at')
	prepopulated_fields = {'slug': ('title',)}


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
	list_display = ('full_name', 'email', 'subject', 'is_read', 'created_at')
	list_filter = ('is_read', 'created_at')
	search_fields = ('full_name', 'email', 'subject', 'message')
	readonly_fields = ('full_name', 'email', 'subject', 'message', 'ip_address', 'user_agent', 'created_at')


@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
	list_display = ('email', 'is_active', 'source', 'created_at', 'updated_at')
	list_filter = ('is_active', 'source', 'created_at')
	search_fields = ('email',)


@admin.register(AssistantPolicy)
class AssistantPolicyAdmin(admin.ModelAdmin):
	list_display = ('key', 'title', 'is_active', 'updated_at')
	list_filter = ('is_active',)
	search_fields = ('key', 'title', 'content')


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
	list_display = ('user', 'title', 'level', 'is_read', 'created_at', 'read_at')
	list_filter = ('level', 'is_read', 'created_at')
	search_fields = ('user__username', 'title', 'message')
	readonly_fields = ('created_at', 'updated_at', 'read_at')


@admin.register(UserMailboxMessage)
class UserMailboxMessageAdmin(admin.ModelAdmin):
	list_display = ('user', 'subject', 'category', 'is_read', 'created_at', 'read_at')
	list_filter = ('category', 'is_read', 'created_at')
	search_fields = ('user__username', 'subject', 'body')
	readonly_fields = ('created_at', 'updated_at', 'read_at')
def _flutterwave_secret_present():
	return bool(str(getattr(settings, 'FLUTTERWAVE_SECRET_KEY', '') or '').strip())


def _flutterwave_balance_cache_key():
	mode = (getattr(settings, 'FLUTTERWAVE_MODE', 'LIVE') or 'LIVE').strip().upper()
	base = (getattr(settings, 'FLUTTERWAVE_BASE_URL', 'https://api.flutterwave.com/v3') or 'https://api.flutterwave.com/v3').rstrip('/')
	return f'admin:flutterwave:balances:{mode}:{base}'


def _fetch_flutterwave_balances(*, force_refresh=False):
	"""Fetch Flutterwave balances for admin display (read-only)."""
	cache_key = _flutterwave_balance_cache_key()
	cache_ttl = int(getattr(settings, 'FLUTTERWAVE_BALANCE_CACHE_SECONDS', 60) or 60)
	if not force_refresh and cache_ttl > 0:
		cached = cache.get(cache_key)
		if cached:
			return cached

	flw_secret = (getattr(settings, 'FLUTTERWAVE_SECRET_KEY', '') or '').strip()
	flw_mode = (getattr(settings, 'FLUTTERWAVE_MODE', 'LIVE') or 'LIVE').strip().upper()
	flw_base_url = (getattr(settings, 'FLUTTERWAVE_BASE_URL', 'https://api.flutterwave.com/v3') or 'https://api.flutterwave.com/v3').rstrip('/')

	if not flw_secret:
		raise ValueError('Missing FLUTTERWAVE_SECRET_KEY')

	headers = {
		'Authorization': f'Bearer {flw_secret}',
		'Accept': 'application/json',
	}
	resp = requests.get(f'{flw_base_url}/balances', headers=headers, timeout=20)
	if resp.status_code not in (200, 201):
		raise ValueError(f'Flutterwave balance request failed ({resp.status_code}): {resp.text[:300]}')
	try:
		payload = resp.json()
	except ValueError as exc:
		raise ValueError('Invalid JSON response from Flutterwave balances endpoint') from exc

	rows = payload.get('data') or []
	if not isinstance(rows, list):
		rows = []

	normalized = []
	for row in rows:
		if not isinstance(row, dict):
			continue
		currency = str(row.get('currency') or row.get('currency_code') or '').strip().upper()
		available = row.get('available_balance')
		ledger = row.get('ledger_balance')
		normalized.append({
			'currency': currency or 'N/A',
			'available_balance': available if available is not None else '',
			'ledger_balance': ledger if ledger is not None else '',
			'raw': row,
		})

	result = {
		'mode': flw_mode,
		'base_url': flw_base_url,
		'rows': normalized,
		'payload': payload,
	}
	if cache_ttl > 0:
		cache.set(cache_key, result, cache_ttl)
	return result
