from django.conf import settings
from django.db import models
from django.utils.text import slugify
import uuid


class Category(models.Model):
	name = models.CharField(max_length=200)
	slug = models.SlugField(max_length=200, unique=True)
	description = models.TextField(blank=True)
	image = models.ImageField(upload_to='categories/', max_length=255, null=True, blank=True)
	parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.CASCADE)
	is_active = models.BooleanField(default=True)

	class Meta:
		verbose_name_plural = 'categories'

	def __str__(self):
		return self.name


class HomeHeroSlide(models.Model):
	badge = models.CharField(max_length=120, blank=True)
	title = models.CharField(max_length=255)
	title_accent = models.CharField(max_length=255, blank=True)
	description = models.TextField(blank=True)
	image = models.ImageField(upload_to='hero/', max_length=255, null=True, blank=True)
	cta_text = models.CharField(max_length=80, blank=True)
	cta_link = models.CharField(max_length=255, blank=True, default='/products')
	secondary_cta_text = models.CharField(max_length=80, blank=True)
	secondary_cta_link = models.CharField(max_length=255, blank=True, default='/about')
	promo = models.CharField(max_length=120, blank=True)
	sort_order = models.PositiveIntegerField(default=0)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['sort_order', 'id']

	def __str__(self):
		return self.title


class Product(models.Model):
	name = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255, unique=True)
	description = models.TextField(blank=True)
	price = models.DecimalField(max_digits=10, decimal_places=2)
	stock = models.PositiveIntegerField(default=0)
	original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
	review_count = models.PositiveIntegerField(default=0)
	is_digital = models.BooleanField(default=False)
	is_flash_sale = models.BooleanField(default=False)
	features = models.JSONField(default=list, blank=True)
	benefits = models.JSONField(default=list, blank=True)
	tags = models.JSONField(default=list, blank=True)
	categories = models.ManyToManyField(Category, related_name='products', blank=True)
	is_active = models.BooleanField(default=True)
	is_featured = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.name)
		super().save(*args, **kwargs)

	def __str__(self):
		return self.name


class ProductReview(models.Model):
	product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
	reviewer_name = models.CharField(max_length=120, blank=True)
	reviewer_email = models.EmailField(blank=True)
	rating = models.PositiveSmallIntegerField(default=5)
	comment = models.TextField()
	is_approved = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		name = self.reviewer_name or (self.user.username if self.user else 'Anonymous')
		return f"Review by {name} ({self.rating}/5)"


class ProductImage(models.Model):
	product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
	image = models.ImageField(upload_to='products/', max_length=255)
	alt = models.CharField(max_length=255, blank=True)
	order = models.PositiveIntegerField(default=0)

	class Meta:
		ordering = ['order']

	def __str__(self):
		return f"Image for {self.product.name} ({self.id})"


