"""产品管理页面。"""

from __future__ import annotations

from typing import Any

import psycopg2
import streamlit as st

from review_analyzer.auth import get_current_user_id
from review_analyzer.i18n import pick, role_label
from review_analyzer.page_shell import render_page_header
from review_analyzer.product_store import (
    LIFECYCLE_OPTIONS,
    VARIANT_STATUS_OPTIONS,
    create_product,
    create_variant,
    get_product_overview_rows,
)

LIFECYCLE_LABELS = {
    "research": {"zh": "调研期", "en": "Research"},
    "launch": {"zh": "新品期", "en": "Launch"},
    "growth": {"zh": "成长期", "en": "Growth"},
    "mature": {"zh": "成熟期", "en": "Mature"},
    "decline": {"zh": "衰退期", "en": "Decline"},
}

VARIANT_STATUS_LABELS = {
    "active": {"zh": "在售", "en": "Active"},
    "paused": {"zh": "暂停", "en": "Paused"},
    "clearance": {"zh": "清仓", "en": "Clearance"},
    "retired": {"zh": "下线", "en": "Retired"},
}

OWNER_ROLE_OPTIONS = ["运营", "产研", "质检", "管理者", "跨团队"]


def _lifecycle_label(value: str | None) -> str:
    if not value:
        return pick("未设置", "Not set")
    mapping = LIFECYCLE_LABELS.get(value)
    if not mapping:
        return value
    return pick(mapping["zh"], mapping["en"])


def _variant_status_label(value: str | None) -> str:
    if not value:
        return "—"
    mapping = VARIANT_STATUS_LABELS.get(value)
    if not mapping:
        return value
    return pick(mapping["zh"], mapping["en"])


def render_products() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning(pick("请先登录", "Please log in first."))
        return

    render_page_header(
        pick("产品管理", "Product Management"),
        pick(
            "用产品组沉淀评论资产，逐步接上变体、行动事项和复盘追踪。",
            "Use product groups to accumulate review assets, then connect variants, action items, and follow-up tracking.",
        ),
        path=pick("核心工作流 / 产品管理", "Core Workflow / Product Management"),
    )

    _render_product_create_form(user_id)
    product_rows = get_product_overview_rows(user_id)

    if not product_rows:
        st.info(pick("暂无产品档案。先上传评论，或新建一个产品组。", "No product profiles yet. Upload reviews first or create a product group."))
        return

    _ensure_selected_product(product_rows)
    selected_row = _get_selected_product(product_rows)
    if selected_row is None:
        selected_row = product_rows[0]

    col_list, col_detail = st.columns([1, 1.6], gap="large")
    with col_list:
        _render_product_list(product_rows, selected_row)
    with col_detail:
        _render_product_detail(user_id, selected_row)


