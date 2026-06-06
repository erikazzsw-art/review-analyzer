from __future__ import annotations

from collections import Counter
from datetime import date, datetime
import json
from typing import Any

from openai import APIError, APITimeoutError, AuthenticationError, OpenAI
import psycopg2.extras

from review_analyzer.analyzer import get_api_key
from review_analyzer.database import get_comments, get_connection, get_sessions


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
        }

    sessions = get_sessions(user_id)
    session_lookup = {
        int(session["id"]): session
        for session in sessions
        if session.get("id") is not None
    }
    comments = get_comments(user_id)

    groups: list[dict[str, Any]] = []
    empty_groups: list[str] = []
    for spec in group_specs:
        group_comments = _filter_comments(comments, session_lookup, spec)
        group_summary = _build_group_summary(spec, group_comments)
        groups.append(group_summary)
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

    return list(dict.fromkeys(actions))[:4]


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