class Cart(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
	session_key = models.CharField(max_length=40, null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"Cart {self.id} ({'user:' + str(self.user) if self.user else 'anonymous'})"

	@property
	def total(self):
		items = self.items.all()
		return sum([item.subtotal for item in items])


class CartItem(models.Model):
	cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
	product = models.ForeignKey(Product, on_delete=models.PROTECT)
	quantity = models.PositiveIntegerField(default=1)

	@property
	def subtotal(self):
		return self.product.price * self.quantity

	def __str__(self):
		return f"{self.quantity} x {self.product.name}"


class ShippingMethod(models.Model):
	name = models.CharField(max_length=200)
	price = models.DecimalField(max_digits=8, decimal_places=2)
	delivery_days = models.CharField(max_length=100, blank=True)
	active = models.BooleanField(default=True)

	def __str__(self):
		return self.name


class Address(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
	full_name = models.CharField(max_length=255)
	line1 = models.CharField(max_length=255)
	line2 = models.CharField(max_length=255, blank=True)
	city = models.CharField(max_length=100)
	state = models.CharField(max_length=100, blank=True)
	postal_code = models.CharField(max_length=20)
	country = models.CharField(max_length=100)
	phone = models.CharField(max_length=50, blank=True)

	def __str__(self):
		return f"{self.full_name} - {self.line1}, {self.city}"


class Order(models.Model):
	STATUS_PENDING = 'pending'
	STATUS_PAID = 'paid'
	STATUS_PROCESSING = 'processing'
	STATUS_SHIPPED = 'shipped'
	STATUS_DELIVERED = 'delivered'

	STATUS_CHOICES = [
		(STATUS_PENDING, 'Pending'),
		(STATUS_PAID, 'Paid'),
		(STATUS_PROCESSING, 'Processing'),
		(STATUS_SHIPPED, 'Shipped'),
		(STATUS_DELIVERED, 'Delivered'),
	]

	user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
	order_number = models.CharField(max_length=32, unique=True, blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
	shipping_method = models.ForeignKey(ShippingMethod, null=True, blank=True, on_delete=models.SET_NULL)
	shipping_address = models.ForeignKey(Address, null=True, blank=True, on_delete=models.SET_NULL, related_name='shipping_orders')
	billing_address = models.ForeignKey(Address, null=True, blank=True, on_delete=models.SET_NULL, related_name='billing_orders')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

	def __str__(self):
		if self.order_number:
			return f"Order {self.order_number} - {self.status}"
		return f"Order {self.id} - {self.status}"

	def save(self, *args, **kwargs):
		# Ensure an order_number exists for tracking (human-safe short uuid)
		if not self.order_number:
			self.order_number = uuid.uuid4().hex[:12].upper()
		super().save(*args, **kwargs)


class OrderItem(models.Model):
	order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
	product = models.ForeignKey(Product, on_delete=models.PROTECT)
	quantity = models.PositiveIntegerField(default=1)
	price = models.DecimalField(max_digits=10, decimal_places=2)

	@property
	def subtotal(self):
		return self.price * self.quantity

	def __str__(self):
		return f"{self.quantity} x {self.product.name}"


class PaymentLink(models.Model):
	class Gateway(models.TextChoices):
		STRIPE = 'stripe', 'Stripe'
		FLUTTERWAVE = 'flutterwave', 'Flutterwave'

	class Status(models.TextChoices):
		PENDING = 'pending', 'Pending'
		PROCESSING = 'processing', 'Processing'
		PAID = 'paid', 'Paid'
		FAILED = 'failed', 'Failed'
		EXPIRED = 'expired', 'Expired'
		REVOKED = 'revoked', 'Revoked'

	reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
	customer_name = models.CharField(max_length=160)
	customer_email = models.EmailField()
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	currency = models.CharField(max_length=3)
	description = models.CharField(max_length=240)
	gateway = models.CharField(max_length=16, choices=Gateway.choices)
	status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
	expires_at = models.DateTimeField(db_index=True)
	created_at = models.DateTimeField(auto_now_add=True)
	paid_at = models.DateTimeField(null=True, blank=True)
	order_reference = models.CharField(max_length=64, blank=True)
	created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='created_payment_links')

	class Meta:
		ordering = ('-created_at', '-pk')
		verbose_name_plural = 'Payment Links'
		constraints = [
			models.CheckConstraint(condition=models.Q(amount__gt=0), name='payment_link_positive_amount'),
			models.CheckConstraint(
				condition=models.Q(status='paid', paid_at__isnull=False) | (~models.Q(status='paid') & models.Q(paid_at__isnull=True)),
				name='payment_link_valid_paid_timestamp',
			),
		]

	def __str__(self):
		return self.reference.hex


class PaymentLinkAttempt(models.Model):
	class Status(models.TextChoices):
		ACTIVE = 'active', 'Active'
		FAILED = 'failed', 'Failed'
		PAID = 'paid', 'Paid'

	link = models.ForeignKey(PaymentLink, on_delete=models.PROTECT, related_name='attempts')
	reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
	status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
	checkout_url = models.URLField(max_length=2048, blank=True)
	provider_session = models.CharField(max_length=255, blank=True)
	expires_at = models.DateTimeField()
	created_at = models.DateTimeField(auto_now_add=True)
	last_checked_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=('link',), condition=models.Q(status='active'), name='payment_link_single_active_attempt'),
			models.UniqueConstraint(fields=('link',), condition=models.Q(status='paid'), name='payment_link_single_paid_attempt'),
		]


class PaymentLinkAudit(models.Model):
	link = models.ForeignKey(PaymentLink, on_delete=models.PROTECT, related_name='audit')
	actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
	action = models.CharField(max_length=40)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ('-created_at', '-pk')


class PaymentLinkThrottle(models.Model):
	key = models.CharField(max_length=64, primary_key=True)
	window_start = models.DateTimeField()
	hits = models.PositiveIntegerField(default=0)


class PaymentLinkNotice(models.Model):
	link = models.ForeignKey(PaymentLink, on_delete=models.PROTECT)
	kind = models.CharField(max_length=24)
	recipient = models.EmailField()
	created_at = models.DateTimeField(auto_now_add=True)
	claimed_at = models.DateTimeField(null=True, blank=True)
	sent_at = models.DateTimeField(null=True, blank=True)
	cancelled_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=('link', 'kind'), condition=~models.Q(kind='invitation'), name='payment_link_unique_paid_notice'),
		]


