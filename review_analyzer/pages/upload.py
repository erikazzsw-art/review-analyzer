"""上传用户评论页面 — 三步流程"""

import hashlib
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from review_analyzer.auth import get_current_user_id
from review_analyzer.config import CATEGORY_TAGS
from review_analyzer.database import (
    create_session,
    add_comments_batch,
    get_existing_hashes,
    get_unprocessed_comments,
    update_comment_analysis,
    update_session_stats,
)
from review_analyzer.parser import parse_file
from review_analyzer.analyzer import analyze_batch, get_api_key
from review_analyzer.notifier import auto_notify_after_analysis


def _render_step_indicator(current: int) -> None:
    """渲染步骤指示器"""
    steps = ["① 填写产品信息", "② 上传评论文件", "③ 分析中"]
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


def render_upload() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning("请先登录")
        return

    # 页头
    st.markdown("""
    <div style="margin-bottom:24px;">
        <div style="font-size:22px;font-weight:700;">上传用户评论</div>
        <div style="font-size:14px;color:#636E72;margin-top:2px;">填写产品信息 → 上传评论文件 → AI 自动分析</div>
    </div>
    """, unsafe_allow_html=True)

    if "upload_step" not in st.session_state:
        st.session_state["upload_step"] = 1

    current_step = st.session_state["upload_step"]
    _render_step_indicator(current_step)

    # ============================================================
    # Step 1: 填写产品信息
    # ============================================================
    if current_step == 1:
        col1, col2 = st.columns(2)
        with col1:
            product_id = st.text_input(
                "产品编号 *",
                placeholder="SKU 或任何可识别该产品的唯一编码",
                key="upload_product_id",
            )
        with col2:
            product_name = st.text_input(
                "产品中文名称",
                placeholder="选填，如：无线蓝牙耳机",
                key="upload_product_name",
            )

        col3, col4 = st.columns(2)
        with col3:
            platform = st.selectbox(
                "平台来源 *",
                ["请选择...", "Amazon", "Walmart", "Shopee", "Temu", "eBay",
                 "AliExpress", "Mercado Libre", "其他"],
                key="upload_platform",
            )
        with col4:
            categories = ["请选择..."] + list(CATEGORY_TAGS.keys())
            category = st.selectbox(
                "产品类目 *",
                categories,
                key="upload_category",
            )

        col5, col6 = st.columns(2)
        with col5:
            version = st.text_input(
                "版本号 *",
                placeholder="如：V1、V2",
                key="upload_version",
            )
        with col6:
            st.write("分析时间段（选填）")
            date_col1, date_col2 = st.columns(2)
            with date_col1:
                date_start = st.date_input("开始日期", value=None, key="upload_date_start",
                                           label_visibility="collapsed")
            with date_col2:
                date_end = st.date_input("结束日期", value=None, key="upload_date_end",
                                         label_visibility="collapsed")

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn = st.columns([3, 1])
        with col_btn[1]:
            if st.button("下一步：上传文件 →", type="primary", use_container_width=True):
                if not product_id:
                    st.error("请填写产品编号")
                elif platform == "请选择...":
                    st.error("请选择平台来源")
                elif category == "请选择...":
                    st.error("请选择产品类目")
                elif not version:
                    st.error("请填写版本号")
                else:
                    st.session_state["upload_info"] = {
                        "product_id": product_id,
                        "product_name": product_name,
                        "platform": platform,
                        "category": category,
                        "version": version,
                        "date_start": str(date_start) if date_start else None,
                        "date_end": str(date_end) if date_end else None,
                    }
                    st.session_state["upload_step"] = 2
                    st.rerun()

    # ============================================================
    # Step 2: 上传文件
    # ============================================================
    elif current_step == 2:
        st.markdown("""
        <div style="background:linear-gradient(90deg,#FFEAEA,#FFF3E0);border:1px solid #FDCB6E;
                    border-radius:12px;padding:16px 20px;margin-bottom:16px;
                    display:flex;align-items:center;gap:12px;font-size:14px;">
            <span style="font-size:24px;">⚠️</span>
            <span>上传的文件必须包含「评论内容」和「日期」字段，否则将无法上传成功。</span>
        </div>
        """, unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "拖拽文件到此处，或点击选择",
            type=["csv", "xlsx", "xls", "docx", "txt"],
            key="upload_file",
            help="支持 CSV / XLSX / DOCX / TXT 格式",
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

                st.success(f"文件解析成功，共 {len(df)} 条评论")
                st.markdown("**📄 文件预览（前 5 行）**")
                st.dataframe(df.head(5), use_container_width=True)

                # 重复检测
                info = st.session_state.get("upload_info", {})
                existing_hashes = get_existing_hashes(user_id, info.get("product_id", ""))
                if "content" in df.columns:
                    df["_hash"] = df["content"].apply(
                        lambda x: hashlib.md5(str(x).encode()).hexdigest() if pd.notna(x) else ""
                    )
                    duplicates = df[df["_hash"].isin(existing_hashes)]
                    new_records = df[~df["_hash"].isin(existing_hashes)]

                    if len(duplicates) > 0:
                        st.warning(f"检测到 {len(duplicates)} 条重复评论，将自动跳过")
                        st.session_state["upload_df_clean"] = new_records.drop(columns=["_hash"])
                    else:
                        st.session_state["upload_df_clean"] = df.drop(columns=["_hash"])
                else:
                    st.session_state["upload_df_clean"] = df

            except Exception as e:
                st.error(f"文件解析失败：{str(e)}")

        st.markdown("<br>", unsafe_allow_html=True)
        col_back, col_next = st.columns([1, 1])
        with col_back:
            if st.button("← 返回修改信息", use_container_width=True):
                st.session_state["upload_step"] = 1
                st.rerun()
        with col_next:
            if st.button("开始分析 →", type="primary", use_container_width=True):
                if "upload_df_clean" not in st.session_state:
                    st.error("请先上传文件")
                else:
                    st.session_state["upload_step"] = 3
                    st.rerun()

    # ============================================================
    # Step 3: 分析中
    # ============================================================
    elif current_step == 3:
        info = st.session_state.get("upload_info", {})
        df = st.session_state.get("upload_df_clean")

        if df is None or df.empty:
            st.error("没有可分析的数据")
            if st.button("返回"):
                st.session_state["upload_step"] = 1
                st.rerun()
            return

        st.markdown("""
        <div style="text-align:center;padding:40px 0;">
            <div style="font-size:48px;margin-bottom:16px;">🔄</div>
            <div style="font-size:18px;font-weight:600;margin-bottom:8px;">AI 正在分析评论...</div>
            <div style="font-size:14px;color:#636E72;margin-bottom:24px;">
                正在提取产品问题与亮点，请耐心等待
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 创建 session
        session_data = {
            "product_id": info.get("product_id"),
            "version": info.get("version", "V1"),
            "auto_title": f"{datetime.now().strftime('%Y-%m-%d')} | {info.get('product_id')} | {len(df)}条",
            "date_range_start": info.get("date_start"),
            "date_range_end": info.get("date_end"),
            "total_reviews": len(df),
            "positive_count": 0,
            "negative_count": 0,
            "category": info.get("category"),
        }
        session_id = create_session(user_id, session_data)

        # 准备评论数据
        comments_to_insert = []
        for _, row in df.iterrows():
            content = str(row.get("content", ""))
            comment = {
                "product_id": info.get("product_id"),
                "version": info.get("version", "V1"),
                "content": content,
                "rating": row.get("rating") if pd.notna(row.get("rating")) else None,
                "date": str(row.get("date", "")),
                "reviewer": str(row.get("reviewer", "")) if pd.notna(row.get("reviewer")) else None,
                "source": info.get("platform"),
                "content_hash": hashlib.md5(content.encode()).hexdigest(),
                "session_id": session_id,
            }
            comments_to_insert.append(comment)

        add_comments_batch(user_id, comments_to_insert)

        # AI 分析
        progress_bar = st.progress(0)
        status_text = st.empty()

        unprocessed = get_unprocessed_comments(user_id, session_id)
        category_name = info.get("category", "3C电子")

        def progress_callback(current: int, total: int) -> None:
            progress_bar.progress(current / total)
            status_text.text(f"正在分析第 {current} / {total} 条评论...")

        results = analyze_batch(
            comments=[c["content"] for c in unprocessed],
            category=category_name,
            api_key=get_api_key(user_id),
            progress_callback=progress_callback,
        )

        # 更新分析结果
        positive_count = 0
        negative_count = 0
        for comment, result in zip(unprocessed, results):
            update_comment_analysis(user_id, comment["id"], result)
            if result.get("sentiment") == "positive":
                positive_count += 1
            elif result.get("sentiment") == "negative":
                negative_count += 1

        update_session_stats(user_id, session_id, len(unprocessed), positive_count, negative_count)

        # 自动推送（根据用户设置的规则判断）
        try:
            push_result = auto_notify_after_analysis(user_id, session_id)
            if push_result and push_result.get("ok"):
                st.toast("📤 已自动推送分析摘要到飞书")
        except Exception:
            pass

        progress_bar.progress(1.0)
        status_text.text("分析完成！")

        st.success("分析完成！正在跳转到结果页...")
        st.session_state["view_session_id"] = session_id
        st.session_state["current_page"] = "results"
        st.session_state["upload_step"] = 1
        # 清理临时数据
        for key in ["upload_df", "upload_df_clean", "upload_info"]:
            st.session_state.pop(key, None)
        st.rerun()
