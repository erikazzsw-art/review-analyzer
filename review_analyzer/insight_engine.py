from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from threading import Lock
from typing import Any

from backend_api.app.services.specific_issue import (
    build_customer_highlight_rows,
    build_specific_issue_rows,
    customer_highlight_tags_for_comment,
    customer_issue_tags_for_comment,
)

_LOGGER = logging.getLogger(__name__)

_RESULTS_AI_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="results-ai")
_RESULTS_AI_CACHE: dict[str, tuple[float, dict[str, Any] | None]] = {}
_RESULTS_AI_INFLIGHT: set[str] = set()
_RESULTS_AI_LOCK = Lock()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _results_ai_enabled() -> bool:
    return _env_bool("RESULTS_AI_ENHANCEMENT_ENABLED", False)


def _results_ai_wait_timeout_seconds() -> float:
    return max(0.0, _env_float("RESULTS_AI_ENHANCEMENT_TIMEOUT_SECONDS", 0.25))


def _results_ai_provider_timeout_seconds() -> float:
    return max(0.1, _env_float("RESULTS_AI_PROVIDER_TIMEOUT_SECONDS", 1.0))


def _results_ai_cache_ttl_seconds(payload: dict[str, Any] | None) -> float:
    if payload:
        return max(1.0, _env_float("RESULTS_AI_CACHE_TTL_SECONDS", 60 * 30))
    return max(1.0, _env_float("RESULTS_AI_FAILURE_CACHE_TTL_SECONDS", 60.0))


def _results_ai_disabled_providers() -> set[str]:
    raw = os.getenv("RESULTS_AI_DISABLED_PROVIDERS", "deepseek")
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _results_ai_max_model_attempts() -> int:
    return max(1, _env_int("RESULTS_AI_MAX_MODEL_ATTEMPTS", 1))


def _clear_results_ai_cache() -> None:
    with _RESULTS_AI_LOCK:
        _RESULTS_AI_CACHE.clear()
        _RESULTS_AI_INFLIGHT.clear()


def build_results_insights(
    user_id: int,
    comments: list[dict[str, Any]],
    context: dict[str, Any],
    locale: str = "en",
) -> dict[str, dict[str, Any]]:
    """Build structured single-product insights from filtered comments.

    Results AI text enhancement is optional and isolated; deterministic
    customer-label statistics are always built from local occurrences first.
    """
    heuristic_payload = _build_heuristic_results(comments, context, locale=locale)
    try:
        ai_payload = _build_ai_results_payload(user_id, comments, context, locale=locale)
    except Exception:
        _LOGGER.exception("results AI enhancement isolated failure; using heuristic payload")
        ai_payload = None
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
                # AI only enhances text fields; tag arrays stay from heuristic counting
                if field in ("positive", "negative", "rows"):
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
    locale: str = "en",
) -> dict[str, Any]:
    """Build the comparison matrix payload."""
    enriched_objects = []
    for obj in objects:
        heuristics = _build_compare_object_heuristic(obj, focus_feature)
        ai_payload = _build_compare_object_ai(user_id, obj, focus_feature, locale=locale)
        enriched_objects.append({**heuristics, **(ai_payload or {})})
    return {
        "title": context.get("title", "对比分析"),
        "focus_feature": focus_feature,
        "objects": enriched_objects,
    }


