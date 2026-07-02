"""评论标签聚合原语。

供"问评论"(qa_handlers) 和"对比分析"(compare_store) 共用。
所有函数都是纯数据处理，不依赖数据库连接。
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any, TypedDict


class TagStat(TypedDict):
    tag: str
    count: int
    pct: float


class RepresentativeReview(TypedDict):
    rating: Any
    date: Any
    content: str
    issue_tag: str
    highlight_tag: str


def top_tags(
    comments: list[dict[str, Any]],
    tag_field: str,
    top_n: int = 8,
) -> list[TagStat]:
    """聚合 comments 中某个逗号分隔标签字段的 Top-N 与占比。

    同一条评论对同一 tag 只计一次；pct 相对于 comments 总数。
    """
    counter: Counter[str] = Counter()
    for comment in comments:
        seen: set[str] = set()
        for raw in str(comment.get(tag_field) or "").split(","):
            tag = raw.strip()
            if tag and tag not in seen:
                seen.add(tag)
                counter[tag] += 1

    pool_size = len(comments)
    results: list[TagStat] = []
    for tag, count in counter.most_common(top_n):
        pct = round((count / pool_size) * 100, 1) if pool_size else 0.0
        results.append({"tag": tag, "count": count, "pct": pct})
    return results


def _to_date_safe(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[: len(fmt)], fmt).date()
        except ValueError:
            continue
    return None


def pick_representative_reviews(
    comments: list[dict[str, Any]],
    top_tags_result: list[TagStat],
    limit: int = 3,
    preferred_top: int = 3,
) -> list[RepresentativeReview]:
    """从 comments 中挑选代表性评论：优先命中 Top-N 里前 preferred_top 个标签，然后按日期倒序。

    默认 limit=3、preferred_top=3，与旧 compare_store._pick_representative_reviews 行为一致。
    """
    if not comments:
        return []

    preferred_tags = {item["tag"] for item in top_tags_result[:preferred_top]}

    def sort_key(comment: dict[str, Any]) -> tuple[int, date, int]:
        raw_tags = ",".join(
            [
                str(comment.get("issue_tag") or "").strip(),
                str(comment.get("highlight_tag") or "").strip(),
            ]
        )
        tag_hit = 1 if any(tag in raw_tags for tag in preferred_tags) else 0
        return (
            tag_hit,
            _to_date_safe(comment.get("date")) or date.min,
            int(comment.get("id") or 0),
        )

    picked = sorted(comments, key=sort_key, reverse=True)[:limit]
    return [
        {
            "rating": comment.get("rating"),
            "date": comment.get("date"),
            "content": str(comment.get("content") or "").strip(),
            "issue_tag": str(comment.get("issue_tag") or "").strip(),
            "highlight_tag": str(comment.get("highlight_tag") or "").strip(),
        }
        for comment in picked
        if str(comment.get("content") or "").strip()
    ]


def pick_citations_by_tags(
    comments: list[dict[str, Any]],
    tag_field: str,
    top_tags_result: list[TagStat],
    per_tag: int = 2,
    max_total: int = 10,
) -> list[dict[str, Any]]:
    """为 QA 场景挑选带完整字段的原始评论作为 citations。

    与 pick_representative_reviews 的区别：
    - 返回原始 comment dict（含 id/product_id/session_id 等，供前端定位）
    - 按 top_tags 顺序，每个 tag 挑 per_tag 条；不重复
    - 挑不满时补长评论；总数不超过 max_total
    """
    if not comments or not top_tags_result:
        return []

    picked_ids: set[int] = set()
    result: list[dict[str, Any]] = []

    for tag_stat in top_tags_result:
        tag = tag_stat["tag"]
        if not tag:
            continue
        matches = []
        for comment in comments:
            cid = comment.get("id")
            if cid is None or cid in picked_ids:
                continue
            raw = str(comment.get(tag_field) or "")
            tags_in_comment = {t.strip() for t in raw.split(",") if t.strip()}
            if tag in tags_in_comment:
                matches.append(comment)

        matches.sort(
            key=lambda c: (
                _to_date_safe(c.get("date")) or date.min,
                len(str(c.get("content") or "")),
            ),
            reverse=True,
        )
        for comment in matches[:per_tag]:
            result.append(comment)
            picked_ids.add(comment["id"])
            if len(result) >= max_total:
                return result

    return result
