from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date, datetime
from typing import Any

import psycopg2.extras
from openai import APIError, APITimeoutError, AuthenticationError, OpenAI

from review_analyzer.analyzer import get_api_key
from review_analyzer.database import get_comments, get_connection, get_sessions
from review_analyzer.insight_engine import build_results_insights

COMPARE_TYPE_LABELS = {
    "same_product_time": "同产品时间对比",
    "same_product_version": "同产品版本对比",
    "same_parent_variants": "同父体变体对比",
    "multi_product": "多产品横向对比",
    "custom": "自定义对比",
}


def build_compare_group_specs(
    user_id: int,
    compare_type: str,
    session_ids: list[int],
    product_id: str | None,
) -> list[dict[str, Any]]:
    sessions = get_sessions(user_id, product_id=product_id)
    session_lookup = {int(session["id"]): session for session in sessions}
    selected_sessions: list[dict[str, Any]] = [
        session_lookup.get(int(session_id))
        for session_id in session_ids
        if session_lookup.get(int(session_id))
    ]

    if not selected_sessions:
        if compare_type == "same_product_version" and sessions:
            seen_versions: set[str] = set()
            for session in sessions:
                version = str(session.get("version") or "V1")
                if version in seen_versions:
                    continue
                seen_versions.add(version)
                selected_sessions.append(session)
                if len(selected_sessions) >= 5:
                    break
        elif compare_type == "same_product_time" and sessions:
            selected_sessions = sessions[:2]
        else:
            selected_sessions = sessions[:5]

    if len(selected_sessions) < 2 and sessions:
        selected_sessions = sessions[:2]

    groups: list[dict[str, Any]] = []
    for session in selected_sessions[:5]:
        if not session:
            continue
        groups.append(
            {
                "label": str(session.get("custom_title") or session.get("auto_title") or session.get("version") or session["id"]),
                "description": f"{session.get('product_id')} · {session.get('version')} · {session.get('created_at')}",
                "session_ids": [int(session["id"])],
                "product_id": str(session.get("product_id") or ""),
                "versions": [str(session.get("version") or "V1")],
                "product_ref_id": session.get("product_ref_id"),
                "variant_ref_id": session.get("variant_ref_id"),
            }
        )

    return groups