class PaymentTransaction(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='payment_transactions')
	order = models.ForeignKey(Order, related_name='transactions', on_delete=models.CASCADE, null=True, blank=True)
	payment_link = models.ForeignKey(PaymentLink, related_name='transactions', on_delete=models.PROTECT, null=True, blank=True)
	provider = models.CharField(max_length=50)
	paypal_order_id = models.CharField(max_length=64, blank=True, db_index=True)
	provider_transaction_id = models.CharField(max_length=255, blank=True)
	status = models.CharField(max_length=32, default='pending', db_index=True)
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	currency = models.CharField(max_length=10, default='USD')
	payer_email = models.EmailField(blank=True)
	success = models.BooleanField(default=False)
	raw_response = models.JSONField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True, null=True)

	class Meta:
		constraints = [
			models.CheckConstraint(
				condition=models.Q(order__isnull=False, payment_link__isnull=True) | models.Q(order__isnull=True, payment_link__isnull=False),
				name='payment_transaction_one_source',
			),
			models.UniqueConstraint(fields=('payment_link',), condition=models.Q(success=True), name='payment_link_unique_success'),
			models.UniqueConstraint(
				fields=('provider', 'provider_transaction_id'), condition=models.Q(payment_link__isnull=False),
				name='payment_link_unique_provider_transaction',
			),
		]

	def __str__(self):
		if self.payment_link_id:
			return f'{self.provider} payment-link transaction ({self.status})'
		return f"{self.provider} txn for order {self.order_id} ({self.status})"


class Wishlist(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
	products = models.ManyToManyField(Product, related_name='wishlist_items', blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"Wishlist for {self.user.username}"


class Page(models.Model):
	title = models.CharField(max_length=255, unique=True)
	slug = models.SlugField(max_length=255, unique=True)
	content = models.TextField()
	seo_description = models.CharField(max_length=160, blank=True)
	seo_keywords = models.CharField(max_length=255, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.title)
		super().save(*args, **kwargs)

	class Meta:
		ordering = ['title']

	def __str__(self):
		return self.title


class AssistantPolicy(models.Model):
	key = models.CharField(max_length=80, unique=True)
	title = models.CharField(max_length=200)
	content = models.TextField()
	is_active = models.BooleanField(default=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['key']

	def __str__(self):
		return f"{self.title} ({self.key})"


class UserNotification(models.Model):
	LEVEL_INFO = 'info'
	LEVEL_SUCCESS = 'success'
	LEVEL_WARNING = 'warning'
	LEVEL_ERROR = 'error'
	LEVEL_CHOICES = [
		(LEVEL_INFO, 'Info'),
		(LEVEL_SUCCESS, 'Success'),
		(LEVEL_WARNING, 'Warning'),
		(LEVEL_ERROR, 'Error'),
	]

	user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notifications', on_delete=models.CASCADE)
	title = models.CharField(max_length=200)
	message = models.TextField()
	level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_INFO)
	is_read = models.BooleanField(default=False)
	read_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.user} - {self.title}"


class UserMailboxMessage(models.Model):
	CATEGORY_GENERAL = 'general'
	CATEGORY_SECURITY = 'security'
	CATEGORY_ORDER = 'order'
	CATEGORY_PAYMENT = 'payment'
	CATEGORY_ACCOUNT = 'account'
	CATEGORY_CHOICES = [
		(CATEGORY_GENERAL, 'General'),
		(CATEGORY_SECURITY, 'Security'),
		(CATEGORY_ORDER, 'Order'),
		(CATEGORY_PAYMENT, 'Payment'),
		(CATEGORY_ACCOUNT, 'Account'),
	]

	user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='mailbox_messages', on_delete=models.CASCADE)
	subject = models.CharField(max_length=255)
	body = models.TextField()
	category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default=CATEGORY_GENERAL)
	is_read = models.BooleanField(default=False)
	read_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.user} - {self.subject}"


class PendingMetadata(models.Model):
	product = models.ForeignKey(Product, related_name='pending_metadata', on_delete=models.CASCADE)
	metadata = models.JSONField()
	confidence = models.FloatField(default=0.0)
	applied = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"PendingMetadata for {self.product} ({self.id})"


class ContactMessage(models.Model):
	full_name = models.CharField(max_length=255)
	email = models.EmailField()
	subject = models.CharField(max_length=255)
	message = models.TextField()
	ip_address = models.CharField(max_length=64, blank=True)
	user_agent = models.CharField(max_length=512, blank=True)
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.full_name} - {self.subject}"


class NewsletterSubscription(models.Model):
	email = models.EmailField(unique=True)
	is_active = models.BooleanField(default=True)
	source = models.CharField(max_length=50, blank=True)
	ip_address = models.CharField(max_length=64, blank=True)
	user_agent = models.CharField(max_length=512, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return self.email

