"""评论分析中的对比分析子页。"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any

import streamlit as st

from review_analyzer.analysis_export import export_compare_page_to_xlsx
from review_analyzer.auth import get_current_user_id
from review_analyzer.database import get_comments, get_sessions
from review_analyzer.i18n import pick
from review_analyzer.insight_engine import build_compare_insights
from review_analyzer.page_shell import render_page_header
from review_analyzer.product_store import get_product_overview_rows
from review_analyzer.translation import translate_compare_dataset

COMPARE_TYPES = {
    "same_product_time": {"zh": "同一产品不同时间维度", "en": "Same Product Across Time"},
    "same_product_version": {"zh": "同一产品多版本对比", "en": "Same Product Across Versions"},
    "multi_product": {"zh": "跨产品对比", "en": "Multi-Product Comparison"},
}

MAX_COMPARE_PRODUCTS = 5

FIELD_ALIASES = {
    "Product Name": ["商品名称"],
    "Image": ["产品图"],
    "Brand": ["品牌"],
    "Price": ["价格"],
    "Launch Time": ["上架时间"],
    "Rating": ["星级"],
    "Review Count": ["评论数"],
    "Audience Traits": ["人群特征"],
    "Usage Moments": ["使用时刻"],
    "Usage Location": ["使用地点"],
    "Behavior": ["行为"],
    "Positive Viewpoints": ["正向观点"],
    "Negative Viewpoints": ["负向观点"],
    "Customer Purchase Motives": ["客户购买动机"],
    "User Expectations": ["用户期望"],
}


def render_compare() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning(pick("请先登录", "Please log in first."))
        return

    render_page_header(
        pick("对比分析", "Compare"),
        pick(
            "围绕时间、版本或多个产品，统一查看商品信息、消费者画像、产品体验、购买动机和未被满足的需求。",
            "Compare time periods, versions, or multiple products across product info, audience profile, product experience, purchase motives, and unmet needs.",
        ),
        path=pick("评论分析 / 对比分析", "Review Analysis / Compare"),
    )

    product_rows = get_product_overview_rows(user_id)
    if not product_rows:
        st.info(pick("当前还没有可用于对比的产品评论。先去上传一批评论。", "There are no product reviews available for comparison yet. Upload a batch first."))
        return

    compare_type = st.selectbox(
        pick("标准对比类型", "Comparison Type"),
        list(COMPARE_TYPES.keys()),
        format_func=lambda value: pick(COMPARE_TYPES[value]["zh"], COMPARE_TYPES[value]["en"]),
        key="compare_type",
    )

    objects = _build_compare_objects(user_id, product_rows, compare_type)
    if len(objects) < 2:
        st.info(pick("请至少准备 2 个有效对比对象。", "Please prepare at least 2 valid comparison objects."))
        return

    standard_payload = build_compare_insights(
        user_id,
        objects,
        {"title": pick(COMPARE_TYPES[compare_type]["zh"], COMPARE_TYPES[compare_type]["en"])},
        focus_feature=None,
    )
    _render_compare_section(
        user_id,
        "standard_compare",
        pick("标准对比", "Standard Comparison"),
        standard_payload,
        objects,
        pick(COMPARE_TYPES[compare_type]["zh"], COMPARE_TYPES[compare_type]["en"]),
    )

    st.markdown(f"## {pick('功能点定向对比', 'Feature-Focused Comparison')}")
    recommended_tags = _collect_recommended_tags(objects)
    selected_tags = st.multiselect(
        pick("选择推荐功能点", "Choose Recommended Features"),
        recommended_tags,
        default=recommended_tags[:1],
        key="compare_focus_feature_tags",
    )
    custom_feature = st.text_input(
        pick("或手动输入功能点 / 关键词", "Or enter a feature / keyword manually"),
        placeholder=pick("例如：assembly, storage, packaging", "e.g. assembly, storage, packaging"),
        key="compare_focus_feature_custom",
    )
    focus_feature = custom_feature.strip() or " / ".join(selected_tags)
    if focus_feature:
        focus_payload = build_compare_insights(
            user_id,
            objects,
            {"title": pick(f"功能点对比 · {focus_feature}", f"Feature Comparison · {focus_feature}")},
            focus_feature=focus_feature,
        )
        _render_compare_section(
            user_id,
            "focus_compare",
            pick(f"功能点对比：{focus_feature}", f"Feature Comparison: {focus_feature}"),
            focus_payload,
            objects,
            focus_feature,
        )
    else:
        st.info(pick("选择推荐功能点或手动输入关键词后，即可生成功能点对比。", "Choose a recommended feature or enter a keyword to generate a feature-focused comparison."))


def _render_compare_section(
    user_id: int,
    section_key: str,
    title: str,
    payload: dict[str, Any],
    objects: list[dict[str, Any]],
    cache_scope: str,
) -> None:
    display_payload = _resolve_compare_payload(user_id, section_key, payload, objects, cache_scope)
    matrix = _build_matrix_rows(display_payload, objects, _compare_language(section_key))
    header_cols = st.columns([5, 1, 1])
    with header_cols[0]:
        st.markdown(f"## {title}")
    with header_cols[1]:
        button_label = pick("查看英文", "View English") if _compare_language(section_key) == "zh" else pick("切换中文", "View Chinese")
        if st.button(button_label, key=f"compare_translate_{section_key}", use_container_width=True):
            st.session_state[_compare_language_key(section_key)] = "en" if _compare_language(section_key) == "zh" else "zh"
            st.rerun()
    with header_cols[2]:
        xlsx_bytes, xlsx_name = export_compare_page_to_xlsx(
            {"columns": matrix["columns"], "objects": matrix["rows"]},
            {"title": title},
        )
        st.download_button(
            pick("下载", "Download"),
            data=xlsx_bytes,
            file_name=xlsx_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"compare_download_{section_key}",
            use_container_width=True,
        )

    for row in matrix["rows"]:
        st.markdown(
            f"""
            <div class="product-block" style="padding:16px 18px;margin-bottom:10px;">
                <div style="font-size:16px;font-weight:700;color:#25212a;margin-bottom:10px;">{row['section']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(row["frame"], use_container_width=True, hide_index=True)


def _build_compare_objects(
    user_id: int,
    product_rows: list[dict[str, Any]],
    compare_type: str,
) -> list[dict[str, Any]]:
    if compare_type == "same_product_time":
        return _build_time_objects(user_id, product_rows)
    if compare_type == "same_product_version":
        return _build_version_objects(user_id, product_rows)
    return _build_multi_product_objects(user_id, product_rows)


def _build_time_objects(user_id: int, product_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    product_map = {str(row["parent_product_id"]): row for row in product_rows if row.get("parent_product_id")}
    selected_product_id = st.selectbox(
        pick("选择产品", "Select Product"),
        list(product_map.keys()),
        format_func=lambda value: _format_product_label(product_map[value]),
        key="compare_time_product",
    )
    all_comments = get_comments(user_id, product_id=selected_product_id)
    all_dates = [_parse_date(comment.get("date")) for comment in all_comments]
    valid_dates = [item for item in all_dates if item is not None]
    if not valid_dates:
        return []
    latest_date = max(valid_dates)
    default_end_a = latest_date - timedelta(days=30)
    default_start_a = default_end_a - timedelta(days=29)
    default_start_b = latest_date - timedelta(days=29)
    col1, col2 = st.columns(2)
    with col1:
        start_a = st.date_input(pick("时间段 A 开始", "Period A Start"), value=default_start_a, key="compare_time_start_a")
        end_a = st.date_input(pick("时间段 A 结束", "Period A End"), value=default_end_a, key="compare_time_end_a")
    with col2:
        start_b = st.date_input(pick("时间段 B 开始", "Period B Start"), value=default_start_b, key="compare_time_start_b")
        end_b = st.date_input(pick("时间段 B 结束", "Period B End"), value=latest_date, key="compare_time_end_b")

    return [
        _build_compare_object(
            label=pick(f"{selected_product_id} · 时间段 A", f"{selected_product_id} · Period A"),
            description=f"{start_a} ~ {end_a}",
            product_row=product_map[selected_product_id],
            comments=_filter_comments_by_date(all_comments, start_a, end_a),
            session=None,
        ),
        _build_compare_object(
            label=pick(f"{selected_product_id} · 时间段 B", f"{selected_product_id} · Period B"),
            description=f"{start_b} ~ {end_b}",
            product_row=product_map[selected_product_id],
            comments=_filter_comments_by_date(all_comments, start_b, end_b),
            session=None,
        ),
    ]


def _build_version_objects(user_id: int, product_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    product_map = {str(row["parent_product_id"]): row for row in product_rows if row.get("parent_product_id")}
    selected_product_id = st.selectbox(
        pick("选择产品", "Select Product"),
        list(product_map.keys()),
        format_func=lambda value: _format_product_label(product_map[value]),
        key="compare_version_product",
    )
    sessions = get_sessions(user_id, product_id=selected_product_id)
    version_map: dict[str, dict[str, Any]] = {}
    for session in sessions:
        version = str(session.get("version") or "V1")
        if version not in version_map:
            version_map[version] = session
    selected_versions = st.multiselect(
        pick("选择版本（至少 2 个）", "Select Versions (At Least 2)"),
        list(version_map.keys()),
        default=list(version_map.keys())[:2],
        key="compare_version_selected",
    )
    objects = []
    for version in selected_versions:
        session = version_map.get(version)
        if not session:
            continue
        comments = get_comments(user_id, session_id=int(session["id"]))
        objects.append(
            _build_compare_object(
                label=f"{selected_product_id} · {version}",
                description=_format_session_description(session),
                product_row=product_map[selected_product_id],
                comments=comments,
                session=session,
            )
        )
    return objects


def _build_multi_product_objects(user_id: int, product_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    product_map = {str(row["parent_product_id"]): row for row in product_rows if row.get("parent_product_id")}
    selected_product_ids = st.multiselect(
        pick("选择产品（最多 5 个）", "Select Products (Up to 5)"),
        list(product_map.keys()),
        default=list(product_map.keys())[:2],
        format_func=lambda value: _format_product_label(product_map[value]),
        key="compare_multi_products",
        max_selections=MAX_COMPARE_PRODUCTS,
    )
    objects = []
    for product_id in selected_product_ids:
        sessions = get_sessions(user_id, product_id=product_id)
        if not sessions:
            continue
        latest_session = sessions[0]
        comments = get_comments(user_id, session_id=int(latest_session["id"]))
        objects.append(
            _build_compare_object(
                label=str(product_map[product_id].get("name") or product_id),
                description=_format_session_description(latest_session),
                product_row=product_map[product_id],
                comments=comments,
                session=latest_session,
            )
        )
    return objects


def _build_compare_object(
    *,
    label: str,
    description: str,
    product_row: dict[str, Any],
    comments: list[dict[str, Any]],
    session: dict[str, Any] | None,
) -> dict[str, Any]:
    positive_tags = _top_tag_rows([comment for comment in comments if comment.get("sentiment") == "positive"], "highlight_tag")
    negative_tags = _top_tag_rows([comment for comment in comments if comment.get("sentiment") == "negative"], "issue_tag")
    avg_rating = _average_rating(comments)
    return {
        "label": label,
        "description": description,
        "comments": comments,
        "review_count": len(comments),
        "positive_tags": positive_tags,
        "negative_tags": negative_tags,
        "product_info": {
            "name": str(product_row.get("name") or product_row.get("parent_product_id") or "--"),
            "asin": _extract_asin(session, product_row),
            "rating": f"{avg_rating:.1f}" if avg_rating is not None else "--",
        },
    }


def _resolve_compare_payload(
    user_id: int,
    section_key: str,
    payload: dict[str, Any],
    objects: list[dict[str, Any]],
    cache_scope: str,
) -> dict[str, Any]:
    if _compare_language(section_key) != "zh":
        return payload
    object_signature = "__".join(str(item.get("label") or "--") for item in objects)
    cache_key = f"compare_translated_payload_{section_key}_{cache_scope}_{object_signature}"
    cached_payload = st.session_state.get(cache_key)
    if cached_payload is None:
        cached_payload = translate_compare_dataset(user_id, payload, "zh")
        st.session_state[cache_key] = cached_payload
    return cached_payload


def _build_matrix_rows(payload: dict[str, Any], objects: list[dict[str, Any]], lang: str) -> dict[str, Any]:
    enriched = payload.get("objects", [])
    labels = [obj.get("label", "--") for obj in objects]
    is_zh = lang == "zh"
    sections = [
        (
            pick("商品信息", "Product Info"),
            ["商品名称", "产品图", "品牌", "ASIN", "价格", "上架时间", "星级", "评论数"] if is_zh else ["Product Name", "Image", "Brand", "ASIN", "Price", "Launch Time", "Rating", "Review Count"],
            "product_info",
        ),
        (
            pick("消费者画像", "Consumer Profile"),
            ["人群特征", "使用时刻", "使用地点", "行为"] if is_zh else ["Audience Traits", "Usage Moments", "Usage Location", "Behavior"],
            "consumer_profile",
        ),
        (
            pick("产品体验", "Product Experience"),
            ["正向观点", "负向观点"] if is_zh else ["Positive Viewpoints", "Negative Viewpoints"],
            "experience",
        ),
        (
            pick("购买动机", "Purchase Motives"),
            ["客户购买动机"] if is_zh else ["Customer Purchase Motives"],
            "purchase_motives",
        ),
        (
            pick("未被满足的需求", "Unmet Needs"),
            ["用户期望"] if is_zh else ["User Expectations"],
            "unmet_needs",
        ),
    ]

    rows = []
    for title, keys, section_key in sections:
        frame_rows = []
        for key in keys:
            row = {pick("维度", "Dimension"): key}
            for index, item in enumerate(enriched):
                cell_value = _extract_matrix_cell(item, section_key, key)
                row[labels[index]] = cell_value
            frame_rows.append(row)
        rows.append(
            {
                "section": title,
                "children": frame_rows,
                "values": labels,
                "frame": frame_rows,
            }
        )
    return {"columns": [pick("维度", "Dimension"), *labels], "rows": rows}


def _extract_matrix_cell(item: dict[str, Any], section_key: str, field_key: str) -> str:
    section_payload = item.get(section_key)
    if isinstance(section_payload, dict):
        value = section_payload.get(field_key)
        if value is None:
            for alias in FIELD_ALIASES.get(field_key, []):
                if alias in section_payload:
                    value = section_payload.get(alias)
                    break
        if value is None and field_key in {"客户购买动机", "Customer Purchase Motives"}:
            value = section_payload.get("summary") or section_payload.get("purchase_motives")
        if value is None and field_key in {"用户期望", "User Expectations"}:
            value = section_payload.get("summary") or section_payload.get("unmet_needs")
        if isinstance(value, list):
            return "\n".join(str(entry) for entry in value[:5]) or "--"
        if value not in (None, ""):
            return str(value)
        return "--"
    if section_key in {"purchase_motives", "unmet_needs"} and section_payload not in (None, ""):
        return str(section_payload)
    return "--"


def _collect_recommended_tags(objects: list[dict[str, Any]]) -> list[str]:
    counter: Counter[str] = Counter()
    for obj in objects:
        for row in obj.get("positive_tags", []) + obj.get("negative_tags", []):
            tag = str(row.get("tag") or "").strip()
            if tag:
                counter[tag] += 1
    return [tag for tag, _ in counter.most_common(12)]


def _top_tag_rows(comments: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for comment in comments:
        seen_tags: set[str] = set()
        for raw_tag in str(comment.get(field) or "").split(","):
            tag = raw_tag.strip()
            if not tag or tag in seen_tags:
                continue
            seen_tags.add(tag)
            counter[tag] += 1
    pool_size = len(comments)
    rows = []
    for tag, count in counter.most_common(6):
        pct = round(count / pool_size * 100, 1) if pool_size else 0.0
        rows.append({"tag": tag, "pct": pct})
    return rows


def _filter_comments_by_date(comments: list[dict[str, Any]], start: date, end: date) -> list[dict[str, Any]]:
    filtered = []
    for comment in comments:
        comment_date = _parse_date(comment.get("date"))
        if comment_date is None:
            continue
        if start <= comment_date <= end:
            filtered.append(comment)
    return filtered


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _average_rating(comments: list[dict[str, Any]]) -> float | None:
    ratings = []
    for comment in comments:
        rating = comment.get("rating")
        if rating in (None, ""):
            continue
        try:
            ratings.append(float(rating))
        except (TypeError, ValueError):
            continue
    if not ratings:
        return None
    return sum(ratings) / len(ratings)


def _format_product_label(row: dict[str, Any]) -> str:
    name = row.get("name") or row.get("parent_product_id")
    return f"{name} · {row.get('parent_product_id')} · {row.get('review_count', 0)} {pick('条评论', 'reviews')}"


def _format_session_description(session: dict[str, Any]) -> str:
    start = str(session.get("date_range_start") or "")
    end = str(session.get("date_range_end") or "")
    if start and end:
        return f"{start} ~ {end}"
    return str(session.get("created_at") or pick("最新批次", "Latest Batch"))


def _extract_asin(session: dict[str, Any] | None, product_row: dict[str, Any]) -> str:
    if session and session.get("variant_ref_id"):
        return f"Variant {session['variant_ref_id']}"
    return str(product_row.get("parent_product_id") or "--")


def _compare_language(section_key: str) -> str:
    return str(st.session_state.get(_compare_language_key(section_key), "en"))


def _compare_language_key(section_key: str) -> str:
    return f"compare_language_{section_key}"
