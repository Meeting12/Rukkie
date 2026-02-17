from django.core.checks import Warning, register
from django.conf import settings

@register()
def sqlite_dev_warning(app_configs, **kwargs):
    errors = []
    try:
        default_db = settings.DATABASES.get('default', {})
        engine = default_db.get('ENGINE', '')
    except Exception:
        engine = ''

    if settings.DEBUG and 'sqlite3' in engine:
        msg = (
            'SQLite is in use while DEBUG=True. This is fine for quick local development, '
            'but Postgres is recommended for parity with production. Consider running Postgres locally '
            'via docker-compose to avoid migration/runtime surprises.'
        )
        hint = 'Run `docker compose up -d` to start a local Postgres, set DATABASE_URL, or run CI against Postgres.'
        errors.append(Warning(msg, hint=hint, id='store.W001'))
    return errors
