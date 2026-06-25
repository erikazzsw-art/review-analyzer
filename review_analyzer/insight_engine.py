from __future__ import annotations

import json
from collections import Counter
from typing import Any

from openai import APIError, APITimeoutError, AuthenticationError, OpenAI

from review_analyzer.analyzer import get_api_key


def build_results_insights(
    user_id: int,
    comments: list[dict[str, Any]],
    context: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build structured single-product insights from filtered comments."""
    heuristic_payload = _build_heuristic_results(comments, context)
    ai_payload = _build_ai_results_payload(user_id, comments, context)
    if ai_payload:
        merged = dict(heuristic_payload)
        for key, value in ai_payload.items():
            if key not in merged:
                continue
            if not isinstance(value, dict):
                continue
            existing = merged[key]
            for field, field_value in value.items():
                if field_value is None or field_value == "" or field_value == []:
                    continue
                existing[field] = field_value
            merged[key] = existing
        return merged
    return heuristic_payload


def build_compare_insights(
    user_id: int,
    objects: list[dict[str, Any]],
    context: dict[str, Any],
    focus_feature: str | None = None,
) -> dict[str, Any]:
    """Build the comparison matrix payload."""
    enriched_objects = []
    for obj in objects:
        heuristics = _build_compare_object_heuristic(obj, focus_feature)
        ai_payload = _build_compare_object_ai(user_id, obj, focus_feature)
        enriched_objects.append({**heuristics, **(ai_payload or {})})
    return {
        "title": context.get("title", "对比分析"),
        "focus_feature": focus_feature,
        "objects": enriched_objects,
    }


def _build_heuristic_results(comments: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    positive = [comment for comment in comments if comment.get("sentiment") == "positive"]
    negative = [comment for comment in comments if comment.get("sentiment") == "negative"]
    neutral = [comment for comment in comments if comment.get("sentiment") not in ("positive", "negative")]
    positive_tags = _top_tag_rows(positive, "highlight_tag")
    negative_tags = _top_tag_rows(negative, "issue_tag")

    total = len(comments)
    pos_rate = round(len(positive) / total * 100, 1) if total else 0.0
    neg_rate = round(len(negative) / total * 100, 1) if total else 0.0

    consumer_summary = _build_consumer_profile_summary(positive_tags, negative_tags)
    evidence = _sample_quotes(comments, limit=5)
    experience_summary = (
        f"Out of {total} reviews, {pos_rate}% are positive and {neg_rate}% are negative. "
        f"Top strength: {positive_tags[0]['tag'] if positive_tags else 'N/A'}. "
        f"Top issue: {negative_tags[0]['tag'] if negative_tags else 'N/A'}."
    )
    purchase_summary = (
        f"Based on {len(positive)} positive reviews, the main purchase drivers are: "
        f"{', '.join(row['tag'] for row in positive_tags[:3]) or 'general product value'}."
    )
    unmet_summary = (
        f"Based on {len(negative)} negative reviews, the key unmet needs are: "
        f"{', '.join(row['tag'] for row in negative_tags[:3]) or 'no clear pattern'}."
    )
    recommendations = _build_recommendations(positive_tags, negative_tags, context)

    return {
        "consumer_profile": {
            "summary": consumer_summary,
            "rows": [
                {"label": "Review distribution", "detail": f"Positive {pos_rate}% · Negative {neg_rate}% · Neutral {round(len(neutral) / total * 100, 1) if total else 0}%"},
                {"label": "Core audience focus", "detail": _join_tag_names(positive_tags[:3], negative_tags[:2])},
                {"label": "Key insight", "detail": consumer_summary},
            ],
            "evidence": evidence,
        },
        "user_experience": {
            "summary": experience_summary,
            "positive": positive_tags[:10] or [{"tag": "No clear strength", "pct": 0.0, "reason": "No stable positive tag found."}],
            "negative": negative_tags[:10] or [{"tag": "No clear friction", "pct": 0.0, "reason": "No stable negative tag found."}],
        },
        "purchase_motives": {
            "summary": purchase_summary,
            "rows": positive_tags[:10] or [{"tag": "Great value", "pct": 0.0, "reason": "No clear buying motive extracted."}],
        },
        "unmet_needs": {
            "summary": unmet_summary,
            "rows": negative_tags[:10] or [{"tag": "Quality improvement", "pct": 0.0, "reason": "No clear unmet need extracted."}],
        },
        "recommendations": {
            "summary": "Use both complaints and strengths to align product, listing, and communication decisions.",
            "rows": [{"label": f"Recommendation {index + 1}", "detail": item} for index, item in enumerate(recommendations)],
        },
    }


def _build_compare_object_heuristic(object_payload: dict[str, Any], focus_feature: str | None) -> dict[str, Any]:
    product_info = object_payload.get("product_info", {})
    positive_tags = object_payload.get("positive_tags", [])
    negative_tags = object_payload.get("negative_tags", [])
    review_count = int(object_payload.get("review_count", 0))

    feature_hint = focus_feature.strip() if focus_feature else ""
    if feature_hint:
        positive_tags = [row for row in positive_tags if feature_hint.lower() in row["tag"].lower()] or positive_tags
        negative_tags = [row for row in negative_tags if feature_hint.lower() in row["tag"].lower()] or negative_tags

    top_positive = _join_tag_names(positive_tags[:3], [])
    top_negative = _join_tag_names([], negative_tags[:3])
    return {
        "product_info": {
            "商品名称": str(product_info.get("name") or object_payload.get("label") or "--"),
            "产品图": str(product_info.get("image") or "--"),
            "品牌": str(product_info.get("brand") or "--"),
            "ASIN": str(product_info.get("asin") or "--"),
            "价格": str(product_info.get("price") or "--"),
            "上架时间": str(product_info.get("launched_at") or "--"),
            "星级": str(product_info.get("rating") or "--"),
            "评论数": str(review_count or "--"),
        },
        "consumer_profile": {
            "人群特征": (
                f"Likely value-focused shoppers paying attention to {top_positive or 'overall product fundamentals'}."
            ),
            "使用时刻": "Not enough direct timing evidence in the selected comments.",
            "使用地点": "Not enough direct location evidence in the selected comments.",
            "行为": f"Customers repeatedly mention {top_negative or top_positive or 'core product usage'} when describing usage.",
        },
        "experience": {
            "正向观点": top_positive or "No stable positive viewpoint detected.",
            "负向观点": top_negative or "No stable negative viewpoint detected.",
        },
        "purchase_motives": top_positive or "Customers mainly buy for general product value and practicality.",
        "unmet_needs": top_negative or "No strong unmet need signal was found in the selected comments.",
    }


def _build_ai_results_payload(
    user_id: int,
    comments: list[dict[str, Any]],
    context: dict[str, Any],
) -> dict[str, Any] | None:
    if not comments:
        return None
    positive_tags = _top_tag_rows([c for c in comments if c.get("sentiment") == "positive"], "highlight_tag")
    negative_tags = _top_tag_rows([c for c in comments if c.get("sentiment") == "negative"], "issue_tag")
    prompt = {
        "context": context,
        "review_count": len(comments),
        "representative_comments": _serialize_comments(comments[:15]),
        "positive_tags": positive_tags,
        "negative_tags": negative_tags,
    }
    try:
        client = OpenAI(
            api_key=get_api_key(user_id),
            base_url="https://api.deepseek.com/v1",
            timeout=30.0,
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an ecommerce review analyst. Analyze the provided review data and return a JSON object with exactly these keys:\n"
                        "1. consumer_profile: {summary: string, rows: [{label: string, detail: string}], evidence: [string]}\n"
                        "2. user_experience: {summary: string, positive: [{tag: string, pct: number, reason: string}], negative: [{tag: string, pct: number, reason: string}]}\n"
                        "3. purchase_motives: {summary: string, rows: [{tag: string, pct: number, reason: string}]}\n"
                        "4. unmet_needs: {summary: string, rows: [{tag: string, pct: number, reason: string}]}\n"
                        "5. recommendations: {summary: string, rows: [{label: string, detail: string}]}\n\n"
                        "Rules:\n"
                        "- CRITICAL: The 'tag' field in positive/negative/purchase_motives/unmet_needs MUST use the EXACT tag names from the provided positive_tags and negative_tags arrays. Do NOT rephrase, rename or create new tag names.\n"
                        "- positive and negative arrays must have up to 10 items each, sorted by pct descending\n"
                        "- pct is the percentage of reviews mentioning that tag (0-100)\n"
                        "- reason must quote or closely paraphrase a real review as evidence\n"
                        "- recommendations should be actionable (Product/Operations/Listing/QA)\n"
                        "- Write all values in concise English\n"
                        "- Return ONLY the JSON object, no markdown"
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            temperature=0.2,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )
        payload = json.loads(response.choices[0].message.content.strip())
        if not isinstance(payload, dict):
            return None
        return _validate_ai_payload(payload)
    except (APIError, APITimeoutError, AuthenticationError, json.JSONDecodeError, ValueError, TypeError):
        return None


def _validate_ai_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Validate AI output structure, returning None for invalid modules."""
    expected_keys = {"consumer_profile", "user_experience", "purchase_motives", "unmet_needs", "recommendations"}
    validated: dict[str, Any] = {}
    for key in expected_keys:
        module = payload.get(key)
        if not isinstance(module, dict):
            continue
        if key == "user_experience":
            pos = module.get("positive")
            neg = module.get("negative")
            if not isinstance(pos, list) or not isinstance(neg, list):
                continue
            module["positive"] = [_normalize_tag_row(r) for r in pos[:10] if isinstance(r, dict)]
            module["negative"] = [_normalize_tag_row(r) for r in neg[:10] if isinstance(r, dict)]
        elif key in ("purchase_motives", "unmet_needs"):
            rows = module.get("rows")
            if not isinstance(rows, list):
                continue
            module["rows"] = [_normalize_tag_row(r) for r in rows[:10] if isinstance(r, dict)]
        elif key == "recommendations":
            rows = module.get("rows")
            if not isinstance(rows, list):
                continue
            module["rows"] = [r for r in rows if isinstance(r, dict) and r.get("detail")]
        validated[key] = module
    return validated if validated else None


def _normalize_tag_row(row: dict[str, Any]) -> dict[str, Any]:
    """Ensure tag rows have consistent field names."""
    return {
        "tag": str(row.get("tag") or row.get("label") or row.get("name") or ""),
        "pct": float(row.get("pct") or row.get("percentage") or row.get("percent") or 0),
        "reason": str(row.get("reason") or row.get("evidence") or row.get("detail") or row.get("example") or ""),
    }


def _build_compare_object_ai(
    user_id: int,
    object_payload: dict[str, Any],
    focus_feature: str | None,
) -> dict[str, Any] | None:
    comments = object_payload.get("comments", [])
    if not comments:
        return None
    prompt = {
        "label": object_payload.get("label"),
        "description": object_payload.get("description"),
        "focus_feature": focus_feature or "",
        "review_count": object_payload.get("review_count", 0),
        "positive_tags": object_payload.get("positive_tags", []),
        "negative_tags": object_payload.get("negative_tags", []),
        "representative_comments": _serialize_comments(comments[:8]),
    }
    try:
        client = OpenAI(
            api_key=get_api_key(user_id),
            base_url="https://api.deepseek.com/v1",
            timeout=30.0,
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return compact JSON for a comparison matrix. "
                        "Use keys product_info, consumer_profile, experience, purchase_motives, unmet_needs. "
                        "Write all values in concise English."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            temperature=0.2,
            max_tokens=1800,
            response_format={"type": "json_object"},
        )
        payload = json.loads(response.choices[0].message.content.strip())
        return payload if isinstance(payload, dict) else None
    except (APIError, APITimeoutError, AuthenticationError, json.JSONDecodeError, ValueError, TypeError):
        return None


def _serialize_comments(comments: list[dict[str, Any]]) -> list[dict[str, str]]:
    serialized: list[dict[str, str]] = []
    for comment in comments:
        serialized.append(
            {
                "date": str(comment.get("date") or ""),
                "content": str(comment.get("content") or "")[:220],
                "issue_tag": str(comment.get("issue_tag") or ""),
                "highlight_tag": str(comment.get("highlight_tag") or ""),
                "sentiment": str(comment.get("sentiment") or ""),
            }
        )
    return serialized


def _top_tag_rows(comments: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    examples: dict[str, str] = {}
    pool_size = len(comments)
    for comment in comments:
        content = str(comment.get("content") or "").strip()
        seen: set[str] = set()
        for raw_tag in str(comment.get(field) or "").split(","):
            tag = raw_tag.strip()
            if not tag or tag in seen:
                continue
            seen.add(tag)
            counter[tag] += 1
            if tag not in examples and content:
                examples[tag] = content[:160]
    rows: list[dict[str, Any]] = []
    for tag, count in counter.most_common(10):
        pct = round(count / pool_size * 100, 1) if pool_size else 0.0
        rows.append(
            {
                "tag": tag,
                "pct": pct,
                "reason": examples.get(tag) or "No representative comment found.",
            }
        )
    return rows


def _build_consumer_profile_summary(
    positive_tags: list[dict[str, Any]],
    negative_tags: list[dict[str, Any]],
) -> str:
    positive_hint = ", ".join(row["tag"] for row in positive_tags[:2])
    negative_hint = ", ".join(row["tag"] for row in negative_tags[:2])
    if positive_hint and negative_hint:
        return (
            f"The audience values {positive_hint} but is sensitive to problems around {negative_hint}."
        )
    if positive_hint:
        return f"The audience is mainly driven by {positive_hint} and overall product practicality."
    if negative_hint:
        return f"The audience is highly sensitive to friction around {negative_hint}."
    return "The selected reviews do not contain a strong enough profile signal yet."


def _sample_quotes(comments: list[dict[str, Any]], limit: int = 3) -> list[str]:
    quotes: list[str] = []
    for comment in comments:
        content = str(comment.get("content") or "").strip()
        if content:
            quotes.append(content[:180])
        if len(quotes) >= limit:
            break
    return quotes


def _build_recommendations(
    positive_tags: list[dict[str, Any]],
    negative_tags: list[dict[str, Any]],
    context: dict[str, Any],
) -> list[str]:
    top_negative = negative_tags[0]["tag"] if negative_tags else "the main friction point"
    top_positive = positive_tags[0]["tag"] if positive_tags else "the current product strength"
    product_id = context.get("product_id", "this product")
    return [
        f"Product: Prioritize fixes around {top_negative} for {product_id}.",
        f"Operations: Use {top_positive} as the lead proof point in review-based communication.",
        f"Listing: Clarify expectations and reduce confusion around {top_negative}.",
        f"Marketing: Build messaging around {top_positive} with direct customer wording.",
    ]


def _join_tag_names(
    positive_tags: list[dict[str, Any]],
    negative_tags: list[dict[str, Any]],
) -> str:
    names = [row["tag"] for row in positive_tags] + [row["tag"] for row in negative_tags]
    return ", ".join(names) if names else "No stable theme found."
