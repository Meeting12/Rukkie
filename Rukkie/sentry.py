from __future__ import annotations

import os
from typing import Any


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float = 0.0) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(str(value).strip())
    except Exception:
        return default


def init_sentry(*, debug: bool = False) -> bool:
    dsn = str(os.environ.get("SENTRY_DSN", "") or "").strip()
    if not dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration
    except Exception:
        return False

    environment = str(
        os.environ.get("SENTRY_ENVIRONMENT")
        or ("development" if debug else "production")
    ).strip()
    release = str(os.environ.get("SENTRY_RELEASE", "") or "").strip() or None
    traces_sample_rate = _env_float("SENTRY_TRACES_SAMPLE_RATE", 0.0)
    profiles_sample_rate = _env_float("SENTRY_PROFILES_SAMPLE_RATE", 0.0)
    send_default_pii = _env_bool("SENTRY_SEND_DEFAULT_PII", False)

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        send_default_pii=send_default_pii,
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
    )
    return True