def build_compare_specs_from_filters(
    user_id: int,
    compare_type: str,
    filter_groups: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """V2 specs builder driven by product / version / review-date filters.

    Each ``filter_groups`` entry accepts: ``product_id`` (required), ``versions``
    (optional list), ``date_start`` / ``date_end`` (ISO yyyy-mm-dd, review date),
    plus optional ``label`` and ``description`` overrides. Sessions are matched
    on ``product_id`` and (when provided) version list; the spec carries those
    fields plus the date window, which ``_filter_comments`` later applies on the
    review ``date`` column.
    """
    sessions = get_sessions(user_id)
    sessions_by_product: dict[str, list[dict[str, Any]]] = {}
    for session in sessions:
        key = str(session.get("product_id") or "").strip()
        if not key:
            continue
        sessions_by_product.setdefault(key, []).append(session)

    specs: list[dict[str, Any]] = []
    for raw in filter_groups[:5]:
        product_id = str(raw.get("product_id") or "").strip()
        if not product_id:
            continue

        versions_raw = raw.get("versions") or raw.get("version")
        version_list: list[str] = []
        if isinstance(versions_raw, str):
            version_list = [versions_raw.strip()] if versions_raw.strip() else []
        elif isinstance(versions_raw, (list, tuple, set)):
            version_list = [str(item).strip() for item in versions_raw if str(item).strip()]

        date_start = _to_date(raw.get("date_start") or raw.get("date_from"))
        date_end = _to_date(raw.get("date_end") or raw.get("date_to"))

        product_sessions = sessions_by_product.get(product_id, [])
        if version_list:
            version_set = {value for value in version_list}
            product_sessions = [
                session
                for session in product_sessions
                if str(session.get("version") or "").strip() in version_set
            ]
        session_ids = [int(session["id"]) for session in product_sessions if session.get("id") is not None]

        label = str(raw.get("label") or "").strip()
        if not label:
            label_parts = [product_id]
            if version_list:
                label_parts.append("/".join(version_list))
            if date_start or date_end:
                label_parts.append(
                    f"{date_start.isoformat() if date_start else '…'} ~ {date_end.isoformat() if date_end else '…'}"
                )
            label = " · ".join(label_parts)

        description = str(raw.get("description") or "").strip()
        if not description:
            desc_parts: list[str] = []
            if version_list:
                desc_parts.append(f"版本 {' / '.join(version_list)}")
            if date_start or date_end:
                desc_parts.append(
                    f"评论日期 {date_start.isoformat() if date_start else '…'} 到 {date_end.isoformat() if date_end else '…'}"
                )
            if not desc_parts:
                desc_parts.append("全部评论")
            description = " · ".join(desc_parts)

        spec: dict[str, Any] = {
            "label": label,
            "description": description,
            "session_ids": session_ids,
            "product_id": product_id,
            "versions": version_list,
        }
        if date_start:
            spec["date_start"] = date_start.isoformat()
        if date_end:
            spec["date_end"] = date_end.isoformat()
        specs.append(spec)

    return specs


def get_comparison_dataset(user_id: int, filters: dict[str, Any]) -> dict[str, Any]:
    compare_type = str(filters.get("compare_type") or "custom")
    group_specs = [group for group in filters.get("groups", []) if group.get("label")]
    if len(group_specs) < 2:
        return {
            "compare_type": compare_type,
            "groups": [],
            "comparison_rows": [],
            "issue_differences": [],
            "highlight_differences": [],
            "risk_groups": [],
            "opportunity_groups": [],
            "recommended_actions": ["请至少选择两个有效的对比对象。"],
            "empty_groups": [],
            "_group_comments": [],
        }

    sessions = get_sessions(user_id)
    session_lookup = {
        int(session["id"]): session
        for session in sessions
        if session.get("id") is not None
    }
    comments = get_comments(user_id)

    groups: list[dict[str, Any]] = []
    group_comments_list: list[list[dict[str, Any]]] = []
    empty_groups: list[str] = []
    for spec in group_specs:
        group_comments = _filter_comments(comments, session_lookup, spec)
        group_summary = _build_group_summary(spec, group_comments)
        groups.append(group_summary)
        group_comments_list.append(group_comments)
        if group_summary["review_count"] == 0:
            empty_groups.append(group_summary["label"])

    comparison_rows = [
        {
            "对比对象": group["label"],
            "说明": group["description"],
            "评论数": group["review_count"],
            "有效评论": group["valid_review_count"],
            "好评率": f"{group['positive_rate']:.1f}%",
            "差评率": f"{group['negative_rate']:.1f}%",
            "平均评分": "-" if group["avg_rating"] is None else f"{group['avg_rating']:.1f}",
            "TOP问题": group["top_issue"],
            "TOP亮点": group["top_highlight"],
        }
        for group in groups
    ]

    issue_differences = _build_tag_difference_rows(groups, "top_issues")
    highlight_differences = _build_tag_difference_rows(groups, "top_highlights")
    risk_groups = _build_risk_groups(groups)
    opportunity_groups = _build_opportunity_groups(groups)
    recommended_actions = _build_recommended_actions(
        compare_type,
        groups,
        risk_groups,
        opportunity_groups,
    )

    return {
        "compare_type": compare_type,
        "groups": groups,
        "comparison_rows": comparison_rows,
        "issue_differences": issue_differences,
        "highlight_differences": highlight_differences,
        "risk_groups": risk_groups,
        "opportunity_groups": opportunity_groups,
        "recommended_actions": recommended_actions,
        "empty_groups": empty_groups,
        "_group_comments": group_comments_list,
    }


def generate_ai_comparison_summary(
    user_id: int,
    dataset: dict[str, Any],
    focus_feature: str | None = None,
) -> dict[str, Any]:
    groups = dataset.get("groups", [])
    groups_with_data = [group for group in groups if group.get("review_count", 0) > 0]
    if len(groups_with_data) < 2:
        raise ValueError("当前有效评论不足，暂时无法生成 AI 对比总结。")

    api_key = get_api_key(user_id)
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
        timeout=30.0,
    )

    prompt = _build_ai_summary_prompt(dataset, focus_feature=focus_feature)
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": _comparison_summary_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=900,
            response_format={"type": "json_object"},
        )
    except AuthenticationError as exc:
        raise ValueError("DeepSeek API Key 无效，请先到设置页检查配置。") from exc
    except APITimeoutError as exc:
        raise ValueError("AI 对比总结生成超时，请稍后重试。") from exc
    except APIError as exc:
        raise ValueError(f"AI 对比总结生成失败：{exc}") from exc

    content = response.choices[0].message.content.strip()
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("AI 返回结果无法解析，请重试一次。") from exc

    return {
        "headline": str(payload.get("headline") or "AI 对比结论"),
        "summary": _normalize_text_list(payload.get("summary"), limit=3),
        "recommendations": _normalize_text_list(payload.get("recommendations"), limit=4),
        "risks": _normalize_text_list(payload.get("risks"), limit=3),
    }


def save_comparison_report(
    user_id: int,
    comparison_type: str,
    title: str | None,
    filters: dict[str, Any],
    dataset: dict[str, Any],
    ai_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    summary_text = _join_text_lines(
        [ai_summary.get("headline")] if ai_summary else [],
        ai_summary.get("summary", []) if ai_summary else [],
    )
    recommendations_text = _join_text_lines(
        ai_summary.get("recommendations", []) if ai_summary else [],
        dataset.get("recommended_actions", []),
    )
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO comparison_reports
                    (user_id, comparison_type, title, filters_json, result_snapshot, summary, recommendations)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, user_id, comparison_type, title, filters_json, result_snapshot, summary, recommendations, created_at
                """,
                (
                    user_id,
                    comparison_type,
                    title,
                    psycopg2.extras.Json(filters),
                    psycopg2.extras.Json(
                        {
                            "dataset": dataset,
                            "ai_summary": ai_summary,
                        }
                    ),
                    summary_text or None,
                    recommendations_text or None,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return _normalize_report_row(dict(row)) if row else {}
    finally:
        conn.close()


def get_comparison_report_by_id(user_id: int, report_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, user_id, comparison_type, title, filters_json, result_snapshot, summary, recommendations, created_at
                FROM comparison_reports
                WHERE user_id = %s AND id = %s
                """,
                (user_id, report_id),
            )
            row = cur.fetchone()
            return _normalize_report_row(dict(row)) if row else None
    finally:
        conn.close()


