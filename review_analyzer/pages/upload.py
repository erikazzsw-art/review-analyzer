"""上传用户评论页面 — 三步流程"""

import hashlib
import json
import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from review_analyzer.auth import get_current_user_id
from review_analyzer.config import CATEGORY_TAGS, DEFAULT_CATEGORY
from review_analyzer.page_shell import render_page_header
from review_analyzer.i18n import pick, role_label
from review_analyzer.database import (
    create_session,
    add_comments_batch,
    get_existing_hashes,
    get_sessions,
    get_user_product_count,
    get_unprocessed_comments,
    update_comment_analysis,
    update_session_stats,
)
from review_analyzer.parser import parse_file
from review_analyzer.analyzer import analyze_batch, get_api_key, PROMPT_VERSION
from review_analyzer.notifier import auto_notify_after_analysis
from review_analyzer.paddle_billing import is_pro_user
from review_analyzer.product_store import create_product, get_product_overview_rows, get_variants
from review_analyzer.rag import embed_session_comments
from review_analyzer.workflow_prompts import WORKFLOW_PURPOSES, get_workflow_hint, get_workflow_purpose_label


def _render_step_indicator(current: int) -> None:
    """渲染步骤指示器"""
    steps = pick(
        ["① 填写产品信息", "② 上传评论文件", "③ 分析中"],
        ["① Product Info", "② Upload File", "③ Analyzing"],
    )
    html = '<div class="step-indicator">'
    for i, label in enumerate(steps):
        cls = "step-item"
        if i + 1 == current:
            cls += " active"
        elif i + 1 < current:
            cls += " done"
        html += f'<div class="{cls}">{label}</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


PLATFORM_OPTIONS = [
    "请选择...",
    "Amazon",
    "Walmart",
    "Shopee",
    "Temu",
    "eBay",
    "AliExpress",
    "Mercado Libre",
    "其他",
]

VARIANT_BINDING_MODES = {
    "auto": {"zh": "自动识别子变体", "en": "Auto-detect Variant"},
    "group_only": {"zh": "仅绑定产品组", "en": "Bind Group Only"},
    "manual": {"zh": "手动指定子变体", "en": "Choose Variant Manually"},
}

CATEGORY_LABELS = {
    "家具家居": "Furniture & Home",
    "3C电子": "Consumer Electronics",
    "服装鞋帽": "Fashion",
    "母婴用品": "Baby Products",
    "运动户外": "Sports & Outdoors",
    "美妆个护": "Beauty & Personal Care",
    "厨房用品": "Kitchenware",
    "宠物用品": "Pet Supplies",
}

IDENTIFIER_KEYWORDS = (
    "sku",
    "asin",
    "child_asin",
    "childasin",
    "seller_sku",
    "seller sku",
    "merchant_sku",
    "merchant sku",
    "product_id",
    "product id",
    "item_id",
    "item id",
)


def _platform_label(value: str) -> str:
    if value == "请选择...":
        return pick("请选择...", "Please select...")
    if value == "其他":
        return pick("其他", "Other")
    return value


def _category_label(value: str) -> str:
    if value == "请选择...":
        return pick("请选择...", "Please select...")
    return pick(value, CATEGORY_LABELS.get(value, value))


def _variant_binding_mode_label(value: str) -> str:
    mapping = VARIANT_BINDING_MODES.get(value)
    if not mapping:
        return value
    return pick(mapping["zh"], mapping["en"])


def _format_product_option(row: dict) -> str:
    product_name = row.get("name") or row.get("parent_product_id")
    category = row.get("category") or pick("未设类目", "No category")
    platform = row.get("platform") or pick("未设平台", "No platform")
    category = _category_label(category) if category in CATEGORY_LABELS or category == "请选择..." else category
    return f"{product_name} | {row.get('parent_product_id')} | {platform} | {category}"


