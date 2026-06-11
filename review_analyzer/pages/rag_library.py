from __future__ import annotations

import streamlit as st

from review_analyzer.auth import get_current_user_id
from review_analyzer.database import get_comments
from review_analyzer.i18n import pick, t
from review_analyzer.paddle_billing import is_pro_user
from review_analyzer.page_shell import render_page_header
from review_analyzer.product_store import get_product_overview_rows
from review_analyzer.rag import answer_question

MAX_RAG_PRODUCTS = 5


def render_rag_library() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning(t("login_required"))
        return

    render_page_header(
        pick("评论问答知识库", "Review Q&A Library"),
        pick("先选产品范围，再基于已有评论内容提问。", "Select a product scope first, then ask questions based on existing review content."),
        path=pick("知识检索 / 问评论", "Knowledge Retrieval / Review Q&A"),
    )

    if not is_pro_user(user_id):
        st.warning(pick("问评论是 Pro 功能。升级后可按一个或多个产品做评论问答。", "Review Q&A is a Pro feature. Upgrade to ask questions across one or more products."))
        return

    product_rows = get_product_overview_rows(user_id)
    product_map = {str(row["parent_product_id"]): row for row in product_rows if row.get("parent_product_id")}
    product_ids = list(product_map.keys())
    if not product_ids:
        st.info(pick("还没有可提问的产品评论。先去上传一批评论。", "There are no review assets available for Q&A yet. Upload a batch of reviews first."))
        return

    selected_product_ids = st.multiselect(
        pick("选择问答产品范围（最多 5 个）", "Select products for Q&A (up to 5)"),
        product_ids,
        default=product_ids[:1],
        format_func=lambda value: _format_product_label(product_map[value]),
        key="rag_library_products",
        max_selections=MAX_RAG_PRODUCTS,
    )
    if not selected_product_ids:
        st.info(pick("请先选择至少 1 个产品后再提问。", "Select at least one product before asking a question."))
        return

    selected_labels = [_format_product_label(product_map[product_id]) for product_id in selected_product_ids]
    st.markdown(f"### {pick('已选产品范围', 'Selected Product Scope')}")
    for label in selected_labels:
        st.write(f"- {label}")

    selected_comments = []
    for product_id in selected_product_ids:
        selected_comments.extend(get_comments(user_id, product_id=product_id))

    selected_comments = _dedupe_comments(selected_comments)
    st.caption(
        pick(
            f"当前范围：{len(selected_product_ids)} 个产品 · {len(selected_comments)} 条评论",
            f"Current scope: {len(selected_product_ids)} products · {len(selected_comments)} reviews",
        )
    )
    if not selected_comments:
        st.info(pick("所选产品还没有可用于问答的评论。", "The selected products do not have usable reviews for Q&A yet."))
        return

    question = st.text_area(
        pick("请输入你想问评论的问题", "Ask a question about the reviews"),
        placeholder=pick("例如：哪几个产品最常被吐槽安装困难？", "For example: Which products get the most complaints about assembly difficulty?"),
        key="rag_library_question",
        height=110,
    )
    if st.button(pick("开始提问", "Ask"), key="rag_library_submit", type="primary", use_container_width=True):
        if not question.strip():
            st.warning(pick("请先输入问题。", "Please enter a question first."))
            return
        with st.spinner(pick("正在检索评论并生成回答...", "Retrieving reviews and generating an answer...")):
            result = answer_question(user_id, question.strip(), selected_comments)
        st.markdown(f"### {pick('回答', 'Answer')}")
        st.write(result.get("answer") or pick("暂无回答。", "No answer yet."))
        retrieval_method = str(result.get("retrieval_method") or "text")
        st.caption(
            pick(
                f"检索方式：{'向量检索' if retrieval_method == 'vector' else '文本检索'}",
                f"Retrieval method: {'Vector Search' if retrieval_method == 'vector' else 'Text Search'}",
            )
        )
        citations = result.get("citations", [])
        if citations:
            st.markdown(f"### {pick('引用评论', 'Cited Reviews')}")
            for index, comment in enumerate(citations, 1):
                source_product = str(comment.get("product_id") or "--")
                source_version = str(comment.get("version") or "--")
                source_session = str(comment.get("session_id") or "--")
                date_text = str(comment.get("date") or pick("无日期", "No date"))
                rating = comment.get("rating") or pick("无评分", "No rating")
                st.markdown(
                    pick(
                        f"**[{index}] {source_product} · {source_version} · 批次 {source_session} · {rating} 星 · {date_text}**",
                        f"**[{index}] {source_product} · {source_version} · Batch {source_session} · {rating} stars · {date_text}**",
                    )
                )
                st.write(str(comment.get("content") or ""))
        else:
            st.info(pick("当前问题没有命中可引用的评论，建议把问题问得更具体一些，例如包装、安装、质量或某个功能点。", "No citable reviews matched this question. Try making the question more specific, such as packaging, assembly, quality, or a particular feature."))


def _format_product_label(row: dict) -> str:
    name = row.get("name") or row.get("parent_product_id")
    return pick(
        f"{name} · {row.get('parent_product_id')} · {row.get('review_count', 0)} 条评论",
        f"{name} · {row.get('parent_product_id')} · {row.get('review_count', 0)} reviews",
    )


def _dedupe_comments(comments: list[dict]) -> list[dict]:
    seen_hashes: set[str] = set()
    deduped: list[dict] = []
    for comment in comments:
        key = str(comment.get("content_hash") or comment.get("id") or "")
        if key and key in seen_hashes:
            continue
        if key:
            seen_hashes.add(key)
        deduped.append(comment)
    return deduped