def _join_text_lines(*groups: list[Any]) -> str:
    lines: list[str] = []
    for group in groups:
        for item in group:
            text = str(item or "").strip()
            if text:
                lines.append(text)
    return "\n".join(dict.fromkeys(lines))


def _normalize_report_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    for field in ("filters_json", "result_snapshot"):
        value = normalized.get(field)
        if isinstance(value, str):
            try:
                normalized[field] = json.loads(value)
            except json.JSONDecodeError:
                normalized[field] = {}
    return normalized


def _filter_comments(
    comments: list[dict[str, Any]],
    session_lookup: dict[int, dict[str, Any]],
    spec: dict[str, Any],
) -> list[dict[str, Any]]:
    session_ids = {int(value) for value in spec.get("session_ids", []) if value is not None}
    versions = _normalize_str_set(spec.get("versions") or spec.get("version"))
    variant_ids = _normalize_int_set(spec.get("variant_ids") or spec.get("variant_ref_id"))
    product_ref_ids = _normalize_int_set(spec.get("product_ref_ids") or spec.get("product_ref_id"))
    product_id = str(spec.get("product_id") or "").strip()
    date_start = _to_date(spec.get("date_start"))
    date_end = _to_date(spec.get("date_end"))

    filtered: list[dict[str, Any]] = []
    for comment in comments:
        session_id = int(comment["session_id"]) if comment.get("session_id") is not None else None
        session = session_lookup.get(session_id) if session_id is not None else None

        if session_ids and session_id not in session_ids:
            continue
        if not session_ids and product_id and str(comment.get("product_id") or "").strip() != product_id:
            continue
        if versions and str(comment.get("version") or "").strip() not in versions:
            continue
        if variant_ids:
            session_variant_id = int(session["variant_ref_id"]) if session and session.get("variant_ref_id") else None
            if session_variant_id not in variant_ids:
                continue
        if product_ref_ids:
            session_product_id = int(session["product_ref_id"]) if session and session.get("product_ref_id") else None
            if session_product_id not in product_ref_ids:
                continue

        if date_start or date_end:
            comment_date = _to_date(comment.get("date"))
            if comment_date is None:
                continue
            if date_start and comment_date < date_start:
                continue
            if date_end and comment_date > date_end:
                continue

        filtered.append(dict(comment))

    return _dedupe_comments(filtered)


def _build_group_summary(spec: dict[str, Any], comments: list[dict[str, Any]]) -> dict[str, Any]:
    label = str(spec.get("label") or "未命名对象").strip()
    description = str(spec.get("description") or "").strip()
    session_ids = [int(value) for value in spec.get("session_ids", []) if value is not None]
    versions = [str(value) for value in spec.get("versions", []) if str(value).strip()]
    review_count = len(comments)
    valid_comments = [comment for comment in comments if comment.get("sentiment") != "unrecognizable"]
    positive_comments = [comment for comment in valid_comments if comment.get("sentiment") == "positive"]
    negative_comments = [comment for comment in valid_comments if comment.get("sentiment") == "negative"]
    ratings = [_to_float(comment.get("rating")) for comment in comments]
    valid_ratings = [rating for rating in ratings if rating is not None]

    top_issues = _get_top_tags(negative_comments, "issue_tag")
    top_highlights = _get_top_tags(positive_comments, "highlight_tag")

    return {
        "label": label,
        "description": description or "当前筛选范围",
        "session_ids": session_ids,
        "product_id": str(spec.get("product_id") or ""),
        "versions": versions,
        "product_ref_id": spec.get("product_ref_id"),
        "variant_ref_id": spec.get("variant_ref_id"),
        "review_count": review_count,
        "valid_review_count": len(valid_comments),
        "positive_rate": round((len(positive_comments) / len(valid_comments)) * 100, 1) if valid_comments else 0.0,
        "negative_rate": round((len(negative_comments) / len(valid_comments)) * 100, 1) if valid_comments else 0.0,
        "avg_rating": round(sum(valid_ratings) / len(valid_ratings), 1) if valid_ratings else None,
        "top_issue": top_issues[0]["tag"] if top_issues else "-",
        "top_highlight": top_highlights[0]["tag"] if top_highlights else "-",
        "top_issues": top_issues,
        "top_highlights": top_highlights,
        "representative_reviews": {
            "negative": _pick_representative_reviews(negative_comments, top_issues),
            "positive": _pick_representative_reviews(positive_comments, top_highlights),
        },
    }


