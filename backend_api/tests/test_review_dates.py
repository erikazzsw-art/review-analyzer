from __future__ import annotations

from datetime import date, datetime

from review_analyzer.review_dates import normalize_comment_review_date, parse_comment_review_date


def test_parse_comment_review_date_supports_iso_values() -> None:
    assert normalize_comment_review_date("2026-07-01") == "2026-07-01"
    assert normalize_comment_review_date("2026-07-01T12:34:56Z") == "2026-07-01"
    assert parse_comment_review_date(datetime(2026, 7, 1, 12, 34)) == date(2026, 7, 1)


def test_parse_comment_review_date_supports_amazon_reviewed_text() -> None:
    assert (
        normalize_comment_review_date("Reviewed in the United States on July 1, 2026")
        == "2026-07-01"
    )
    assert (
        normalize_comment_review_date("Reviewed in Canada on February 29, 2024")
        == "2024-02-29"
    )


def test_parse_comment_review_date_leaves_unparseable_values_null() -> None:
    assert normalize_comment_review_date("") is None
    assert normalize_comment_review_date("Reviewed someday") is None
    assert normalize_comment_review_date("Reviewed in the United States on February 30, 2026") is None
