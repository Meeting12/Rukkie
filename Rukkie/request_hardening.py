import logging
import re

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseNotFound

logger = logging.getLogger(__name__)


class RequestHardeningMiddleware:
    """
    Block common web scanner probes and oversized payload abuse before view handling.
    """

    ALLOWED_METHODS = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'}
    PROBE_PATTERNS = [
        re.compile(r'\.php($|/)', re.IGNORECASE),
        re.compile(r'wp-admin|wp-login|xmlrpc\.php', re.IGNORECASE),
        re.compile(r'vendor/phpunit|cgi-bin|boaform', re.IGNORECASE),
        re.compile(r'(^|/)\.env($|/)|(^|/)\.git($|/)', re.IGNORECASE),
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _max_body_bytes_for_path(path: str) -> int:
        default_max = int(getattr(settings, 'REQUEST_BODY_MAX_BYTES', 2 * 1024 * 1024))
        csv_import_max = int(getattr(settings, 'CSV_IMPORT_MAX_BYTES', default_max))
        if (path or '').startswith('/admin/store/product/import-csv/'):
            return csv_import_max
        return default_max

    def __call__(self, request):
        method = (request.method or '').upper()
        if method and method not in self.ALLOWED_METHODS:
            logger.warning('security.blocked method=%s path=%s', method, request.path)
            return HttpResponseNotAllowed(sorted(self.ALLOWED_METHODS))

        raw_path = request.path or ''
        query_string = request.META.get('QUERY_STRING', '')
        attack_surface = f'{raw_path}?{query_string}'

        for pattern in self.PROBE_PATTERNS:
            if pattern.search(attack_surface):
                logger.warning('security.blocked probe path=%s ip=%s', raw_path, request.META.get('REMOTE_ADDR'))
                return HttpResponseNotFound()

        if '%00' in attack_surface or '\x00' in attack_surface:
            logger.warning('security.blocked null-byte path=%s ip=%s', raw_path, request.META.get('REMOTE_ADDR'))
            return HttpResponse(status=400)

        max_bytes = self._max_body_bytes_for_path(raw_path)
        content_length = request.META.get('CONTENT_LENGTH')
        if content_length:
            try:
                length = int(content_length)
            except (TypeError, ValueError):
                length = 0
            if length > max_bytes:
                logger.warning('security.blocked oversized_body path=%s bytes=%s max=%s', raw_path, length, max_bytes)
                return HttpResponse(status=413)

        return self.get_response(request)