def _dedupe_comments(comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for comment in comments:
        fallback_key = f"comment-{comment.get('id')}"
        key = str(comment.get("content_hash") or fallback_key)
        current = deduped.get(key)
        if current is None or int(comment.get("id") or 0) > int(current.get("id") or 0):
            deduped[key] = comment

    return sorted(
        deduped.values(),
        key=lambda comment: (
            _to_date(comment.get("date")) or date.min,
            int(comment.get("id") or 0),
        ),
        reverse=True,
    )


def _get_top_tags(comments: list[dict[str, Any]], tag_field: str) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for comment in comments:
        seen_tags: set[str] = set()
        for raw_tag in str(comment.get(tag_field) or "").split(","):
            tag = raw_tag.strip()
            if tag and tag not in seen_tags:
                seen_tags.add(tag)
                counter[tag] += 1

    pool_size = len(comments)
    results: list[dict[str, Any]] = []
    for tag, count in counter.most_common(8):
        pct = round((count / pool_size) * 100, 1) if pool_size else 0.0
        results.append({"tag": tag, "count": count, "pct": pct})
    return results


def _pick_representative_reviews(
    comments: list[dict[str, Any]],
    top_tags: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not comments:
        return []

    preferred_tags = {item["tag"] for item in top_tags[:3]}

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
            _to_date(comment.get("date")) or date.min,
            int(comment.get("id") or 0),
        )

    picked = sorted(comments, key=sort_key, reverse=True)[:3]
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


def _build_tag_difference_rows(groups: list[dict[str, Any]], field_name: str) -> list[dict[str, Any]]:
    all_tags = [
        item["tag"]
        for group in groups
        for item in group.get(field_name, [])
    ]
    unique_tags = list(dict.fromkeys(all_tags))
    rows: list[dict[str, Any]] = []

    for tag in unique_tags:
        row: dict[str, Any] = {"标签": tag}
        values: list[float] = []
        leader = "-"
        best_value = -1.0

        for group in groups:
            pct = _find_tag_pct(group.get(field_name, []), tag)
            values.append(pct)
            row[group["label"]] = f"{pct:.1f}%"
            if pct > best_value:
                best_value = pct
                leader = group["label"]

        row["最高组"] = leader
        row["最大差值"] = f"{(max(values) - min(values)):.1f}pt" if values else "0.0pt"
        row["_sort_value"] = max(values) - min(values) if values else 0.0
        rows.append(row)

    rows.sort(key=lambda row: row["_sort_value"], reverse=True)
    for row in rows:
        row.pop("_sort_value", None)
    return rows[:12]


def _build_risk_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        groups,
        key=lambda group: (
            group["negative_rate"],
            group["review_count"],
        ),
        reverse=True,
    )
    return [
        {
            "label": group["label"],
            "negative_rate": group["negative_rate"],
            "review_count": group["review_count"],
            "top_issue": group["top_issue"],
        }
        for group in ranked
        if group["review_count"] > 0
    ]


def _build_opportunity_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        groups,
        key=lambda group: (
            group["positive_rate"],
            _top_tag_strength(group.get("top_highlights", [])),
            group["review_count"],
        ),
        reverse=True,
    )
    return [
        {
            "label": group["label"],
            "positive_rate": group["positive_rate"],
            "review_count": group["review_count"],
            "top_highlight": group["top_highlight"],
        }
        for group in ranked
        if group["review_count"] > 0
    ]