def _sync_existing_product_defaults(selected_product: dict) -> None:
    signature = f"{selected_product.get('id')}::{selected_product.get('parent_product_id')}"
    if st.session_state.get("upload_existing_binding_signature") == signature:
        return

    st.session_state["upload_product_id"] = selected_product.get("parent_product_id") or ""
    st.session_state["upload_product_name"] = selected_product.get("name") or ""
    st.session_state["upload_platform"] = (
        selected_product.get("platform")
        if selected_product.get("platform") in PLATFORM_OPTIONS
        else "请选择..."
    )
    st.session_state["upload_category"] = (
        selected_product.get("category")
        if selected_product.get("category") in CATEGORY_TAGS
        else "请选择..."
    )
    st.session_state["upload_version"] = selected_product.get("current_version") or "V1"
    st.session_state["upload_existing_binding_signature"] = signature


def _normalize_identifier(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    return text or None


def _extract_identifier_candidates(df: pd.DataFrame) -> set[str]:
    candidates: set[str] = set()
    for _, row in df.iterrows():
        raw_data = row.get("raw_data")
        if not raw_data:
            continue
        try:
            payload = json.loads(raw_data)
        except (TypeError, json.JSONDecodeError):
            continue

        for key, value in payload.items():
            key_text = str(key).strip().lower()
            if not any(keyword in key_text for keyword in IDENTIFIER_KEYWORDS):
                continue
            normalized = _normalize_identifier(value)
            if normalized:
                candidates.add(normalized)

    return candidates


def _resolve_variant_binding(
    user_id: int,
    product_ref_id: int | None,
    df: pd.DataFrame,
    variant_binding_mode: str,
    manual_variant_id: int | None,
) -> tuple[int | None, str]:
    if not product_ref_id:
        return None, pick("当前未绑定产品档案，将仅按产品组编号分析。", "No product profile is linked yet. This batch will be analyzed at the product-group level only.")

    if variant_binding_mode == "group_only":
        return None, pick("已设置为仅绑定产品组，本次不会绑定到子变体。", "This batch is set to bind at the product-group level only. No child variant will be linked.")

    variants = get_variants(user_id, product_ref_id)
    if not variants:
        return None, pick("当前产品组还没有子变体档案，本次默认只绑定产品组。", "This product group does not have variant profiles yet, so the batch will stay at the product-group level.")

    if variant_binding_mode == "manual":
        if not manual_variant_id:
            return None, pick("未选择手动变体，本次默认只绑定产品组。", "No manual variant was selected, so the batch will stay at the product-group level.")
        variant = next((item for item in variants if int(item["id"]) == int(manual_variant_id)), None)
        if not variant:
            return None, pick("手动指定的变体不存在，本次默认只绑定产品组。", "The selected manual variant does not exist, so the batch will stay at the product-group level.")
        return int(variant["id"]), f"{pick('已手动绑定到子变体：', 'Manually bound to variant: ')}{variant.get('variant_sku') or variant.get('child_asin')}"

    candidate_identifiers = _extract_identifier_candidates(df)
    if not candidate_identifiers:
        return None, pick("未在文件里识别到 ASIN / SKU 字段，默认只绑定到产品组。", "No ASIN/SKU field was detected in the file, so the batch will stay at the product-group level.")

    matched_variants = []
    for variant in variants:
        variant_sku = _normalize_identifier(variant.get("variant_sku"))
        child_asin = _normalize_identifier(variant.get("child_asin"))
        if variant_sku and variant_sku in candidate_identifiers:
            matched_variants.append(variant)
            continue
        if child_asin and child_asin in candidate_identifiers:
            matched_variants.append(variant)

    unique_variant_ids = {int(item["id"]) for item in matched_variants}
    if not unique_variant_ids:
        return None, pick("文件里有 ASIN / SKU 字段，但未匹配到现有子变体，默认只绑定到产品组。", "The file contains ASIN/SKU fields, but none matched an existing variant, so the batch will stay at the product-group level.")
    if len(unique_variant_ids) > 1:
        return None, pick("文件里识别到多个子变体，本次先只绑定产品组，避免把混合批次误绑到单一变体。", "Multiple child variants were detected in the file. The batch will stay at the product-group level to avoid incorrect single-variant binding.")

    matched_variant = matched_variants[0]
    return int(matched_variant["id"]), (
        f"{pick('已自动匹配到子变体：', 'Automatically matched variant: ')}{matched_variant.get('variant_sku') or matched_variant.get('child_asin')}"
    )


def _start_analysis_step() -> None:
    """进入分析步骤。"""
    cleaned_df = st.session_state.get("upload_df_clean")
    if cleaned_df is None:
        st.error(pick("请先上传文件", "Please upload a file first."))
        return
    if cleaned_df.empty:
        st.error(pick("当前没有可分析的新评论，请更换文件后再试", "There are no new reviews available to analyze. Please try a different file."))
        return

    st.session_state["upload_step"] = 3
    st.rerun()


def render_upload() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning(pick("请先登录", "Please log in first."))
        return

    render_page_header(
        pick("上传评论", "Upload Reviews"),
        pick("填写产品信息 → 上传评论文件 → AI 自动分析。", "Fill in product info, upload the file, and let AI analyze it automatically."),
        path=pick("核心工作流 / 上传评论", "Core Workflow / Upload Reviews"),
    )

    if "upload_step" not in st.session_state:
        st.session_state["upload_step"] = 1

    current_step = st.session_state["upload_step"]
    _render_step_indicator(current_step)

    # ============================================================
    # Step 1: 填写产品信息
    # ============================================================
    if current_step == 1:
        product_rows = get_product_overview_rows(user_id)
        managed_product_rows = [row for row in product_rows if row.get("id")]
        default_binding_mode = "existing" if managed_product_rows else "new"

        workflow_purpose = st.selectbox(
            pick("工作目的 *", "Workflow Purpose *"),
            WORKFLOW_PURPOSES,
            format_func=get_workflow_purpose_label,
            key="upload_workflow_purpose",
        )
        workflow_hint = get_workflow_hint(workflow_purpose)
        if workflow_hint:
            st.info(workflow_hint)

        binding_mode_options = ["new"] if not managed_product_rows else ["existing", "new"]
        binding_mode = st.radio(
            pick("产品绑定方式", "Product Binding Mode"),
            binding_mode_options,
            key="upload_binding_mode",
            format_func=lambda value: pick("绑定已有产品组", "Bind Existing Product Group") if value == "existing" else pick("新建产品组", "Create New Product Group"),
            horizontal=True,
            index=binding_mode_options.index(default_binding_mode),
        )

        selected_product = None
        product_ref_id = None
        variant_binding_mode = "group_only"
        manual_variant_id = None
        variants: list[dict] = []

        if binding_mode == "existing":
            selected_product_id = st.selectbox(
                pick("选择已有产品组 *", "Select Existing Product Group *"),
                [int(row["id"]) for row in managed_product_rows],
                key="upload_existing_product_ref_id",
                format_func=lambda product_id: _format_product_option(
                    next(row for row in managed_product_rows if int(row["id"]) == int(product_id))
                ),
            )
            selected_product = next(
                row for row in managed_product_rows if int(row["id"]) == int(selected_product_id)
            )
            product_ref_id = int(selected_product["id"])
            _sync_existing_product_defaults(selected_product)
            variants = get_variants(user_id, product_ref_id)

            variant_binding_mode = st.radio(
                pick("变体绑定方式", "Variant Binding Mode"),
                list(VARIANT_BINDING_MODES.keys()),
                key="upload_variant_binding_mode",
                format_func=_variant_binding_mode_label,
                horizontal=True,
            )
            if variant_binding_mode == "manual":
                if variants:
                    manual_variant_id = st.selectbox(
                        pick("手动选择子变体", "Choose Child Variant Manually"),
                        [int(item["id"]) for item in variants],
                        key="upload_manual_variant_id",
                        format_func=lambda variant_id: next(
                            (
                                f"{variant.get('variant_sku') or pick('未设 SKU', 'No SKU')}"
                                f" | {variant.get('child_asin') or pick('无 ASIN', 'No ASIN')}"
                            )
                            for variant in variants
                            if int(variant["id"]) == int(variant_id)
                        ),
                    )
                else:
                    st.warning(pick("当前产品组还没有子变体档案，手动绑定不可用。", "This product group does not have variant profiles yet, so manual binding is unavailable."))
                    variant_binding_mode = "group_only"

        col1, col2 = st.columns(2)
        with col1:
            product_id = st.text_input(
                pick("产品编号 *", "Product ID *"),
                placeholder=pick("SKU 或任何可识别该产品的唯一编码", "SKU or any unique identifier for this product"),
                key="upload_product_id",
                disabled=binding_mode == "existing",
            )
        with col2:
            product_name = st.text_input(
                pick("产品中文名称", "Product Name"),
                placeholder=pick("选填，如：无线蓝牙耳机", "Optional, e.g. Wireless Bluetooth Earbuds"),
                key="upload_product_name",
            )

        col3, col4 = st.columns(2)
        with col3:
            platform = st.selectbox(
                pick("平台来源 *", "Platform *"),
                PLATFORM_OPTIONS,
                format_func=_platform_label,
                key="upload_platform",
            )
        with col4:
            categories = ["请选择..."] + list(CATEGORY_TAGS.keys())
            category = st.selectbox(
                pick("产品类目 *", "Category *"),
                categories,
                format_func=_category_label,
                key="upload_category",
            )

        col5, col6 = st.columns(2)
        with col5:
            version = st.text_input(
                pick("版本号 *", "Version *"),
                placeholder=pick("如：V1、V2", "e.g. V1, V2"),
                key="upload_version",
            )
        with col6:
            st.write(pick("分析时间段（选填）", "Analysis Date Range (Optional)"))
            date_col1, date_col2 = st.columns(2)
            with date_col1:
                date_start = st.date_input(pick("开始日期", "Start Date"), value=None, key="upload_date_start",
                                           label_visibility="collapsed")
            with date_col2:
                date_end = st.date_input(pick("结束日期", "End Date"), value=None, key="upload_date_end",
                                         label_visibility="collapsed")

        version_notes = st.text_area(
            pick("版本升级说明（选填）", "Version Update Notes (Optional)"),
            placeholder=pick("如：新增折叠床腿，优化包装缓冲材料", "e.g. Added folding legs and improved packaging cushioning"),
            key="upload_version_notes",
            height=80,
        )

        if binding_mode == "existing" and selected_product:
            st.caption(
                pick("已绑定到产品组：", "Bound to product group: ")
                +
                f"{selected_product.get('name') or selected_product.get('parent_product_id')} "
                f"({selected_product.get('parent_product_id')})"
            )
        elif binding_mode == "new":
            st.caption(pick("本次会在分析开始前自动创建产品组，并先绑定到产品组层级。", "A product group will be created automatically before analysis and this batch will first bind at the group level."))

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn = st.columns([3, 1])
        with col_btn[1]:
            if st.button(pick("下一步：上传文件 →", "Next: Upload File →"), type="primary", use_container_width=True):
                if not product_id:
                    st.error(pick("请填写产品编号", "Please enter a product ID."))
                elif (
                    binding_mode == "new"
                    and any(str(row.get("parent_product_id")) == product_id for row in managed_product_rows)
                ):
                    st.error(pick("该产品组已存在，请改为“绑定已有产品组”，避免重复建档。", "That product group already exists. Switch to 'Bind Existing Product Group' to avoid duplicate profiles."))
                elif platform == "请选择...":
                    st.error(pick("请选择平台来源", "Please select a platform."))
                elif category == "请选择...":
                    st.error(pick("请选择产品类目", "Please select a category."))
                elif not version:
                    st.error(pick("请填写版本号", "Please enter a version."))
                elif (
                    not is_pro_user(user_id)
                    and get_user_product_count(user_id) >= 1
                    and product_id not in {s["product_id"] for s in get_sessions(user_id)}
                ):
                    st.error(pick("Free 版可分析 1 个产品。升级 Pro 后可继续添加更多产品。", "The Free plan supports analysis for 1 product. Upgrade to Pro to add more products."))
                else:
                    final_product_id = (
                        selected_product.get("parent_product_id")
                        if binding_mode == "existing" and selected_product
                        else product_id
                    )
                    st.session_state["upload_info"] = {
                        "product_id": final_product_id,
                        "product_name": product_name,
                        "platform": platform,
                        "category": category,
                        "version": version,
                        "date_start": str(date_start) if date_start else None,
                        "date_end": str(date_end) if date_end else None,
                        "version_notes": version_notes or None,
                        "workflow_purpose": workflow_purpose,
                        "binding_mode": binding_mode,
                        "product_ref_id": product_ref_id,
                        "variant_binding_mode": variant_binding_mode,
                        "manual_variant_id": manual_variant_id,
                    }
                    st.session_state["upload_step"] = 2
                    st.rerun()

    # ============================================================
    # Step 2: 上传文件
    # ============================================================
    elif current_step == 2:
        upload_info = st.session_state.get("upload_info", {})
        analysis_ready_count = 0
        binding_summary = (
            f"{pick('工作目的', 'Purpose')}: {get_workflow_purpose_label(upload_info.get('workflow_purpose'))} | "
            f"{pick('产品组', 'Product Group')}: {upload_info.get('product_id')} | "
            f"{pick('版本', 'Version')}: {upload_info.get('version')}"
        )
        st.caption(binding_summary)

        st.markdown("""
        <div style="background:linear-gradient(90deg,#FFEAEA,#FFF3E0);border:1px solid #FDCB6E;
                    border-radius:12px;padding:16px 20px;margin-bottom:16px;
                    display:flex;align-items:center;gap:12px;font-size:14px;">
            <span style="font-size:24px;">⚠️</span>
            <span>%s</span>
        </div>
        """ % pick("上传的文件必须包含「评论内容」和「日期」字段，否则将无法上传成功。", "The uploaded file must include both review content and date fields, or the upload will fail."),
        unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            pick("拖拽文件到此处，或点击选择", "Drag a file here or click to upload"),
            type=["csv", "xlsx", "xls", "docx", "txt"],
            key="upload_file",
            help=pick("支持 CSV / XLSX / DOCX / TXT 格式", "Supports CSV / XLSX / DOCX / TXT"),
        )

        if uploaded_file:
            try:
                import tempfile
                suffix = os.path.splitext(uploaded_file.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                file_type = suffix.lstrip(".").lower()
                df = parse_file(tmp_path, file_type)
                os.unlink(tmp_path)
                st.session_state["upload_df"] = df

                st.success(pick(f"文件解析成功，共 {len(df)} 条评论", f"File parsed successfully with {len(df)} reviews"))

                # 过滤完全空行（无内容、无评分、无标题）
                def _is_empty_row(row):
                    content = str(row.get("content", "")).strip() if pd.notna(row.get("content")) else ""
                    rating = row.get("rating")
                    has_rating = pd.notna(rating) if rating is not None else False
                    reviewer = str(row.get("reviewer", "")).strip() if pd.notna(row.get("reviewer")) else ""
                    return not content and not has_rating and not reviewer

                empty_mask = df.apply(_is_empty_row, axis=1)
                empty_count = empty_mask.sum()
                if empty_count > 0:
                    st.info(pick(f"已跳过 {empty_count} 条完全空白的行", f"Skipped {empty_count} completely blank rows"))
                    df = df[~empty_mask].reset_index(drop=True)

                # 重复检测：用所有关键字段组合 hash
                info = st.session_state.get("upload_info", {})
                existing_hashes = get_existing_hashes(user_id, info.get("product_id", ""))

                def _compute_row_hash(row):
                    parts = [
                        str(row.get("content", "")) if pd.notna(row.get("content")) else "",
                        str(row.get("rating", "")) if pd.notna(row.get("rating")) else "",
                        str(row.get("date", "")) if pd.notna(row.get("date")) else "",
                        str(row.get("reviewer", "")) if pd.notna(row.get("reviewer")) else "",
                        str(row.get("source", "")) if pd.notna(row.get("source")) else "",
                        str(row.get("raw_data", "")) if pd.notna(row.get("raw_data")) else "",
                    ]
                    return hashlib.md5("|".join(parts).encode()).hexdigest()

                df["_hash"] = df.apply(_compute_row_hash, axis=1)
                duplicates = df[df["_hash"].isin(existing_hashes)]
                new_records = df[~df["_hash"].isin(existing_hashes)]

                if len(duplicates) > 0:
                    if len(new_records) == 0:
                        st.error(pick(f"上传数据重复：全部 {len(duplicates)} 条评论与已有记录相同，请勿重复上传", f"Duplicate upload: all {len(duplicates)} reviews already exist. Please do not upload them again."))
                        st.session_state["upload_df_clean"] = new_records.drop(columns=["_hash"])
                    else:
                        st.warning(pick(f"检测到 {len(duplicates)} 条重复评论（将自动跳过），剩余 {len(new_records)} 条待分析", f"Detected {len(duplicates)} duplicate reviews and skipped them automatically. {len(new_records)} reviews remain for analysis."))
                        st.session_state["upload_df_clean"] = new_records.drop(columns=["_hash"])
                else:
                    st.session_state["upload_df_clean"] = df.drop(columns=["_hash"])

                cleaned_df = st.session_state["upload_df_clean"]
                variant_ref_id, variant_binding_message = _resolve_variant_binding(
                    user_id=user_id,
                    product_ref_id=upload_info.get("product_ref_id"),
                    df=cleaned_df,
                    variant_binding_mode=upload_info.get("variant_binding_mode", "group_only"),
                    manual_variant_id=upload_info.get("manual_variant_id"),
                )
                st.session_state["upload_info"]["variant_ref_id"] = variant_ref_id
                st.session_state["upload_info"]["variant_binding_message"] = variant_binding_message

                if variant_ref_id:
                    st.success(variant_binding_message)
                else:
                    st.info(variant_binding_message)

                analysis_ready_count = len(cleaned_df)
                if analysis_ready_count > 0:
                    st.markdown(
                        f"""
                        <div style="background:#fff8ef;border:1px solid #ffd7a8;border-radius:18px;
                                    padding:18px 20px;margin:14px 0 18px;">
                            <div style="font-size:16px;font-weight:700;color:#202020;margin-bottom:6px;">
                                %s
                            </div>
                            <div style="font-size:14px;color:#6f6877;">
                                %s
                            </div>
                        </div>
                        """ % (
                            pick("文件已准备好，可直接开始分析", "The file is ready for analysis"),
                            pick(
                                f"当前待分析 {analysis_ready_count} 条评论。点击下方按钮后会自动进入分析流程，分析完成后直接打开结果页。",
                                f"{analysis_ready_count} reviews are ready to analyze. Click below to start the analysis flow and open the results page automatically when it finishes.",
                            ),
                        ),
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        pick("开始分析并查看结果 →", "Start Analysis and Open Results →"),
                        key="upload_start_analysis_top",
                        type="primary",
                        use_container_width=True,
                    ):
                        _start_analysis_step()

                st.markdown(f"**📄 {pick('文件预览（前 5 行）', 'File Preview (First 5 Rows)')}**")
                st.dataframe(df.head(5), use_container_width=True)

            except Exception as e:
                st.error(f"{pick('文件解析失败：', 'Failed to parse file: ')}{str(e)}")

        st.markdown("<br>", unsafe_allow_html=True)
        col_back, col_next = st.columns([1, 1])
        with col_back:
            if st.button(pick("← 返回修改信息", "← Back to Product Info"), use_container_width=True):
                st.session_state["upload_step"] = 1
                st.rerun()
        with col_next:
            button_label = pick("开始分析并查看结果 →", "Start Analysis and Open Results →") if analysis_ready_count else pick("开始分析 →", "Start Analysis →")
            if st.button(button_label, type="primary", use_container_width=True, key="upload_start_analysis_bottom"):
                _start_analysis_step()

    # ============================================================
    # Step 3: 分析中
    # ============================================================
    elif current_step == 3:
        info = st.session_state.get("upload_info", {})
        df = st.session_state.get("upload_df_clean")

        if df is None or df.empty:
            st.error(pick("上传数据重复：所有评论与已有记录相同，无需重复分析", "Duplicate upload: all reviews already exist, so no re-analysis is needed."))
            if st.button(pick("返回", "Back")):
                st.session_state["upload_step"] = 1
                st.rerun()
            return

        st.markdown("""
        <div style="text-align:center;padding:40px 0 20px;">
            <div style="font-size:48px;margin-bottom:16px;">🔄</div>
            <div style="font-size:18px;font-weight:600;margin-bottom:8px;">%s</div>
            <div style="font-size:14px;color:#636E72;margin-bottom:8px;">
                %s
            </div>
        </div>
        """ % (
            pick("AI 正在分析评论...", "AI is analyzing the reviews..."),
            pick("正在提取产品问题与亮点，请耐心等待", "Extracting key issues and highlights. Please wait a moment."),
        ), unsafe_allow_html=True)

        progress_container = st.empty()
        status_text = st.empty()

        # 用 session_state 保证 create_session + add_comments_batch 只执行一次
        # Streamlit 脚本在分析期间可能因 WebSocket 心跳被重新执行
        session_id = st.session_state.get("analyzing_session_id")
        if session_id is None:
            product_ref_id = info.get("product_ref_id")
            if info.get("binding_mode") == "new":
                created_product_id = st.session_state.get("upload_created_product_ref_id")
                if created_product_id is None:
                    created_product_id = create_product(
                        user_id,
                        {
                            "parent_product_id": info.get("product_id"),
                            "name": info.get("product_name"),
                            "platform": info.get("platform"),
                            "category": info.get("category") or DEFAULT_CATEGORY,
                            "lifecycle_stage": "growth",
                            "current_version": info.get("version", "V1"),
                            "owner_role": "运营",
                        },
                    )
                    st.session_state["upload_created_product_ref_id"] = created_product_id
                product_ref_id = created_product_id
                info["product_ref_id"] = product_ref_id

            session_data = {
                "product_id": info.get("product_id"),
                "version": info.get("version", "V1"),
                "auto_title": (
                    f"{datetime.now().strftime('%Y-%m-%d')} | "
                    f"{info.get('product_id')} | {info.get('workflow_purpose')} | {len(df)}{pick('条', ' reviews')}"
                ),
                "date_range_start": info.get("date_start"),
                "date_range_end": info.get("date_end"),
                "total_reviews": len(df),
                "positive_count": 0,
                "negative_count": 0,
                "category": info.get("category"),
                "prompt_version": PROMPT_VERSION,
                "version_notes": info.get("version_notes"),
                "workflow_purpose": info.get("workflow_purpose"),
                "product_ref_id": product_ref_id,
                "variant_ref_id": info.get("variant_ref_id"),
            }
            session_id = create_session(user_id, session_data)
            st.session_state["analyzing_session_id"] = session_id

            # 准备并插入评论数据（同样只做一次）
            comments_to_insert = []
            for _, row in df.iterrows():
                content = str(row.get("content", "")) if pd.notna(row.get("content")) else ""
                rating_val = row.get("rating") if pd.notna(row.get("rating")) else None
                date_val = str(row.get("date", "")) if pd.notna(row.get("date")) else ""
                reviewer_val = str(row.get("reviewer", "")) if pd.notna(row.get("reviewer")) else ""
                source_val = str(row.get("source", "")) if pd.notna(row.get("source")) else ""
                raw_data_val = str(row.get("raw_data", "")) if pd.notna(row.get("raw_data")) else ""
                hash_parts = [content, str(rating_val or ""), date_val, reviewer_val, source_val, raw_data_val]
                comment = {
                    "product_id": info.get("product_id"),
                    "version": info.get("version", "V1"),
                    "content": content,
                    "rating": rating_val,
                    "date": date_val,
                    "reviewer": reviewer_val if reviewer_val else None,
                    "source": info.get("platform"),
                    "content_hash": hashlib.md5("|".join(hash_parts).encode()).hexdigest(),
                    "session_id": session_id,
                }
                comments_to_insert.append(comment)
            add_comments_batch(user_id, comments_to_insert)

        # AI 分析
        unprocessed = get_unprocessed_comments(user_id, session_id)
        category_name = info.get("category", DEFAULT_CATEGORY)

        embedding_state_key = f"embedding_done_{session_id}"
        if not st.session_state.get(embedding_state_key):
            try:
                status_text.text(pick("正在生成评论向量，用于 Ask your reviews...", "Generating review embeddings for Review Q&A..."))
                embedding_result = embed_session_comments(user_id, session_id)
                embedded_count = embedding_result.get("embedded", 0)
                if embedded_count:
                    st.toast(pick(f"已生成 {embedded_count} 条评论向量", f"Generated embeddings for {embedded_count} reviews"))
            except Exception as e:
                st.warning(f"{pick('评论向量生成失败，将使用文本检索兜底：', 'Embedding generation failed. Falling back to text retrieval: ')}{e}")
            finally:
                st.session_state[embedding_state_key] = True

        analysis_start_time = time.time()

        def _render_progress(percent: float, eta_text: str) -> None:
            progress_container.markdown(f"""
            <div style="max-width:500px;margin:0 auto 16px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <span style="font-size:14px;font-weight:600;color:#202020;">{percent:.0f}%</span>
                    <span style="font-size:13px;color:#636E72;">{eta_text}</span>
                </div>
                <div style="background:#F0F0F0;border-radius:10px;height:12px;overflow:hidden;">
                    <div style="background:linear-gradient(90deg,#FF8C00,#FFA500);height:100%;
                                border-radius:10px;width:{percent}%;transition:width 0.3s ease;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        _render_progress(0, pick("预计时间计算中...", "Estimating time..."))

        def progress_callback(current: int, total: int) -> None:
            percent = current / total * 100
            elapsed = time.time() - analysis_start_time
            if current > 0:
                avg_per_item = elapsed / current
                remaining_items = total - current
                eta_seconds = int(avg_per_item * remaining_items)
                if eta_seconds >= 60:
                    eta_text = pick(f"预计还需 {eta_seconds // 60} 分 {eta_seconds % 60} 秒", f"About {eta_seconds // 60}m {eta_seconds % 60}s remaining")
                else:
                    eta_text = pick(f"预计还需 {eta_seconds} 秒", f"About {eta_seconds}s remaining")
            else:
                eta_text = pick("预计时间计算中...", "Estimating time...")
            _render_progress(percent, eta_text)
            status_text.text(pick(f"正在分析第 {current} / {total} 条评论...", f"Analyzing review {current} / {total}..."))

        results = analyze_batch(
            comments=[{"content": c["content"], "rating": c.get("rating")} for c in unprocessed],
            category=category_name,
            api_key=get_api_key(user_id),
            progress_callback=progress_callback,
        )

        # 更新分析结果：有评分以评分为准覆写 sentiment
        positive_count = 0
        negative_count = 0
        unrecognizable_count = 0
        for comment, result in zip(unprocessed, results):
            rating = comment.get("rating")
            if rating is not None:
                try:
                    rating = int(float(rating))
                    result["sentiment"] = "negative" if rating <= 3 else "positive"
                except (ValueError, TypeError):
                    pass

            update_comment_analysis(user_id, comment["id"], result)

            sentiment = result.get("sentiment")
            if sentiment == "unrecognizable":
                unrecognizable_count += 1
            elif sentiment == "positive":
                positive_count += 1
            elif sentiment == "negative":
                negative_count += 1

        valid_count = len(unprocessed) - unrecognizable_count
        update_session_stats(user_id, session_id, len(unprocessed), positive_count, negative_count)

        # 自动推送（根据用户设置的规则判断）
        try:
            push_result = auto_notify_after_analysis(user_id, session_id)
            if push_result and push_result.get("ok"):
                st.toast(pick("📤 已自动推送分析摘要到飞书", "📤 Analysis summary sent to Feishu automatically"))
        except Exception:
            pass

        _render_progress(100, pick("分析完成！", "Analysis complete!"))
        status_text.text(pick("分析完成！正在跳转到结果页...", "Analysis complete. Opening the results page..."))
        st.session_state["view_session_id"] = session_id
        st.session_state["analysis_redirect_session_id"] = session_id
        st.session_state["current_page"] = "analysis"
        st.session_state["analysis_subpage"] = "results"
        st.session_state["upload_step"] = 1
        # 清理临时数据、分析锁和旧的时间筛选 state
        for key in ["upload_df", "upload_df_clean", "upload_info", "analyzing_session_id",
                    "upload_created_product_ref_id", "upload_existing_binding_signature",
                    "upload_manual_variant_id", "upload_variant_binding_mode",
                    "upload_existing_product_ref_id", "upload_file",
                    "time_filter_option", "time_filter_start", "time_filter_end"]:
            st.session_state.pop(key, None)
        st.rerun()
