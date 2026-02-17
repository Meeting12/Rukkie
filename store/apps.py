from django.apps import AppConfig


class StoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store'

    def ready(self):
        # import signals to ensure image processing runs when ProductImage is saved
        try:
            from .media_layout import ensure_base_media_structure
            from . import signals  # noqa: F401
            ensure_base_media_structure()
        except Exception:
            pass

