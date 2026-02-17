class SecurityHeadersMiddleware:
    """Add common security headers: Referrer-Policy, Permissions-Policy, X-Content-Type-Options.

    This complements existing Django settings that enable HSTS, secure cookies, and CSP middleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # X-Content-Type-Options
        response.setdefault('X-Content-Type-Options', 'nosniff')
        response.setdefault('X-Frame-Options', 'DENY')
        response.setdefault('X-XSS-Protection', '1; mode=block')
        response.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        response.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
        # Referrer-Policy
        try:
            from django.conf import settings
            ref_policy = getattr(settings, 'REFERRER_POLICY', 'same-origin')
            response.setdefault('Referrer-Policy', ref_policy)
            perm = getattr(settings, 'PERMISSIONS_POLICY', None)
            if perm:
                response.setdefault('Permissions-Policy', perm)
        except Exception:
            pass
        return response