def _build_recommended_actions(
    compare_type: str,
    groups: list[dict[str, Any]],
    risk_groups: list[dict[str, Any]],
    opportunity_groups: list[dict[str, Any]],
) -> list[str]:
    actions: list[str] = []
    groups_with_data = [group for group in groups if group["review_count"] > 0]
    if len(groups_with_data) < 2:
        return ["当前可用评论不足以形成稳定对比，建议先补充更多批次或放宽筛选范围。"]

    first_group = groups_with_data[0]
    last_group = groups_with_data[-1]
    risk_group = risk_groups[0] if risk_groups else None
    opportunity_group = opportunity_groups[0] if opportunity_groups else None

    if compare_type in {"same_product_time", "same_product_version"}:
        delta_negative = round(last_group["negative_rate"] - first_group["negative_rate"], 1)
        if delta_negative <= -5:
            actions.append(
                f"{last_group['label']} 的差评率比 {first_group['label']} 下降 {abs(delta_negative):.1f} 个点，"
                "说明当前改进方向已经看到效果，建议继续固化为标准动作。"
            )
        elif delta_negative >= 5:
            actions.append(
                f"{last_group['label']} 的差评率比 {first_group['label']} 上升 {delta_negative:.1f} 个点，"
                f"建议优先排查「{last_group['top_issue']}」相关链路。"
            )
        else:
            actions.append(
                f"{first_group['label']} 和 {last_group['label']} 的差评率变化不大，"
                "建议继续观察 TOP 问题是否发生结构性变化。"
            )

        delta_positive = round(last_group["positive_rate"] - first_group["positive_rate"], 1)
        if delta_positive >= 5:
            actions.append(
                f"{last_group['label']} 的好评率比 {first_group['label']} 提升 {delta_positive:.1f} 个点，"
                f"可以围绕「{last_group['top_highlight']}」沉淀 Listing 文案和广告卖点。"
            )
        elif delta_positive <= -5:
            actions.append(
                f"{last_group['label']} 的好评率比 {first_group['label']} 下降 {abs(delta_positive):.1f} 个点，"
                "建议复盘最近的产品 / 包装 / 发货变更，找到流失的好评触点。"
            )

    if compare_type == "same_parent_variants" and risk_group and opportunity_group:
        if risk_group["label"] != opportunity_group["label"]:
            actions.append(
                f"{opportunity_group['label']} 更适合作为当前主推变体，"
                f"{risk_group['label']} 需要优先处理「{risk_group['top_issue']}」后再加大投放。"
            )

    if compare_type in {"multi_product", "custom"} and risk_group and opportunity_group:
        if risk_group["label"] == opportunity_group["label"]:
            actions.append(
                f"{risk_group['label']} 同时有较强卖点和较高风险，适合保留曝光，但要先压低「{risk_group['top_issue']}」问题。"
            )
        else:
            actions.append(
                f"{opportunity_group['label']} 当前更像主推机会款，"
                f"{risk_group['label']} 更像风险款，建议先控制预算并修复核心问题。"
            )

    if risk_group and risk_group["top_issue"] != "-":
        actions.append(
            f"优先建立关于「{risk_group['top_issue']}」的跟进行动，"
            f"先从 {risk_group['label']} 开始，避免高差评问题继续扩散。"
        )

    if opportunity_group and opportunity_group["top_highlight"] != "-":
        actions.append(
            f"可在 Listing、广告或素材中优先强化 {opportunity_group['label']} 的「{opportunity_group['top_highlight']}」卖点。"
        )

    # 每个 group 各出一条针对性建议: TOP 问题修复 + TOP 亮点放大。
    for group in groups_with_data:
        top_issue = str(group.get("top_issue") or "").strip()
        if top_issue and top_issue != "-":
            actions.append(
                f"{group['label']}: 围绕「{top_issue}」做一次根因复盘，输出可执行的工艺/包装/客服话术调整。"
            )

    for group in groups_with_data:
        top_highlight = str(group.get("top_highlight") or "").strip()
        if top_highlight and top_highlight != "-":
            actions.append(
                f"{group['label']}: 把「{top_highlight}」沉淀到主图、A+ 内容和广告 headline，扩大该卖点的曝光面。"
            )

    # 同一 group 的 TOP 问题 vs TOP 亮点反差较大时, 提示用户做"扬长避短"决策。
    for group in groups_with_data:
        if (
            group.get("top_issue") not in (None, "", "-")
            and group.get("top_highlight") not in (None, "", "-")
            and group.get("negative_rate", 0) >= 30
        ):
            actions.append(
                f"{group['label']}: 差评率 {group['negative_rate']:.1f}% 偏高，"
                f"建议先解决「{group['top_issue']}」再放大「{group['top_highlight']}」，避免好评被同期差评稀释。"
            )

    return list(dict.fromkeys(actions))[:10]


