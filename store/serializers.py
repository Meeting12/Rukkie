from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Product, ProductImage, Category, HomeHeroSlide, Cart, CartItem, Order, OrderItem, ShippingMethod, Address, Wishlist, Page, PaymentTransaction, ProductReview

User = get_user_model()


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        if not getattr(obj, 'image', None):
            return ''
        try:
            request = self.context.get('request')
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        except Exception:
            return ''

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'image_url', 'alt', 'order']


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        if not getattr(obj, 'image', None):
            return ''
        try:
            request = self.context.get('request')
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        except Exception:
            return ''

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'image_url', 'parent', 'is_active', 'product_count']


class HomeHeroSlideSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        if not getattr(obj, 'image', None):
            return ''
        try:
            request = self.context.get('request')
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        except Exception:
            return ''

    class Meta:
        model = HomeHeroSlide
        fields = [
            'id',
            'badge',
            'title',
            'title_accent',
            'description',
            'image',
            'image_url',
            'cta_text',
            'cta_link',
            'secondary_cta_text',
            'secondary_cta_link',
            'promo',
            'sort_order',
            'is_active',
        ]


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'original_price', 'stock', 'rating', 'review_count',
            'is_active', 'is_featured', 'is_flash_sale', 'is_digital', 'created_at', 'images', 'categories',
            'features', 'benefits', 'tags'
        ]


class ProductReviewSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    verified = serializers.SerializerMethodField()

    def get_display_name(self, obj):
        if obj.reviewer_name:
            return obj.reviewer_name
        if obj.user_id and getattr(obj.user, 'username', None):
            return obj.user.username
        return 'Anonymous'

    def get_verified(self, obj):
        return bool(obj.user_id)

    class Meta:
        model = ProductReview
        fields = ['id', 'product', 'display_name', 'reviewer_name', 'reviewer_email', 'rating', 'comment', 'verified', 'created_at']
        read_only_fields = ['id', 'product', 'display_name', 'verified', 'created_at']


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'subtotal']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'session_key', 'items', 'total']


class ShippingMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingMethod
        fields = ['id', 'name', 'price', 'delivery_days', 'active']


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'price', 'subtotal']


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = [
            'id',
            'provider',
            'paypal_order_id',
            'provider_transaction_id',
            'status',
            'amount',
            'currency',
            'payer_email',
            'success',
            'created_at',
            'updated_at',
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = AddressSerializer(read_only=True)
    billing_address = AddressSerializer(read_only=True)
    transactions = PaymentTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'user', 'status', 'shipping_method', 'shipping_address', 'billing_address', 'total', 'items', 'transactions', 'created_at']


class WishlistSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'user', 'products', 'created_at', 'updated_at']


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ['id', 'title', 'slug', 'content', 'seo_description', 'seo_keywords', 'created_at']


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']