def _render_product_create_form(user_id: int) -> None:
    with st.expander(pick("新建产品组", "Create Product Group"), expanded=False):
        with st.form("create_product_form"):
            col1, col2 = st.columns(2)
            with col1:
                parent_product_id = st.text_input(
                    pick("父体产品编号 *", "Parent Product ID *"),
                    placeholder=pick("例如：BEDFRAME-PARENT-001", "Example: BEDFRAME-PARENT-001"),
                    key="product_parent_product_id",
                )
            with col2:
                product_name = st.text_input(
                    pick("产品组名称", "Product Group Name"),
                    placeholder=pick("例如：带灯床架", "Example: Bed Frame with Lights"),
                    key="product_name",
                )

            col3, col4 = st.columns(2)
            with col3:
                platform = st.text_input(pick("平台", "Platform"), placeholder="Amazon / Walmart", key="product_platform")
            with col4:
                category = st.text_input(pick("类目", "Category"), placeholder=pick("家具家居", "Furniture & Home"), key="product_category")

            col5, col6, col7 = st.columns(3)
            with col5:
                lifecycle_stage = st.selectbox(
                    pick("生命周期", "Lifecycle"),
                    LIFECYCLE_OPTIONS,
                    index=LIFECYCLE_OPTIONS.index("growth"),
                    format_func=_lifecycle_label,
                    key="product_lifecycle_stage",
                )
            with col6:
                current_version = st.text_input(pick("当前版本", "Current Version"), value="V1", key="product_current_version")
            with col7:
                production_cycle_days = st.number_input(
                    pick("生产周期（天）", "Production Cycle (Days)"),
                    min_value=0,
                    value=0,
                    step=1,
                    key="product_production_cycle_days",
                )

            core_selling_points = st.text_area(
                pick("核心卖点", "Core Selling Points"),
                placeholder=pick("例如：带灯、快装、静音支撑", "Example: built-in light, easy assembly, quiet support"),
                key="product_core_selling_points",
                height=90,
            )
            main_competitors = st.text_input(
                pick("主要竞品", "Main Competitors"),
                placeholder=pick("选填，多个竞品可用逗号分隔", "Optional, separate multiple competitors with commas"),
                key="product_main_competitors",
            )
            owner_role = st.selectbox(
                pick("当前负责人", "Owner Role"),
                OWNER_ROLE_OPTIONS,
                index=0,
                format_func=role_label,
                key="product_owner_role",
            )

            submitted = st.form_submit_button(pick("保存产品组", "Save Product Group"), type="primary", use_container_width=True)
            if submitted:
                if not parent_product_id.strip():
                    st.error(pick("请填写父体产品编号", "Please enter a parent product ID."))
                    return
                try:
                    create_product(
                        user_id,
                        {
                            "parent_product_id": parent_product_id.strip(),
                            "name": product_name.strip() or None,
                            "platform": platform.strip() or None,
                            "category": category.strip() or None,
                            "lifecycle_stage": lifecycle_stage,
                            "current_version": current_version.strip() or "V1",
                            "core_selling_points": core_selling_points.strip() or None,
                            "main_competitors": main_competitors.strip() or None,
                            "owner_role": owner_role,
                            "production_cycle_days": int(production_cycle_days) or None,
                        },
                    )
                    st.success(pick("产品组已保存", "Product group saved."))
                    st.rerun()
                except psycopg2.errors.UniqueViolation:
                    st.error(pick("该父体产品编号已存在，请换一个编号。", "That parent product ID already exists. Please use a different one."))
                except psycopg2.errors.UndefinedTable:
                    st.error(pick("数据库还未执行 V2.5 schema，请先在 Supabase 中同步 `supabase_schema.sql`。", "The V2.5 schema has not been applied yet. Please sync `supabase_schema.sql` in Supabase first."))
                except Exception as exc:
                    st.error(f"{pick('保存产品组失败：', 'Failed to save product group: ')}{exc}")


def _ensure_selected_product(product_rows: list[dict[str, Any]]) -> None:
    default_product_id = product_rows[0]["parent_product_id"]
    if "products_selected_parent_id" not in st.session_state:
        st.session_state["products_selected_parent_id"] = default_product_id

    available_ids = {row["parent_product_id"] for row in product_rows}
    if st.session_state["products_selected_parent_id"] not in available_ids:
        st.session_state["products_selected_parent_id"] = default_product_id