def _build_ai_summary_prompt(dataset: dict[str, Any], focus_feature: str | None = None) -> str:
    compare_type = str(dataset.get("compare_type") or "custom")
    compare_type_label = COMPARE_TYPE_LABELS.get(compare_type, compare_type)
    payload = {
        "compare_type": compare_type_label,
        "groups": [
            {
                "label": group["label"],
                "description": group["description"],
                "review_count": group["review_count"],
                "valid_review_count": group["valid_review_count"],
                "positive_rate": group["positive_rate"],
                "negative_rate": group["negative_rate"],
                "avg_rating": group["avg_rating"],
                "top_issues": group.get("top_issues", [])[:3],
                "top_highlights": group.get("top_highlights", [])[:3],
                "negative_review_examples": [
                    _truncate_text(review["content"])
                    for review in group.get("representative_reviews", {}).get("negative", [])[:2]
                ],
                "positive_review_examples": [
                    _truncate_text(review["content"])
                    for review in group.get("representative_reviews", {}).get("positive", [])[:2]
                ],
            }
            for group in dataset.get("groups", [])
        ],
        "issue_differences": dataset.get("issue_differences", [])[:6],
        "highlight_differences": dataset.get("highlight_differences", [])[:6],
        "risk_groups": dataset.get("risk_groups", [])[:3],
        "opportunity_groups": dataset.get("opportunity_groups", [])[:3],
        "rule_actions": dataset.get("recommended_actions", [])[:4],
    }
    focus_feature = str(focus_feature or dataset.get("focus_feature") or "").strip()
    focus_instruction = (
        f"\n当前功能点关注：{focus_feature}\n请优先围绕这个功能点解释差异、风险和机会。"
        if focus_feature
        else ""
    )
    return (
        "请基于下面的对比数据，生成适合电商运营 / 产研 / 质检阅读的中文结论。\n"
        "要求：\n"
        "1. 只能使用提供的数据，不要虚构评论数、占比或产品表现。\n"
        "2. 结论要偏业务判断，不要只是复述表格。\n"
        "3. 推荐动作必须可执行，能直接指导主推、修复、复盘或 Listing 优化。\n"
        "4. 如果数据不足，要明确提示不要过度下结论。\n\n"
        f"{focus_instruction}"
        f"对比数据：\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _comparison_summary_system_prompt() -> str:
    return (
        "你是一位有 6 年跨境电商经验的 VOC 分析顾问。"
        "请把评论对比数据总结成经营判断。"
        "输出必须是 JSON 对象，格式为："
        '{"headline":"一句话结论","summary":["..."],"recommendations":["..."],"risks":["..."]}'
    )


def _normalize_text_list(value: Any, limit: int) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    elif value in (None, ""):
        items = []
    else:
        items = [str(value).strip()]
    return items[:limit]


def _truncate_text(value: str, limit: int = 180) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _find_tag_pct(tags: list[dict[str, Any]], target_tag: str) -> float:
    for item in tags:
        if item["tag"] == target_tag:
            return float(item["pct"])
    return 0.0


def _top_tag_strength(tags: list[dict[str, Any]]) -> float:
    if not tags:
        return 0.0
    return float(tags[0]["pct"])


def _normalize_str_set(value: Any) -> set[str]:
    if value is None or value == "":
        return set()
    if isinstance(value, (list, tuple, set)):
        return {str(item).strip() for item in value if str(item).strip()}
    return {str(value).strip()}


def _normalize_int_set(value: Any) -> set[int]:
    if value is None or value == "":
        return set()
    values = value if isinstance(value, (list, tuple, set)) else [value]
    normalized: set[int] = set()
    for item in values:
        try:
            normalized.add(int(item))
        except (TypeError, ValueError):
            continue
    return normalized


def _to_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text:
        return None

    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def dataset_to_xlsx_payload(
    dataset: dict[str, Any],
    ai_summary: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Adapt a comparison dataset to ``export_compare_page_to_xlsx``'s contract.

    Builds the ``columns`` list (first cell + one column per group), then layers
    the workbook into sections: KPI overview, issue & highlight differences,
    risk / opportunity callouts, recommended actions, optional AI summary.
    """
    groups = list(dataset.get("groups") or [])
    columns = ["指标 / 维度"] + [str(group.get("label") or "-") for group in groups]

    def _row(label: str, values: list[Any]) -> dict[str, Any]:
        return {"label": label, "values": [str(value) for value in values]}

    overview_children: list[dict[str, Any]] = [
        _row("描述", [group.get("description", "-") for group in groups]),
        _row("评论数", [group.get("review_count", 0) for group in groups]),
        _row("有效评论", [group.get("valid_review_count", 0) for group in groups]),
        _row("好评率", [f"{group.get('positive_rate', 0):.1f}%" for group in groups]),
        _row("差评率", [f"{group.get('negative_rate', 0):.1f}%" for group in groups]),
        _row(
            "平均评分",
            [
                "-" if group.get("avg_rating") is None else f"{group.get('avg_rating'):.1f}"
                for group in groups
            ],
        ),
        _row("TOP 问题", [group.get("top_issue", "-") for group in groups]),
        _row("TOP 亮点", [group.get("top_highlight", "-") for group in groups]),
    ]

    issue_children: list[dict[str, Any]] = []
    for diff in dataset.get("issue_differences") or []:
        tag = str(diff.get("标签") or diff.get("tag") or "-")
        values = [str(diff.get(group.get("label"), "-")) for group in groups]
        issue_children.append(_row(tag, values))

    highlight_children: list[dict[str, Any]] = []
    for diff in dataset.get("highlight_differences") or []:
        tag = str(diff.get("标签") or diff.get("tag") or "-")
        values = [str(diff.get(group.get("label"), "-")) for group in groups]
        highlight_children.append(_row(tag, values))

    risk_children: list[dict[str, Any]] = []
    for risk in dataset.get("risk_groups") or []:
        risk_children.append(
            _row(
                str(risk.get("label") or "-"),
                [
                    f"差评率 {risk.get('negative_rate', 0):.1f}% · 评论 {risk.get('review_count', 0)} 条 · TOP {risk.get('top_issue', '-')}"
                ]
                + [""] * (len(columns) - 2),
            )
        )

    opportunity_children: list[dict[str, Any]] = []
    for opp in dataset.get("opportunity_groups") or []:
        opportunity_children.append(
            _row(
                str(opp.get("label") or "-"),
                [
                    f"好评率 {opp.get('positive_rate', 0):.1f}% · 评论 {opp.get('review_count', 0)} 条 · TOP {opp.get('top_highlight', '-')}"
                ]
                + [""] * (len(columns) - 2),
            )
        )

    action_children: list[dict[str, Any]] = [
        _row(f"建议 {idx + 1}", [str(text)] + [""] * (len(columns) - 2))
        for idx, text in enumerate(dataset.get("recommended_actions") or [])
    ]

    sections: list[dict[str, Any]] = [
        {"section": "① 总览指标", "values": [""] * (len(columns) - 1), "children": overview_children},
    ]
    if issue_children:
        sections.append({"section": "② 问题差异", "values": [""] * (len(columns) - 1), "children": issue_children})
    if highlight_children:
        sections.append({"section": "③ 亮点差异", "values": [""] * (len(columns) - 1), "children": highlight_children})
    if risk_children:
        sections.append({"section": "④ 风险对象", "values": [""] * (len(columns) - 1), "children": risk_children})
    if opportunity_children:
        sections.append({"section": "⑤ 机会对象", "values": [""] * (len(columns) - 1), "children": opportunity_children})
    if action_children:
        sections.append({"section": "⑥ 推荐动作", "values": [""] * (len(columns) - 1), "children": action_children})

    if ai_summary:
        ai_children: list[dict[str, Any]] = []
        headline = str(ai_summary.get("headline") or "").strip()
        if headline:
            ai_children.append(_row("结论", [headline] + [""] * (len(columns) - 2)))
        for idx, item in enumerate(ai_summary.get("summary") or []):
            ai_children.append(_row(f"总结 {idx + 1}", [str(item)] + [""] * (len(columns) - 2)))
        for idx, item in enumerate(ai_summary.get("recommendations") or []):
            ai_children.append(_row(f"建议 {idx + 1}", [str(item)] + [""] * (len(columns) - 2)))
        for idx, item in enumerate(ai_summary.get("risks") or []):
            ai_children.append(_row(f"风险 {idx + 1}", [str(item)] + [""] * (len(columns) - 2)))
        if ai_children:
            sections.append({"section": "⑦ AI 总结", "values": [""] * (len(columns) - 1), "children": ai_children})

    compare_type = str(dataset.get("compare_type") or "custom")
    context = {
        "title": f"{COMPARE_TYPE_LABELS.get(compare_type, compare_type)} · {len(groups)} 个对象",
    }
    return {"columns": columns, "objects": sections}, context


def compute_compare_fingerprint(
    user_id: int,
    compare_type: str,
    group_specs: list[dict[str, Any]],
) -> str:
    """Fingerprint cache key for (user, compare_type, normalized groups).

    Normalizes each group to (product_id, sorted versions, date_start, date_end),
    then sha256 the JSON. Same filter inputs → same fingerprint → same cache hit.
    """
    normalized: list[dict[str, Any]] = []
    for spec in group_specs:
        normalized.append(
            {
                "product_id": str(spec.get("product_id") or "").strip(),
                "versions": sorted(
                    str(value).strip()
                    for value in (spec.get("versions") or [])
                    if str(value).strip()
                ),
                "date_start": str(spec.get("date_start") or "").strip(),
                "date_end": str(spec.get("date_end") or "").strip(),
            }
        )
    payload = json.dumps(
        {"user_id": int(user_id), "compare_type": compare_type, "groups": normalized},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_compare_cache(fingerprint: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT group_insights, ai_summary
                FROM comparison_summary_cache
                WHERE fingerprint = %s
                """,
                (fingerprint,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "group_insights": _maybe_parse_json(row.get("group_insights")) or [],
                "ai_summary": _maybe_parse_json(row.get("ai_summary")),
            }
    finally:
        conn.close()


def save_compare_cache(
    fingerprint: str,
    user_id: int,
    compare_type: str,
    filter_payload: dict[str, Any],
    group_insights: list[dict[str, Any] | None],
    ai_summary: dict[str, Any] | None,
) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO comparison_summary_cache
                    (fingerprint, user_id, compare_type, filter_payload, group_insights, ai_summary)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (fingerprint) DO UPDATE SET
                    group_insights = EXCLUDED.group_insights,
                    ai_summary = EXCLUDED.ai_summary
                """,
                (
                    fingerprint,
                    user_id,
                    compare_type,
                    psycopg2.extras.Json(filter_payload),
                    psycopg2.extras.Json(group_insights),
                    psycopg2.extras.Json(ai_summary) if ai_summary is not None else None,
                ),
            )
            conn.commit()
    finally:
        conn.close()


def _maybe_parse_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value


def build_group_insights(
    user_id: int,
    group: dict[str, Any],
    comments: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Per-group structured insights (consumer_profile / purchase_motives / …).

    Reuses ``build_results_insights`` so the compare page renders the same
    7-dimension layout as the single-product results page. Returns None when
    the group has no comments — callers should skip rendering insight blocks.
    """
    if not comments:
        return None
    context = {
        "title": str(group.get("label") or "对比对象"),
        "description": str(group.get("description") or ""),
        "product_id": str(group.get("product_id") or ""),
        "version": "/".join(group.get("versions") or []) or "全部版本",
        "review_count": len(comments),
    }
    try:
        return build_results_insights(user_id, comments, context)
    except Exception:  # noqa: BLE001 — insight LLM is best-effort
        return None


# ---------------------------------------------------------------------------
# History helpers (list / load / delete comparison_summary_cache entries)
# ---------------------------------------------------------------------------


def list_compare_history(
    user_id: int,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """List user's comparison history from comparison_summary_cache.

    Returns ``{items: [...], total: int}``. Each item contains fingerprint,
    compare_type, product_names, group_labels, created_at.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if q and q.strip():
                search_term = f"%{q.strip()}%"
                cur.execute(
                    """
                    WITH cache_with_products AS (
                        SELECT
                            c.fingerprint,
                            c.compare_type,
                            c.filter_payload,
                            c.created_at,
                            COALESCE(
                                array_agg(DISTINCT p.name) FILTER (WHERE p.name IS NOT NULL),
                                ARRAY[]::TEXT[]
                            ) AS product_names
                        FROM comparison_summary_cache c
                        LEFT JOIN LATERAL (
                            SELECT (elem->>'product_id')::TEXT AS pid
                            FROM jsonb_array_elements(c.filter_payload->'groups') AS elem
                        ) g ON TRUE
                        LEFT JOIN products p ON p.parent_product_id = g.pid AND p.user_id = c.user_id
                        WHERE c.user_id = %s
                        GROUP BY c.fingerprint, c.compare_type, c.filter_payload, c.created_at
                    )
                    SELECT * FROM cache_with_products
                    WHERE EXISTS (
                        SELECT 1 FROM unnest(product_names) AS pn WHERE pn ILIKE %s
                    )
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, search_term, limit, offset),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        c.fingerprint,
                        c.compare_type,
                        c.filter_payload,
                        c.created_at,
                        COALESCE(
                            array_agg(DISTINCT p.name) FILTER (WHERE p.name IS NOT NULL),
                            ARRAY[]::TEXT[]
                        ) AS product_names
                    FROM comparison_summary_cache c
                    LEFT JOIN LATERAL (
                        SELECT (elem->>'product_id')::TEXT AS pid
                        FROM jsonb_array_elements(c.filter_payload->'groups') AS elem
                    ) g ON TRUE
                    LEFT JOIN products p ON p.parent_product_id = g.pid AND p.user_id = c.user_id
                    WHERE c.user_id = %s
                    GROUP BY c.fingerprint, c.compare_type, c.filter_payload, c.created_at
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, limit, offset),
                )
            rows = cur.fetchall()

            # Count total
            if q and q.strip():
                cur.execute(
                    """
                    WITH cache_with_products AS (
                        SELECT
                            c.fingerprint,
                            COALESCE(
                                array_agg(DISTINCT p.name) FILTER (WHERE p.name IS NOT NULL),
                                ARRAY[]::TEXT[]
                            ) AS product_names
                        FROM comparison_summary_cache c
                        LEFT JOIN LATERAL (
                            SELECT (elem->>'product_id')::TEXT AS pid
                            FROM jsonb_array_elements(c.filter_payload->'groups') AS elem
                        ) g ON TRUE
                        LEFT JOIN products p ON p.parent_product_id = g.pid AND p.user_id = c.user_id
                        WHERE c.user_id = %s
                        GROUP BY c.fingerprint
                    )
                    SELECT COUNT(*) FROM cache_with_products
                    WHERE EXISTS (
                        SELECT 1 FROM unnest(product_names) AS pn WHERE pn ILIKE %s
                    )
                    """,
                    (user_id, search_term),
                )
            else:
                cur.execute(
                    "SELECT COUNT(*) FROM comparison_summary_cache WHERE user_id = %s",
                    (user_id,),
                )
            total = cur.fetchone()["count"]

        items = []
        for row in rows:
            filter_payload = _maybe_parse_json(row.get("filter_payload")) or {}
            groups = filter_payload.get("groups") or []
            group_labels = _build_group_labels(groups)
            items.append({
                "fingerprint": row["fingerprint"],
                "compare_type": row["compare_type"],
                "product_names": list(row.get("product_names") or []),
                "group_labels": group_labels,
                "created_at": row["created_at"].isoformat() if row.get("created_at") else "",
            })
        return {"items": items, "total": total}
    finally:
        conn.close()