def _build_heuristic_results(
    comments: list[dict[str, Any]],
    context: dict[str, Any],
    locale: str = "en",
) -> dict[str, dict[str, Any]]:
    positive = [comment for comment in comments if comment.get("sentiment") == "positive"]
    negative = [comment for comment in comments if comment.get("sentiment") == "negative"]
    positive_tags = build_customer_highlight_rows(comments, locale=locale)
    negative_tags = build_specific_issue_rows(comments, locale=locale)

    total = len(comments)
    pos_rate = round(len(positive) / total * 100, 1) if total else 0.0
    neg_rate = round(len(negative) / total * 100, 1) if total else 0.0

    consumer_summary = _build_consumer_profile_summary(comments)
    evidence = _sample_quotes(comments, limit=5)
    experience_summary = (
        f"Out of {total} reviews, {pos_rate}% are positive and {neg_rate}% are negative. "
        f"Top strength: {positive_tags[0]['tag'] if positive_tags else 'N/A'}. "
        f"Top issue: {negative_tags[0]['tag'] if negative_tags else 'N/A'}."
    )
    purchase_summary = (
        f"Based on customer label occurrences across {total} reviews, the main purchase drivers are: "
        f"{', '.join(row['tag'] for row in positive_tags[:3]) or 'general product value'}."
    )
    unmet_summary = (
        f"Based on customer label occurrences across {total} reviews, the key unmet needs are: "
        f"{', '.join(row['tag'] for row in negative_tags[:3]) or 'no clear pattern'}."
    )
    recommendations = _build_recommendations(positive_tags, negative_tags, context)

    return {
        "consumer_profile": {
            "summary": consumer_summary,
            "rows": [
                {"label": "Demographics", "detail": _infer_demographics_heuristic(comments)},
                {"label": "Interests & Context", "detail": _infer_interests_heuristic(comments)},
                {"label": "Purchase Behavior", "detail": _infer_behavior_heuristic(comments)},
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
    locale: str = "en",
) -> dict[str, Any] | None:
    if not comments:
        return None
    positive_tags = build_customer_highlight_rows(comments, locale=locale)
    negative_tags = build_specific_issue_rows(comments, locale=locale)
    prompt = {
        "context": context,
        "review_count": len(comments),
        "representative_comments": _serialize_comments(comments[:15], locale=locale),
        "positive_tags": positive_tags,
        "negative_tags": negative_tags,
    }
    cache_key = _results_ai_cache_key(
        user_id=user_id,
        prompt=prompt,
        locale=locale,
    )
    cached = _get_results_ai_cache(cache_key)
    if cached is not _CACHE_MISS:
        return cached

    if not _results_ai_enabled():
        return None

    with _RESULTS_AI_LOCK:
        if cache_key in _RESULTS_AI_INFLIGHT:
            _LOGGER.info("results AI enhancement already in flight; using heuristic payload")
            return None
        _RESULTS_AI_INFLIGHT.add(cache_key)

    future = _RESULTS_AI_EXECUTOR.submit(_call_ai_results_payload, prompt, locale)
    future.add_done_callback(lambda done: _store_results_ai_future(cache_key, done))

    wait_timeout = _results_ai_wait_timeout_seconds()
    if wait_timeout <= 0:
        _LOGGER.info("results AI enhancement scheduled in background; using heuristic payload")
        return None

    try:
        return future.result(timeout=wait_timeout)
    except FutureTimeoutError:
        _put_results_ai_cache(cache_key, None)
        _LOGGER.warning(
            "results AI enhancement timed out after %.2fs; using heuristic payload",
            wait_timeout,
        )
        return None


_CACHE_MISS = object()


def _results_ai_cache_key(
    *,
    user_id: int,
    prompt: dict[str, Any],
    locale: str,
) -> str:
    raw = json.dumps(
        {
            "user_id": user_id,
            "locale": locale,
            "prompt": prompt,
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _get_results_ai_cache(cache_key: str) -> dict[str, Any] | None | object:
    with _RESULTS_AI_LOCK:
        cached = _RESULTS_AI_CACHE.get(cache_key)
    if not cached:
        return _CACHE_MISS
    created_at, payload = cached
    if time.time() - created_at > _results_ai_cache_ttl_seconds(payload):
        with _RESULTS_AI_LOCK:
            _RESULTS_AI_CACHE.pop(cache_key, None)
        return _CACHE_MISS
    return payload


def _put_results_ai_cache(cache_key: str, payload: dict[str, Any] | None) -> None:
    with _RESULTS_AI_LOCK:
        _RESULTS_AI_CACHE[cache_key] = (time.time(), payload)


def _store_results_ai_future(
    cache_key: str,
    future: Future[dict[str, Any] | None],
) -> None:
    try:
        payload = future.result()
        _put_results_ai_cache(cache_key, payload)
    except Exception:
        _LOGGER.exception("results AI enhancement background failure; cached empty fallback")
        _put_results_ai_cache(cache_key, None)
    finally:
        with _RESULTS_AI_LOCK:
            _RESULTS_AI_INFLIGHT.discard(cache_key)


def _call_ai_results_payload(prompt: dict[str, Any], locale: str) -> dict[str, Any] | None:
    try:
        from backend_api.app.services.llm_router import router_completion

        response, model_name = router_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an ecommerce review analyst. Analyze the provided review data and return a JSON object with exactly these keys:\n"
                        "1. consumer_profile: {summary: string, rows: [{label: string, detail: string}], evidence: [string]}\n"
                        "   - summary: One sentence describing WHO the buyers are and their life context (no product quality judgments)\n"
                        "   - rows MUST have exactly 3 items with these labels:\n"
                        "     {label: \"Demographics\", detail: \"Who is buying? Infer roles, family status, life stage (e.g. parents with young children, college students, first-time homeowners)\"}\n"
                        "     {label: \"Interests & Context\", detail: \"What interests them? What scenario triggers the purchase? (e.g. children's room decor, home office setup, space-saving)\"}\n"
                        "     {label: \"Purchase Behavior\", detail: \"How do they decide and use? (e.g. compare on price, buy on deals, self-assemble, prefer bundles)\"}\n"
                        "   - evidence: 2-3 quotes revealing buyer identity or context, NOT product opinions\n"
                        "   - IMPORTANT: consumer_profile describes THE PEOPLE (like Facebook Ads audience targeting), NOT the product. No product strengths/weaknesses/tags here.\n"
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
            locale=locale,
            disabled_providers=_results_ai_disabled_providers(),
            request_timeout=_results_ai_provider_timeout_seconds(),
            max_model_attempts=_results_ai_max_model_attempts(),
        )
        payload = json.loads(response.choices[0].message.content.strip())
        if not isinstance(payload, dict):
            _LOGGER.warning("results AI enhancement returned non-object payload via %s", model_name)
            return None
        validated = _validate_ai_payload(payload)
        if validated:
            _LOGGER.info("results AI enhancement succeeded via %s", model_name)
        else:
            _LOGGER.warning("results AI enhancement returned invalid module shape via %s", model_name)
        return validated
    except (json.JSONDecodeError, ValueError, TypeError, RuntimeError) as exc:
        _LOGGER.warning("results AI enhancement failed; using heuristic payload: %s", exc)
        return None
    except Exception:
        _LOGGER.exception("results AI enhancement unexpected failure; using heuristic payload")
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
    locale: str = "en",
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
        "representative_comments": _serialize_comments(comments[:8], locale=locale),
    }
    try:
        from backend_api.app.services.llm_router import router_completion

        response, _model_name = router_completion(
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
            locale=locale,
        )
        payload = json.loads(response.choices[0].message.content.strip())
        return payload if isinstance(payload, dict) else None
    except (json.JSONDecodeError, ValueError, TypeError, RuntimeError):
        return None


def _serialize_comments(comments: list[dict[str, Any]], locale: str = "en") -> list[dict[str, str]]:
    serialized: list[dict[str, str]] = []
    for comment in comments:
        serialized.append(
            {
                "date": str(comment.get("date") or ""),
                "content": str(comment.get("content") or "")[:220],
                "issue_tag": ", ".join(customer_issue_tags_for_comment(comment, locale=locale)),
                "highlight_tag": ", ".join(customer_highlight_tags_for_comment(comment, locale=locale)),
                "sentiment": str(comment.get("sentiment") or ""),
            }
        )
    return serialized


def _has_aspect_evidence(comment: dict[str, Any], tag: str) -> bool:
    """Check if comment has direct LLM evidence for the given aspect tag.

    Validates that evidence_span actually appears in the comment's content,
    which filters out cluster-propagated reviews (they inherit aspects from
    the representative but the evidence text won't match their own content).
    """
    aj = comment.get("aspects_json")
    if not isinstance(aj, dict):
        return False
    if aj.get("cluster_propagated"):
        return False
    aspects = aj.get("aspects")
    if not isinstance(aspects, list):
        return False
    content = str(comment.get("content") or "")
    norm = tag.lower().replace(" ", "_")
    return any(
        (a.get("key") or "").lower().replace(" ", "_") == norm
        and a.get("evidence_span")
        and a["evidence_span"] in content
        for a in aspects
    )


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
            if tag not in examples and content and _has_aspect_evidence(comment, tag):
                examples[tag] = content[:160]
    # Fallback: if no verified example found, use first available
    for comment in comments:
        content = str(comment.get("content") or "").strip()
        if not content:
            continue
        for raw_tag in str(comment.get(field) or "").split(","):
            tag = raw_tag.strip()
            if tag and tag not in examples:
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


def _build_consumer_profile_summary(comments: list[dict[str, Any]]) -> str:
    """Generate a one-sentence audience description from review text (people-focused, no product judgments)."""
    if not comments:
        return "Not enough reviews to build an audience profile."
    return "Review-based audience profile — see rows below for demographics, interests, and purchase behavior."


def _infer_demographics_heuristic(comments: list[dict[str, Any]]) -> str:
    """Extract buyer identity signals from review text."""
    keywords_map = {
        "parent": ["kid", "kids", "child", "children", "son", "daughter", "boy", "girl", "toddler", "baby"],
        "gift buyer": ["gift", "present", "birthday", "christmas"],
        "first-time buyer": ["first time", "first purchase", "never bought"],
        "repeat buyer": ["bought again", "second time", "reorder", "repurchase"],
        "budget-conscious": ["price", "cheap", "affordable", "budget", "deal", "value for money"],
        "professional": ["office", "work", "business", "professional"],
        "student": ["dorm", "college", "university", "student", "school"],
    }
    signals: dict[str, int] = {}
    for comment in comments:
        content = str(comment.get("content") or "").lower()
        for label, triggers in keywords_map.items():
            if any(t in content for t in triggers):
                signals[label] = signals.get(label, 0) + 1
    if not signals:
        return "General consumers — no strong demographic signal in reviews."
    top = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:3]
    return ", ".join(f"{label.title()} ({count} mentions)" for label, count in top)


def _infer_interests_heuristic(comments: list[dict[str, Any]]) -> str:
    """Extract interest and context signals from review text."""
    keywords_map = {
        "home decor": ["room", "bedroom", "living room", "decor", "furniture", "house", "apartment"],
        "space-saving": ["small space", "compact", "space-saving", "small room", "tiny"],
        "tech features": ["usb", "led", "light", "bluetooth", "charging", "smart"],
        "outdoor use": ["outdoor", "garden", "patio", "camping", "travel"],
        "fitness": ["gym", "workout", "exercise", "fitness", "yoga"],
        "kids' use": ["kid", "kids", "child", "children", "playroom", "nursery"],
        "pet owners": ["dog", "cat", "pet"],
    }
    signals: dict[str, int] = {}
    for comment in comments:
        content = str(comment.get("content") or "").lower()
        for label, triggers in keywords_map.items():
            if any(t in content for t in triggers):
                signals[label] = signals.get(label, 0) + 1
    if not signals:
        return "General product interest — no strong contextual signal in reviews."
    top = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:3]
    return ", ".join(f"{label.title()} ({count} mentions)" for label, count in top)


def _infer_behavior_heuristic(comments: list[dict[str, Any]]) -> str:
    """Extract purchase and usage behavior signals from review text."""
    keywords_map = {
        "self-assembly": ["assemble", "assembly", "put together", "build it", "instructions"],
        "price comparison": ["compare", "compared", "cheaper", "better deal", "alternative"],
        "impulse/deal buy": ["prime day", "sale", "discount", "deal", "coupon", "black friday"],
        "gift purchase": ["gift", "present", "for my", "for her", "for him"],
        "replacement buy": ["replace", "replacement", "broke", "old one", "upgrade"],
        "bundle preference": ["set", "bundle", "all-in-one", "package", "combo"],
    }
    signals: dict[str, int] = {}
    for comment in comments:
        content = str(comment.get("content") or "").lower()
        for label, triggers in keywords_map.items():
            if any(t in content for t in triggers):
                signals[label] = signals.get(label, 0) + 1
    if not signals:
        return "Standard purchase behavior — no distinctive pattern detected in reviews."
    top = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:3]
    return ", ".join(f"{label.title()} ({count} mentions)" for label, count in top)


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
