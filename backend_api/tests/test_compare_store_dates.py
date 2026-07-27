from __future__ import annotations

from datetime import date

from review_analyzer.compare_store import _filter_comments


def test_filter_comments_prefers_normalized_review_date_for_date_window() -> None:
    comments = [
        {
            "id": 1,
            "session_id": 10,
            "product_id": "Parent",
            "version": "V1",
            "content_hash": "h1",
            "date": "Reviewed in the United States on July 1, 2026",
            "review_date": date(2026, 7, 1),
        }
    ]

    filtered = _filter_comments(
        comments,
        {10: {"id": 10}},
        {
            "product_id": "Parent",
            "date_start": "2026-07-01",
            "date_end": "2026-07-31",
        },
    )

    assert [row["id"] for row in filtered] == [1]