def _build_group_labels(groups: list[dict[str, Any]]) -> list[str]:
    """Build short display labels from filter_payload groups."""
    labels = []
    for g in groups:
        parts = []
        versions = g.get("versions") or []
        if versions:
            parts.append("/".join(str(v) for v in versions))
        date_start = g.get("date_start") or ""
        date_end = g.get("date_end") or ""
        if date_start and date_end:
            parts.append(f"{date_start}~{date_end}")
        elif date_start:
            parts.append(f"{date_start}~")
        elif date_end:
            parts.append(f"~{date_end}")
        labels.append(" · ".join(parts) if parts else "全部")
    return labels


def load_compare_history_entry(
    user_id: int,
    fingerprint: str,
) -> dict[str, Any] | None:
    """Load a single cache entry for replay (filter_payload + insights + summary)."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT compare_type, filter_payload, group_insights, ai_summary
                FROM comparison_summary_cache
                WHERE fingerprint = %s AND user_id = %s
                """,
                (fingerprint, user_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "compare_type": row["compare_type"],
                "filter_payload": _maybe_parse_json(row.get("filter_payload")) or {},
                "group_insights": _maybe_parse_json(row.get("group_insights")) or [],
                "ai_summary": _maybe_parse_json(row.get("ai_summary")),
            }
    finally:
        conn.close()


def delete_compare_history(user_id: int, fingerprint: str) -> bool:
    """Delete a single comparison cache entry. Returns True if deleted."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM comparison_summary_cache
                WHERE fingerprint = %s AND user_id = %s
                """,
                (fingerprint, user_id),
            )
            deleted = cur.rowcount > 0
            conn.commit()
            return deleted
    finally:
        conn.close()