def _get_selected_product(product_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    selected_parent_id = st.session_state.get("products_selected_parent_id")
    for row in product_rows:
        if row["parent_product_id"] == selected_parent_id:
            return row
    return None


def _render_product_list(product_rows: list[dict[str, Any]], selected_row: dict[str, Any]) -> None:
    st.markdown(f"**{pick('产品组列表', 'Product Groups')}**")
    for row in product_rows:
        is_selected = row["parent_product_id"] == selected_row["parent_product_id"]
        button_label = _build_product_button_label(row)
        if st.button(
            button_label,
            key=f"product_card_{row['parent_product_id']}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            st.session_state["products_selected_parent_id"] = row["parent_product_id"]
            st.rerun()


def _build_product_button_label(row: dict[str, Any]) -> str:
    product_name = row.get("name") or row["parent_product_id"]
    neg_rate = f"{row['negative_rate']:.1f}%"
    product_type = pick("历史产品", "Archived from History") if row.get("is_archived_from_sessions") else pick("已建档", "Profile Created")
    return (
        f"{product_name}\n"
        f"{row['parent_product_id']} | {product_type} | {row['review_count']} {pick('条评论', 'reviews')} | {pick('差评率', 'Negative Rate')} {neg_rate}"
    )


def _render_product_detail(user_id: int, product_row: dict[str, Any]) -> None:
    title = product_row.get("name") or product_row["parent_product_id"]
    st.markdown(
        f"""
        <div class="product-block" style="padding:24px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:24px;font-weight:700;color:#202020;font-family:'Montserrat',system-ui,sans-serif;">
                        {title}
                    </div>
                    <div style="font-size:13px;color:#828282;margin-top:4px;">
                        {pick('父体产品编号：', 'Parent Product ID: ')}{product_row['parent_product_id']}
                    </div>
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;">
                    <span class="tag tag-platform">{product_row.get('platform') or pick('未设置平台', 'Platform not set')}</span>
                    <span class="tag tag-topic">{_lifecycle_label(str(product_row.get('lifecycle_stage')))}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if product_row.get("is_archived_from_sessions"):
        st.info(pick("这个产品来自历史评论数据，当前还没有正式产品档案。你可以先查看资产，再补建产品组。", "This product comes from historical review data and does not have a formal profile yet. You can review the asset first, then create the product group later."))

    metric_cols = st.columns(5)
    metrics = [
        (pick("评论总量", "Total Reviews"), f"{product_row['review_count']}", "◆"),
        (pick("好评率", "Positive Rate"), f"{product_row['positive_rate']:.1f}%", "▲"),
        (pick("差评率", "Negative Rate"), f"{product_row['negative_rate']:.1f}%", "▼"),
        (pick("当前版本", "Current Version"), product_row.get("current_version") or "V1", "◎"),
        (pick("待复盘", "Pending Follow-up"), f"{product_row['pending_review_count']}", "↺"),
    ]
    for index, (label, value, icon) in enumerate(metrics):
        with metric_cols[index]:
            st.markdown(
                f"""
                <div class="metric-card purple" style="padding:18px 20px;">
                    <div class="metric-icon">{icon}</div>
                    <div class="metric-val" style="font-size:24px;">{value}</div>
                    <div class="metric-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    base_cols = st.columns(3)
    with base_cols[0]:
        st.markdown(f"**{pick('类目', 'Category')}**  \n{product_row.get('category') or pick('未设置', 'Not set')}")
    with base_cols[1]:
        st.markdown(f"**{pick('负责人', 'Owner')}**  \n{role_label(product_row.get('owner_role')) if product_row.get('owner_role') else pick('未设置', 'Not set')}")
    with base_cols[2]:
        cycle_value = product_row.get("production_cycle_days")
        cycle_text = f"{cycle_value} {pick('天', 'days')}" if cycle_value else pick("未设置", "Not set")
        st.markdown(f"**{pick('生产周期', 'Production Cycle')}**  \n{cycle_text}")

    insight_cols = st.columns(3)
    with insight_cols[0]:
        st.markdown(
            f"""
            <div class="action-card">
                <h4 style="margin:0 0 10px;font-size:15px;">{pick('最大问题', 'Top Issue')}</h4>
                <div style="font-size:15px;color:#202020;">{product_row.get('top_issue') or pick('暂无问题标签', 'No issue tag yet')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with insight_cols[1]:
        st.markdown(
            f"""
            <div class="action-card">
                <h4 style="margin:0 0 10px;font-size:15px;">{pick('最大亮点', 'Top Highlight')}</h4>
                <div style="font-size:15px;color:#202020;">{product_row.get('top_highlight') or pick('暂无亮点标签', 'No highlight tag yet')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with insight_cols[2]:
        latest_session = product_row.get("latest_session_label") or pick("暂无上传批次", "No upload batch yet")
        st.markdown(
            f"""
            <div class="action-card">
                <h4 style="margin:0 0 10px;font-size:15px;">{pick('最近批次', 'Latest Batch')}</h4>
                <div style="font-size:15px;color:#202020;">{latest_session}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if product_row.get("core_selling_points"):
        st.markdown(f"**{pick('核心卖点', 'Core Selling Points')}**  \n{product_row['core_selling_points']}")
    if product_row.get("main_competitors"):
        st.markdown(f"**{pick('主要竞品', 'Main Competitors')}**  \n{product_row['main_competitors']}")

    st.markdown(f"**{pick('变体 SKU 列表', 'Variant SKU List')}**")
    variants = product_row.get("variants", [])
    if variants:
        variant_rows = []
        for variant in variants:
            variant_rows.append(
                {
                    "SKU": variant.get("variant_sku") or "—",
                    "Child ASIN": variant.get("child_asin") or "—",
                    pick("颜色", "Color"): variant.get("color") or "—",
                    pick("尺码", "Size"): variant.get("size") or "—",
                    pick("款式", "Style"): variant.get("style") or "—",
                    pick("材质", "Material"): variant.get("material") or "—",
                    pick("状态", "Status"): _variant_status_label(str(variant.get("status"))),
                    pick("上架时间", "Launch Time"): variant.get("launched_at") or "—",
                }
            )
        st.dataframe(variant_rows, use_container_width=True, hide_index=True)
    else:
        st.info(pick("未绑定变体。后续上传流程绑定到变体前，不会阻塞父体产品视图。", "No variants are linked yet. The parent-product view will still work before future uploads bind to variants."))

    _render_variant_create_form(user_id, product_row)


def _render_variant_create_form(user_id: int, product_row: dict[str, Any]) -> None:
    if not product_row.get("id"):
        return

    with st.expander(pick("新增变体 SKU", "Add Variant SKU"), expanded=False):
        with st.form(f"create_variant_form_{product_row['id']}"):
            col1, col2 = st.columns(2)
            with col1:
                variant_sku = st.text_input(pick("变体 SKU *", "Variant SKU *"), key=f"variant_sku_{product_row['id']}")
            with col2:
                child_asin = st.text_input("Child ASIN", key=f"variant_child_asin_{product_row['id']}")

            col3, col4 = st.columns(2)
            with col3:
                color = st.text_input(pick("颜色", "Color"), key=f"variant_color_{product_row['id']}")
            with col4:
                size = st.text_input(pick("尺码", "Size"), key=f"variant_size_{product_row['id']}")

            col5, col6 = st.columns(2)
            with col5:
                style = st.text_input(pick("款式", "Style"), key=f"variant_style_{product_row['id']}")
            with col6:
                material = st.text_input(pick("材质", "Material"), key=f"variant_material_{product_row['id']}")

            col7, col8 = st.columns(2)
            with col7:
                status = st.selectbox(
                    pick("状态", "Status"),
                    VARIANT_STATUS_OPTIONS,
                    format_func=_variant_status_label,
                    key=f"variant_status_{product_row['id']}",
                )
            with col8:
                launched_at = st.text_input(
                    pick("上架时间", "Launch Time"),
                    placeholder=pick("例如：2026-06", "Example: 2026-06"),
                    key=f"variant_launched_at_{product_row['id']}",
                )

            submitted = st.form_submit_button(pick("保存变体", "Save Variant"), type="primary", use_container_width=True)
            if submitted:
                if not variant_sku.strip():
                    st.error(pick("请填写变体 SKU", "Please enter a variant SKU."))
                    return
                try:
                    create_variant(
                        user_id,
                        int(product_row["id"]),
                        {
                            "variant_sku": variant_sku.strip(),
                            "child_asin": child_asin.strip() or None,
                            "color": color.strip() or None,
                            "size": size.strip() or None,
                            "style": style.strip() or None,
                            "material": material.strip() or None,
                            "status": status,
                            "launched_at": launched_at.strip() or None,
                        },
                    )
                    st.success(pick("变体已保存", "Variant saved."))
                    st.rerun()
                except psycopg2.errors.UniqueViolation:
                    st.error(pick("该变体 SKU 已存在，请换一个编号。", "That variant SKU already exists. Please use a different one."))
                except psycopg2.errors.UndefinedTable:
                    st.error(pick("数据库还未执行 V2.5 schema，请先在 Supabase 中同步 `supabase_schema.sql`。", "The V2.5 schema has not been applied yet. Please sync `supabase_schema.sql` in Supabase first."))
                except Exception as exc:
                    st.error(f"{pick('保存变体失败：', 'Failed to save variant: ')}{exc}")
