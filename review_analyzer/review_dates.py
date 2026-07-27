from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

_ISO_DATE_RE = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)")
_MONTH_DATE_RE = re.compile(
    r"\b("
    r"January|February|March|April|May|June|July|August|September|October|November|December"
    r")\s+(\d{1,2}),\s*(\d{4})\b",
    re.IGNORECASE,
)
_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def parse_comment_review_date(value: Any) -> date | None:
    """Parse supported raw comment date values into a normalized date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value or "").strip()
    if not text:
        return None

    iso_match = _ISO_DATE_RE.search(text)
    if iso_match:
        try:
            return datetime.strptime(iso_match.group(1), "%Y-%m-%d").date()
        except ValueError:
            return None

    month_match = _MONTH_DATE_RE.search(text)
    if not month_match:
        return None

    month = _MONTHS.get(month_match.group(1).lower())
    if month is None:
        return None

    try:
        return date(int(month_match.group(3)), month, int(month_match.group(2)))
    except ValueError:
        return None


def normalize_comment_review_date(value: Any) -> str | None:
    parsed = parse_comment_review_date(value)
    return parsed.isoformat() if parsed else None


def review_date_for_comment(comment: dict[str, Any]) -> date | None:
    for key in ("date_iso", "review_date", "date"):
        parsed = parse_comment_review_date(comment.get(key))
        if parsed:
            return parsed
    return None
