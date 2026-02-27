from __future__ import annotations

from gunicorn.glogging import Logger


class IgnoreHealthCheckLogger(Logger):
    """Skip noisy access logs for health probes while keeping normal logs."""

    def access(self, resp, req, environ, request_time):  # type: ignore[override]
        path = ""
        try:
            path = str((environ or {}).get("RAW_URI") or (environ or {}).get("PATH_INFO") or "")
        except Exception:
            path = ""
        if path.startswith("/api/health/"):
            return
        return super().access(resp, req, environ, request_time)
