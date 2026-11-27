from __future__ import annotations

from gunicorn.glogging import Logger


class IgnoreHealthCheckLogger(Logger):
    """Omit health probes and URLs that contain payment-link credentials."""

    def access(self, resp, req, environ, request_time):  # type: ignore[override]
        path = ""
        try:
            path = str((environ or {}).get("RAW_URI") or (environ or {}).get("PATH_INFO") or "")
        except Exception:
            path = ""
        if path.startswith(("/api/health/", "/pay/")):
            return
        return super().access(resp, req, environ, request_time)
