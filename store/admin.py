from django.contrib import admin
import csv
import mimetypes
import os
import re
import tempfile
import zipfile
from urllib.parse import urlparse, unquote
import base64
from django.http import HttpResponse
from datetime import datetime
from django.core.mail import send_mail
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
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
	Wishlist, Page, ContactMessage, NewsletterSubscription
)
from .media_layout import normalize_slug, ensure_category_media_structure, category_media_paths
from .tasks import analyze_and_apply_image

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


def _resolve_existing_image_path(value):
	"""Resolve a CSV path to an existing media file path."""
	normalized = _normalize_media_image_path(value)
	if not normalized:
		return ''
	if default_storage.exists(normalized):
		return normalized
	# Support bare filenames like "chair.jpg" by checking products/ folder.
	filename = os.path.basename(normalized)
	if filename:
		candidate = f'products/{filename}'
		if default_storage.exists(candidate):
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
	base = slugify(product.slug or product.name) or 'product'
	filename = f'{base}-{uuid.uuid4().hex[:10]}{ext}'
	image = ProductImage(product=product, alt=product.name, order=order)
	image.image.save(filename, ContentFile(content), save=False)
	image.save()
	return image


def _create_product_image_from_local_path(product, file_path, order):
	"""Copy a local image file into product image storage."""
	with open(file_path, 'rb') as fh:
		content = fh.read()
	if not content:
		raise ValueError('empty_local_file')
	ext = os.path.splitext(file_path)[1].lower()
	if ext not in IMAGE_EXTENSIONS:
		ext = '.jpg'
	base = slugify(product.slug or product.name) or 'product'
	filename = f'{base}-{uuid.uuid4().hex[:10]}{ext}'
	image = ProductImage(product=product, alt=product.name, order=order)
	image.image.save(filename, ContentFile(content), save=False)
	image.save()
	return image


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
	base = slugify(product.slug or product.name) or 'product'
	filename = f'{base}-{uuid.uuid4().hex[:10]}{ext}'
	image = ProductImage(product=product, alt=product.name, order=order)
	image.image.save(filename, ContentFile(content), save=False)
	image.save()
	return image


def _attach_csv_images_to_product(product, image_sources, archive_index=None, category_slugs=None):
	"""
	Attach images from CSV sources.
	Returns (created_count, failed_count, skipped_existing_count, failed_samples).
	"""
	created = 0
	failed = 0
	skipped_existing = 0
	failed_samples = []
	order = product.images.count()
	existing_paths = set(product.images.values_list('image', flat=True))

	for source in image_sources:
		source = str(source or '').strip()
		if not source:
			continue

		if source.startswith('data:image/'):
			try:
				_create_product_image_from_data_uri(product, source, order)
				created += 1
				order += 1
			except Exception:
				failed += 1
				if len(failed_samples) < 5:
					failed_samples.append(f'{source[:72]}... (invalid data URI)')
				logger.exception('csv.import image_data_uri_failed product_id=%s', product.id)
			continue

		if source.lower().startswith(('http://', 'https://')):
			# Common export format: absolute URL to this site's /media/... path.
			# Resolve to local media file first to avoid self-download failures/timeouts.
			parsed = urlparse(source)
			local_candidate = _resolve_existing_image_path(parsed.path or '')
			if local_candidate:
				if local_candidate in existing_paths:
					skipped_existing += 1
					continue
				ProductImage.objects.create(
					product=product,
					image=local_candidate,
					alt=product.name,
					order=order,
				)
				existing_paths.add(local_candidate)
				created += 1
				order += 1
				continue
			try:
				_create_product_image_from_url(product, source, order)
				created += 1
				order += 1
			except Exception:
				failed += 1
				if len(failed_samples) < 5:
					failed_samples.append(f'{source[:120]} (download failed)')
				logger.exception('csv.import image_download_failed product_id=%s source=%s', product.id, source)
			continue

		relative_path = _resolve_existing_image_path(source)
		if not relative_path:
			archive_file = _resolve_archive_file(source, archive_index)
			if archive_file:
				try:
					_create_product_image_from_local_path(product, archive_file, order)
					created += 1
					order += 1
					continue
				except Exception:
					failed += 1
					if len(failed_samples) < 5:
						failed_samples.append(f'{source[:120]} (archive copy failed)')
					logger.exception('csv.import image_archive_copy_failed product_id=%s source=%s', product.id, source)
					continue

			local_file = _resolve_local_filesystem_path(source, category_slugs=category_slugs)
			if local_file:
				try:
					_create_product_image_from_local_path(product, local_file, order)
					created += 1
					order += 1
					continue
				except Exception:
					failed += 1
					if len(failed_samples) < 5:
						failed_samples.append(f'{source[:120]} (local copy failed)')
					logger.exception('csv.import image_local_copy_failed product_id=%s source=%s', product.id, source)
					continue

			failed += 1
			if len(failed_samples) < 5:
				failed_samples.append(f'{source[:120]} (path not found)')
			logger.warning('csv.import image_path_not_found product_id=%s source=%s', product.id, source)
			continue
		if relative_path in existing_paths:
			skipped_existing += 1
			continue

		ProductImage.objects.create(
			product=product,
			image=relative_path,
			alt=product.name,
			order=order,
		)
		existing_paths.add(relative_path)
		created += 1
		order += 1

	return created, failed, skipped_existing, failed_samples


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
			return format_html(
				'<img src="{}" style="width:56px;height:56px;object-fit:cover;border-radius:8px;" />',
				obj.image.url
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
	list_display = ('name', 'slug', 'category_links', 'price', 'stock', 'is_active')
	list_filter = ('is_active', 'categories')
	search_fields = ('name', 'slug', 'description')
	inlines = [ProductImageInline]
	prepopulated_fields = {'slug': ('name',)}
	actions = ['generate_metadata_from_images']
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
					for row in reader:
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
							c, f_count, s, samples = _attach_csv_images_to_product(
								prod,
								image_sources,
								archive_index=archive_index,
								category_slugs=category_slugs,
							)
							images_created += c
							images_failed += f_count
							images_skipped_existing += s
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
					if images_skipped_existing:
						summary += f' Duplicate image paths skipped: {images_skipped_existing}.'
					if image_fail_samples:
						summary += f' Sample failures: {" | ".join(image_fail_samples)}.'
					if images_failed:
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
				try:
					send_mail(subject, body, from_email, [user.email], fail_silently=True)
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

