from pathlib import Path
from django.conf import settings
from django.utils.text import slugify


def _media_root() -> Path:
    root = getattr(settings, "MEDIA_ROOT", "")
    return Path(root) if root else Path("media")


def normalize_slug(value: str, fallback: str = "general") -> str:
    token = slugify(str(value or "").strip())
    return token or fallback


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_base_media_structure() -> None:
    root = _media_root()
    ensure_dir(root / "products")
    ensure_dir(root / "categories")
    ensure_dir(root / "hero")
    ensure_dir(root / "imports" / "csv")
    ensure_dir(root / "products" / "_shared")
    ensure_dir(root / "products" / "categories")


def category_media_paths(category_slug: str):
    root = _media_root()
    slug = normalize_slug(category_slug, fallback="uncategorized")
    return {
        "category_root": root / "categories" / slug,
        "product_root": root / "products" / "categories" / slug,
        "raw": root / "products" / "categories" / slug / "raw",
        "processed": root / "products" / "categories" / slug / "processed",
        "archive": root / "products" / "categories" / slug / "archive",
        "imports_csv": root / "imports" / "csv" / slug,
    }


def ensure_category_media_structure(category_slug: str):
    ensure_base_media_structure()
    paths = category_media_paths(category_slug)
    for path in paths.values():
        ensure_dir(path)
    return paths

