class CSPMiddleware:
    """Middleware to apply a strict, functional Content-Security-Policy header.

    The policy matches the required directives for Stripe, Flutterwave, and PayPal.
    """

    BASE_SCRIPT_SRC = (
        "'self' https://js.stripe.com https://checkout.flutterwave.com "
        "https://www.paypal.com https://www.paypalobjects.com https://static.cloudflareinsights.com"
    )

    BASE_CONNECT_SRC = (
        "'self' https://api.stripe.com https://api.flutterwave.com https://www.paypal.com "
        "https://cloudflareinsights.com"
    )

    POLICY = (
        "default-src 'self'; "
        f"script-src {BASE_SCRIPT_SRC}; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        f"connect-src {BASE_CONNECT_SRC}; "
        "frame-src https://js.stripe.com https://checkout.flutterwave.com https://www.paypal.com; "
        "form-action 'self' https://checkout.flutterwave.com https://www.paypal.com https://checkout.stripe.com; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none';"
    )

    ADMIN_POLICY = (
        "default-src 'self'; "
        f"script-src 'unsafe-inline' {BASE_SCRIPT_SRC}; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        f"connect-src {BASE_CONNECT_SRC}; "
        "frame-src https://js.stripe.com https://checkout.flutterwave.com https://www.paypal.com; "
        "form-action 'self' https://checkout.flutterwave.com https://www.paypal.com https://checkout.stripe.com; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none';"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Keep strict CSP for storefront/API; allow inline admin scripts only for Django admin pages.
        if str(getattr(request, 'path', '')).startswith('/admin/'):
            response.setdefault('Content-Security-Policy', self.ADMIN_POLICY)
        else:
            response.setdefault('Content-Security-Policy', self.POLICY)
        return response
