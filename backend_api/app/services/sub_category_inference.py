"""Small category inference helpers for upload jobs.

This is intentionally conservative: it only maps clear product/category text to
supported sub_category names when the user-provided category is missing or not
present in taxonomy.
"""
from __future__ import annotations

from typing import Any

_SUB_CATEGORY_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("睫毛膏", ("睫毛膏", "mascara")),
)


def infer_sub_category_from_payload(
    payload: dict[str, Any],
    product_id: str = "",
) -> str | None:
    """Infer a supported sub_category from product/category text.

    Returns None when there is no high-confidence match.
    """
    fields = [
        product_id,
        payload.get("product_id"),
        payload.get("product_name"),
        payload.get("scraped_title"),
        payload.get("category"),
        payload.get("source_filename"),
    ]
    haystack = " ".join(str(value or "") for value in fields).lower()
    if not haystack.strip():
        return None

    for sub_category, aliases in _SUB_CATEGORY_ALIASES:
        if any(alias.lower() in haystack for alias in aliases):
            return sub_category
    return None
