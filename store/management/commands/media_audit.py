from __future__ import annotations

import csv
from typing import Iterable

import requests
from django.core.management.base import BaseCommand

from store.email_react import get_public_site_url
from store.models import Category, HomeHeroSlide, ProductImage
from store.serializers import _resolve_image_url


def _absolute_url(value: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        return ""
    if cleaned.startswith("//"):
        return f"https:{cleaned}"
    if cleaned.startswith("/"):
        return f"{get_public_site_url()}{cleaned}"
    if cleaned.startswith("http://"):
        return f"https://{cleaned[len('http://'):]}"
    return cleaned


class Command(BaseCommand):
    help = "Audit product/category/hero media URLs and report missing or broken assets."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=int, default=12, help="HTTP timeout in seconds for each media probe.")
        parser.add_argument("--limit", type=int, default=0, help="Optional max number of rows per media type.")
        parser.add_argument("--output", type=str, default="", help="Optional CSV output path.")
        parser.add_argument(
            "--types",
            nargs="+",
            default=["products", "categories", "hero"],
            choices=["products", "categories", "hero"],
            help="Media groups to audit.",
        )

    def handle(self, *args, **options):
        timeout = max(3, int(options["timeout"] or 12))
        limit = max(0, int(options["limit"] or 0))
        requested_types = list(dict.fromkeys(options["types"] or ["products", "categories", "hero"]))

        rows: list[dict[str, str]] = []
        if "products" in requested_types:
            rows.extend(self._audit_products(limit=limit, timeout=timeout))
        if "categories" in requested_types:
            rows.extend(self._audit_categories(limit=limit, timeout=timeout))
        if "hero" in requested_types:
            rows.extend(self._audit_hero(limit=limit, timeout=timeout))

        broken_rows = [row for row in rows if row["status"] != "ok"]
        self.stdout.write(
            self.style.NOTICE(
                f"Audited {len(rows)} media row(s). Broken or missing: {len(broken_rows)}."
            )
        )
        if broken_rows:
            for row in broken_rows[:30]:
                self.stdout.write(
                    f"[{row['status']}] {row['kind']} #{row['object_id']} {row['label']} -> {row['url'] or '(empty)'} | {row['detail']}"
                )
        else:
            self.stdout.write(self.style.SUCCESS("No broken media rows found."))

        output_path = str(options.get("output") or "").strip()
        if output_path:
            with open(output_path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(
                    fh,
                    fieldnames=["kind", "object_id", "label", "status", "url", "detail"],
                )
                writer.writeheader()
                writer.writerows(rows)
            self.stdout.write(self.style.SUCCESS(f"CSV report written to {output_path}"))

    def _audit_products(self, *, limit: int, timeout: int) -> Iterable[dict[str, str]]:
        queryset = ProductImage.objects.select_related("product").order_by("product_id", "order", "id")
        if limit:
            queryset = queryset[:limit]
        for row in queryset:
            product_name = getattr(row.product, "name", f"Product #{row.product_id}")
            yield self._probe_row(
                kind="product",
                object_id=row.pk,
                label=product_name,
                raw_url=_resolve_image_url(getattr(row, "image", None), request=None),
                timeout=timeout,
            )

    def _audit_categories(self, *, limit: int, timeout: int) -> Iterable[dict[str, str]]:
        queryset = Category.objects.exclude(image="").exclude(image__isnull=True).order_by("id")
        if limit:
            queryset = queryset[:limit]
        for row in queryset:
            yield self._probe_row(
                kind="category",
                object_id=row.pk,
                label=row.name,
                raw_url=_resolve_image_url(getattr(row, "image", None), request=None),
                timeout=timeout,
            )

    def _audit_hero(self, *, limit: int, timeout: int) -> Iterable[dict[str, str]]:
        queryset = HomeHeroSlide.objects.exclude(image="").exclude(image__isnull=True).order_by("sort_order", "id")
        if limit:
            queryset = queryset[:limit]
        for row in queryset:
            yield self._probe_row(
                kind="hero",
                object_id=row.pk,
                label=row.title,
                raw_url=_resolve_image_url(getattr(row, "image", None), request=None),
                timeout=timeout,
            )

    def _probe_row(self, *, kind: str, object_id: int, label: str, raw_url: str, timeout: int) -> dict[str, str]:
        url = _absolute_url(raw_url)
        result = {
            "kind": kind,
            "object_id": str(object_id),
            "label": str(label or ""),
            "status": "ok",
            "url": url,
            "detail": "",
        }
        if not url:
            result["status"] = "missing_url"
            result["detail"] = "Resolver returned an empty URL."
            return result
        if "<cloud_name>" in url.lower() or "%3ccloud_name%3e" in url.lower():
            result["status"] = "placeholder_url"
            result["detail"] = "URL still contains placeholder Cloudinary values."
            return result
        if not url.startswith(("http://", "https://")):
            result["status"] = "relative_url"
            result["detail"] = "Resolver returned a non-absolute URL."
            return result
        try:
            response = requests.get(url, timeout=timeout, stream=True, allow_redirects=True, headers={"User-Agent": "Rukkie Media Audit/1.0"})
            try:
                content_type = str(response.headers.get("Content-Type") or "").lower()
                if response.status_code != 200:
                    result["status"] = f"http_{response.status_code}"
                    result["detail"] = f"HTTP {response.status_code}"
                elif content_type and not content_type.startswith("image/"):
                    result["status"] = "non_image"
                    result["detail"] = f"Unexpected content type: {content_type}"
            finally:
                response.close()
        except Exception as exc:
            result["status"] = "request_error"
            result["detail"] = f"{exc.__class__.__name__}: {exc}"
        return result
