class CSPMiddleware:
    """Middleware to apply a strict, functional Content-Security-Policy header.

    The policy matches the required directives for Stripe, Flutterwave, and PayPal.
    """

    POLICY = (
        "default-src 'self'; "
        "script-src 'self' https://js.stripe.com https://checkout.flutterwave.com https://www.paypal.com https://www.paypalobjects.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "connect-src 'self' https://api.stripe.com https://api.flutterwave.com https://www.paypal.com; "
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
        # Apply CSP header
        response.setdefault('Content-Security-Policy', self.POLICY)
        return response
