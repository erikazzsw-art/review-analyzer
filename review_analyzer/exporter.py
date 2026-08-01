"""导出 CSV / XLSX — 多 Sheet 结构化输出"""

from __future__ import annotations

import io
from collections import Counter
from datetime import datetime

import xlsxwriter

from backend_api.app.services.category_grouper import CATEGORY_ZH_LABELS
from backend_api.app.services.customer_label_v2_frontstage import customer_label_v2_frontstage_flag_from_env
from backend_api.app.services.review_signal_frontstage import review_signal_frontstage_flag_from_env
from backend_api.app.services.specific_issue import (
    build_customer_highlight_rows,
    build_specific_issue_rows,
    customer_highlight_tags_for_comment,
    customer_issue_tags_for_comment,
    decorate_comment_customer_labels,
    iter_customer_highlight_occurrences,
    iter_specific_issue_occurrences,
)

from .database import get_comments, get_session_by_id


def _category_zh(slug: str | None) -> str:
    """slug → 中文人类可读标签；未知 slug 原样返回，空值返回空串."""
    if not slug:
        return ""
    return CATEGORY_ZH_LABELS.get(slug, slug)


def _build_filename(session: dict, ext: str) -> str:
    """按命名规范生成文件名：[产品标识]-[版本]-[时间范围]-分析结果-[导出日期].ext"""
    product_id = session.get("product_id", "UNKNOWN")
    version = session.get("version", "V1")

    start = str(session.get("date_range_start", "") or "")
    end = str(session.get("date_range_end", "") or "")
    if start and end:
        date_range = f"{start.replace('-', '')}~{end.replace('-', '')}"
    else:
        date_range = "全部"

    export_date = datetime.now().strftime("%Y%m%d")
    return f"{product_id}-{version}-{date_range}-分析结果-{export_date}.{ext}"


def _build_summary_data(session: dict) -> list[list[str]]:
    """构建总览摘要数据行"""
    total = session.get("total_reviews", 0)
    pos = session.get("positive_count", 0)
    neg = session.get("negative_count", 0)
    neutral = total - pos - neg

    pos_rate = f"{pos / total * 100:.1f}%" if total > 0 else "0%"
    neg_rate = f"{neg / total * 100:.1f}%" if total > 0 else "0%"

    rows = [
        ["指标", "数值"],
        ["产品编号", session.get("product_id", "")],
        ["版本", session.get("version", "")],
        ["产品类目", session.get("category", "")],
        ["分析时间段", f"{str(session.get('date_range_start', '') or '')} ~ {str(session.get('date_range_end', '') or '')}"],
        ["创建时间", str(session.get("created_at", ""))[:19]],
        ["总评论数", str(total)],
        ["正面评论数", str(pos)],
        ["正面率", pos_rate],
        ["负面评论数", str(neg)],
        ["负面率", neg_rate],
        ["中性 / 其他", str(neutral)],
    ]
    return rows


CUSTOMER_LABEL_RAW_EXPORT_HEADERS = [
    "客户痛点",
    "痛点证据",
    "客户亮点",
    "亮点证据",
]

SPECIFIC_ISSUE_AUDIT_EXPORT_HEADERS = [
    "Audit Customer Issue",
    "Audit Canonical Issue Key",
    "Audit Internal Aspect",
    "Audit Aspect Key",
    "Audit Evidence Span",
    "Audit Issue Confidence",
    "Audit Evidence Verified",
    "Audit Cluster Propagated",
    "Audit Legacy Fallback",
    "Audit Source Review Allowed",
    "Audit Aspect Allowed",
    "Audit Context Allowed",
]

CUSTOMER_HIGHLIGHT_AUDIT_EXPORT_HEADERS = [
    "Audit Customer Label",
    "Audit Canonical Highlight Key",
    "Audit Highlight Internal Aspect",
    "Audit Highlight Aspect Key",
    "Audit Highlight Evidence Span",
    "Audit Highlight Confidence",
    "Audit Highlight Evidence Verified",
    "Audit Highlight Cluster Propagated",
    "Audit Highlight Legacy Fallback",
    "Audit Highlight Source Review Allowed",
    "Audit Highlight Aspect Allowed",
    "Audit Highlight Context Allowed",
]


def _is_export_frontstage_occurrence(occurrence: dict) -> bool:
    return bool(
        occurrence.get("display_allowed") is not False
        and occurrence.get("source_review_allowed")
        and occurrence.get("verified_evidence")
        and occurrence.get("evidence_span")
        and not occurrence.get("cluster_propagated")
        and not occurrence.get("legacy_fallback")
        and occurrence.get("aspect_allowed") is not False
        and occurrence.get("context_allowed") is not False
    )


def _join_customer_label_field(
    comment: dict,
    field: str,
    *,
    label_type: str,
    display_only: bool = True,
) -> str:
    iterator = iter_specific_issue_occurrences if label_type == "issue" else iter_customer_highlight_occurrences
    canonical_field = "canonical_issue_key" if label_type == "issue" else "canonical_highlight_key"
    values = []
    seen_occurrences: set[str] = set()
    for occurrence in iterator(comment, locale="zh"):
        if display_only and not _is_export_frontstage_occurrence(occurrence):
            continue
        if display_only:
            dedupe_key = str(
                occurrence.get(canonical_field) or occurrence.get("canonical_label_key") or ""
            ).strip()
            if not dedupe_key:
                dedupe_key = str(occurrence.get("evidence_span") or occurrence.get(field) or "").strip()
            if dedupe_key in seen_occurrences:
                continue
            seen_occurrences.add(dedupe_key)
        if field in {
            "verified_evidence",
            "cluster_propagated",
            "legacy_fallback",
            "source_review_allowed",
            "aspect_allowed",
            "context_allowed",
            "display_allowed",
        }:
            values.append("true" if occurrence.get(field) else "false")
            continue
        values.append(str(occurrence.get(field) or "").strip())
    return ", ".join(value for value in values if value)


def _join_specific_issue_field(comment: dict, field: str, *, display_only: bool = True) -> str:
    return _join_customer_label_field(comment, field, label_type="issue", display_only=display_only)


def _join_customer_highlight_field(comment: dict, field: str, *, display_only: bool = True) -> str:
    return _join_customer_label_field(comment, field, label_type="highlight", display_only=display_only)


def _customer_issue_tag_text(comment: dict) -> str:
    return ", ".join(customer_issue_tags_for_comment(comment, locale="zh"))


def _customer_highlight_tag_text(comment: dict) -> str:
    return ", ".join(customer_highlight_tags_for_comment(comment, locale="zh"))


def _num(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _int_num(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _mention_count(row: dict) -> int:
    return _int_num(row.get("mention_count") if row.get("mention_count") is not None else row.get("count"))


def _review_count(row: dict) -> int:
    return _int_num(row.get("review_count") if row.get("review_count") is not None else row.get("count"))


def _mention_share(row: dict) -> float:
    return _num(row.get("mention_share") if row.get("mention_share") is not None else row.get("pct"))


def _impact_review_share(row: dict) -> float:
    return _num(row.get("impact_review_share") if row.get("impact_review_share") is not None else row.get("pct"))


def _pct_text(value: float) -> str:
    return f"{value:.1f}%"


def _representative_evidence(row: dict) -> str:
    if row.get("cluster_propagated") or not row.get("evidence_verified"):
        return ""
    return " | ".join(str(item) for item in (row.get("evidence_spans") or []) if item)


def _build_comments_data(
    comments: list[dict],
    *,
    include_specific_issue: bool = False,
) -> tuple[list[str], list[list[str]]]:
    """构建评论明细数据"""
    headers = [
        "序号", "评论内容", "评分", "日期", "评论者", "来源",
        "情感", "分类", "优先级", "分析理由", "改进建议",
    ]
    if include_specific_issue:
        headers.extend(CUSTOMER_LABEL_RAW_EXPORT_HEADERS)
    else:
        headers.extend(["问题标签", "亮点标签"])
    rows = []
    for i, c in enumerate(comments, 1):
        row = [
            str(i),
            c.get("content", ""),
            str(c.get("rating", "")) if c.get("rating") else "",
            c.get("date", ""),
            c.get("reviewer", "") or "",
            c.get("source", "") or "",
            c.get("sentiment", ""),
            _category_zh(c.get("category")),
            c.get("priority", ""),
            c.get("reason", ""),
            c.get("improvement", ""),
        ]
        if include_specific_issue:
            row.extend(
                [
                    _join_specific_issue_field(c, "specific_issue"),
                    _join_specific_issue_field(c, "evidence_span"),
                    _join_customer_highlight_field(c, "customer_highlight"),
                    _join_customer_highlight_field(c, "evidence_span"),
                ]
            )
        else:
            row.extend([_customer_issue_tag_text(c), _customer_highlight_tag_text(c)])
        rows.append(row)
    return headers, rows


def _decorate_comments_for_export(comments: list[dict]) -> list[dict]:
    flag = customer_label_v2_frontstage_flag_from_env()
    review_signal_flag = review_signal_frontstage_flag_from_env()
    return [
        decorate_comment_customer_labels(
            comment,
            locale="zh",
            v2_frontstage_flag=flag,
            review_signal_frontstage_flag=review_signal_flag,
        )
        for comment in comments
    ]


def _build_label_audit_data(comments: list[dict]) -> tuple[list[str], list[list[str]]]:
    """构建独立审计 Sheet，避免内部字段混入用户默认 Raw Reviews."""
    headers = [
        "序号",
        "评论内容",
        "Frontstage Customer Issue",
        "Frontstage Canonical Issue Key",
        "Frontstage Customer Label",
        "Frontstage Canonical Highlight Key",
    ]
    headers.extend(SPECIFIC_ISSUE_AUDIT_EXPORT_HEADERS)
    headers.extend(CUSTOMER_HIGHLIGHT_AUDIT_EXPORT_HEADERS)

    rows = []
    for i, c in enumerate(comments, 1):
        row = [
            str(i),
            c.get("content", ""),
            _join_specific_issue_field(c, "specific_issue"),
            _join_specific_issue_field(c, "canonical_issue_key"),
            _join_customer_highlight_field(c, "customer_highlight"),
            _join_customer_highlight_field(c, "canonical_highlight_key"),
            _join_specific_issue_field(c, "specific_issue", display_only=False),
            _join_specific_issue_field(c, "canonical_issue_key", display_only=False),
            _join_specific_issue_field(c, "dimension", display_only=False),
            _join_specific_issue_field(c, "aspect_key", display_only=False),
            _join_specific_issue_field(c, "evidence_span", display_only=False),
            _join_specific_issue_field(c, "issue_confidence", display_only=False),
            _join_specific_issue_field(c, "verified_evidence", display_only=False),
            _join_specific_issue_field(c, "cluster_propagated", display_only=False),
            _join_specific_issue_field(c, "legacy_fallback", display_only=False),
            _join_specific_issue_field(c, "source_review_allowed", display_only=False),
            _join_specific_issue_field(c, "aspect_allowed", display_only=False),
            _join_specific_issue_field(c, "context_allowed", display_only=False),
            _join_customer_highlight_field(c, "customer_highlight", display_only=False),
            _join_customer_highlight_field(c, "canonical_highlight_key", display_only=False),
            _join_customer_highlight_field(c, "dimension", display_only=False),
            _join_customer_highlight_field(c, "aspect_key", display_only=False),
            _join_customer_highlight_field(c, "evidence_span", display_only=False),
            _join_customer_highlight_field(c, "highlight_confidence", display_only=False),
            _join_customer_highlight_field(c, "verified_evidence", display_only=False),
            _join_customer_highlight_field(c, "cluster_propagated", display_only=False),
            _join_customer_highlight_field(c, "legacy_fallback", display_only=False),
            _join_customer_highlight_field(c, "source_review_allowed", display_only=False),
            _join_customer_highlight_field(c, "aspect_allowed", display_only=False),
            _join_customer_highlight_field(c, "context_allowed", display_only=False),
        ]
        rows.append(row)
    return headers, rows


def _build_customer_highlight_top10_data(pool_comments: list[dict]) -> tuple[list[str], list[list[str]]]:
    """构建 TOP10 客户亮点数据."""
    headers = [
        "排名",
        "客户亮点",
        "Mention Count",
        "Mention Share",
        "Review Count",
        "Impact Review Share",
        "Representative Evidence",
        "内部维度",
        "Canonical Highlight Key",
        "Aspect Key",
        "Highlight Confidence",
        "Evidence Verified",
        "Cluster Propagated",
        "Legacy Fallback",
    ]
    rows: list[list[str]] = []
    for rank, row in enumerate(build_customer_highlight_rows(pool_comments, locale="zh"), 1):
        aspect_keys = row.get("aspect_keys")
        aspect_key_text = (
            ", ".join(str(item) for item in aspect_keys if item)
            if isinstance(aspect_keys, list)
            else str(row.get("aspect_key") or "")
        )
        rows.append(
            [
                str(rank),
                str(row.get("customer_highlight") or row.get("tag") or ""),
                str(_mention_count(row)),
                _pct_text(_mention_share(row)),
                str(_review_count(row)),
                _pct_text(_impact_review_share(row)),
                _representative_evidence(row),
                str(row.get("dimension") or ""),
                str(row.get("canonical_highlight_key") or ""),
                aspect_key_text,
                str(row.get("highlight_confidence") or ""),
                "true" if row.get("evidence_verified") else "false",
                "true" if row.get("cluster_propagated") else "false",
                "true" if row.get("legacy_fallback") else "false",
            ]
        )
    return headers, rows


def _build_top10_data(
    comments: list[dict],
    tag_field: str,
    pool_comments: list[dict],
) -> tuple[list[str], list[list[str]]]:
    """构建 TOP10 标签数据（问题或亮点）"""
    tag_counter: Counter = Counter()
    tag_sources: dict[str, list[str]] = {}

    for c in pool_comments:
        raw_tags = c.get(tag_field, "")
        if not raw_tags:
            continue
        seen_in_comment: set[str] = set()
        for tag in raw_tags.split(","):
            tag = tag.strip()
            if tag and tag not in seen_in_comment:
                seen_in_comment.add(tag)
                tag_counter[tag] += 1
                if tag not in tag_sources:
                    tag_sources[tag] = []
                content = c.get("content", "")[:120]
                if len(tag_sources[tag]) < 20:
                    tag_sources[tag].append(content)

    pool_size = len(pool_comments) if pool_comments else 1
    headers = ["排名", "标签", "Mention Count", "Mention Share", "Representative Evidence"]
    rows = []
    for rank, (tag, count) in enumerate(tag_counter.most_common(10), 1):
        pct = f"{count / pool_size * 100:.1f}%"
        source_text = " | ".join(tag_sources.get(tag, []))
        rows.append([str(rank), tag, str(count), pct, source_text])

    return headers, rows


def _build_specific_issue_top10_data(pool_comments: list[dict]) -> tuple[list[str], list[list[str]]]:
    """构建 TOP10 Specific Issue 数据."""
    headers = [
        "排名",
        "客户痛点",
        "Mention Count",
        "Mention Share",
        "Review Count",
        "Impact Review Share",
        "Representative Evidence",
        "内部维度",
        "Canonical Issue Key",
        "Aspect Key",
        "Issue Confidence",
        "Evidence Verified",
        "Cluster Propagated",
        "Legacy Fallback",
    ]
    rows: list[list[str]] = []
    for rank, row in enumerate(build_specific_issue_rows(pool_comments, locale="zh"), 1):
        aspect_keys = row.get("aspect_keys")
        aspect_key_text = (
            ", ".join(str(item) for item in aspect_keys if item)
            if isinstance(aspect_keys, list)
            else str(row.get("aspect_key") or "")
        )
        rows.append(
            [
                str(rank),
                str(row.get("specific_issue") or row.get("tag") or ""),
                str(_mention_count(row)),
                _pct_text(_mention_share(row)),
                str(_review_count(row)),
                _pct_text(_impact_review_share(row)),
                _representative_evidence(row),
                str(row.get("dimension") or ""),
                str(row.get("canonical_issue_key") or ""),
                aspect_key_text,
                str(row.get("issue_confidence") or ""),
                "true" if row.get("evidence_verified") else "false",
                "true" if row.get("cluster_propagated") else "false",
                "true" if row.get("legacy_fallback") else "false",
            ]
        )
    return headers, rows


def export_to_xlsx(
    session_id: int,
    user_id: int,
    date_range: tuple[str, str] | None = None,
) -> tuple[bytes, str]:
    """
    生成多 Sheet XLSX 文件。
    返回 (bytes, filename)。
    """
    session = get_session_by_id(user_id, session_id)
    if not session:
        raise ValueError("未找到该分析记录")

    comments = _decorate_comments_for_export(get_comments(user_id, session_id=session_id))
    filename = _build_filename(session, "xlsx")

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})

    # 公共样式
    header_fmt = workbook.add_format({
        "bold": True,
        "bg_color": "#6C5CE7",
        "font_color": "#FFFFFF",
        "border": 1,
        "text_wrap": True,
        "valign": "vcenter",
        "align": "center",
        "font_size": 11,
    })
    cell_fmt = workbook.add_format({
        "border": 1,
        "text_wrap": True,
        "valign": "vcenter",
        "font_size": 10,
    })
    title_fmt = workbook.add_format({
        "bold": True,
        "font_size": 14,
        "font_color": "#6C5CE7",
    })

    # Sheet1: 总览摘要
    ws1 = workbook.add_worksheet("总览摘要")
    ws1.set_column("A:A", 18)
    ws1.set_column("B:B", 40)
    ws1.write(0, 0, "📊 分析结果总览", title_fmt)

    summary_rows = _build_summary_data(session)
    for row_idx, row_data in enumerate(summary_rows, 2):
        for col_idx, val in enumerate(row_data):
            fmt = header_fmt if row_idx == 2 else cell_fmt
            ws1.write(row_idx, col_idx, val, fmt)

    # Sheet2: 源评论分析明细
    ws2 = workbook.add_worksheet("源评论分析明细")
    headers, rows = _build_comments_data(comments, include_specific_issue=True)

    col_widths = [6, 50, 6, 12, 12, 10, 8, 10, 8, 30, 30, 24, 34, 24, 34]
    for i, w in enumerate(col_widths):
        ws2.set_column(i, i, w)

    for col_idx, h in enumerate(headers):
        ws2.write(0, col_idx, h, header_fmt)

    for row_idx, row_data in enumerate(rows, 1):
        for col_idx, val in enumerate(row_data):
            ws2.write(row_idx, col_idx, val, cell_fmt)

    ws_audit = workbook.add_worksheet("Label Audit")
    audit_headers, audit_rows = _build_label_audit_data(comments)
    audit_widths = [6, 50, 26, 30, 26, 32] + [26, 30, 24, 22, 34, 18, 18, 18, 18, 22, 18, 18] * 2
    for i, w in enumerate(audit_widths[: len(audit_headers)]):
        ws_audit.set_column(i, i, w)
    for col_idx, h in enumerate(audit_headers):
        ws_audit.write(0, col_idx, h, header_fmt)
    for row_idx, row_data in enumerate(audit_rows, 1):
        for col_idx, val in enumerate(row_data):
            ws_audit.write(row_idx, col_idx, val, cell_fmt)

    # Sheet3: TOP10 核心问题点
    ws3 = workbook.add_worksheet("TOP10 核心问题点")
    ws3.set_column("A:A", 6)
    ws3.set_column("B:B", 15)
    ws3.set_column("C:C", 10)
    ws3.set_column("D:D", 8)
    ws3.set_column("E:E", 22)
    ws3.set_column("F:F", 26)
    ws3.set_column("G:G", 18)
    ws3.set_column("H:H", 34)
    ws3.set_column("I:I", 16)
    ws3.set_column("J:J", 18)
    ws3.set_column("K:K", 16)
    ws3.set_column("L:L", 18)
    ws3.set_column("M:M", 18)

    t3_headers, t3_rows = _build_specific_issue_top10_data(comments)
    for col_idx, h in enumerate(t3_headers):
        ws3.write(0, col_idx, h, header_fmt)
    for row_idx, row_data in enumerate(t3_rows, 1):
        for col_idx, val in enumerate(row_data):
            ws3.write(row_idx, col_idx, val, cell_fmt)

    # Sheet4: TOP10 产品亮点
    ws4 = workbook.add_worksheet("TOP10 产品亮点")
    ws4.set_column("A:A", 6)
    ws4.set_column("B:B", 15)
    ws4.set_column("C:C", 10)
    ws4.set_column("D:D", 8)
    ws4.set_column("E:E", 22)
    ws4.set_column("F:F", 26)
    ws4.set_column("G:G", 18)
    ws4.set_column("H:H", 34)
    ws4.set_column("I:I", 16)
    ws4.set_column("J:J", 18)
    ws4.set_column("K:K", 16)
    ws4.set_column("L:L", 18)
    ws4.set_column("M:M", 18)

    t4_headers, t4_rows = _build_customer_highlight_top10_data(comments)
    for col_idx, h in enumerate(t4_headers):
        ws4.write(0, col_idx, h, header_fmt)
    for row_idx, row_data in enumerate(t4_rows, 1):
        for col_idx, val in enumerate(row_data):
            ws4.write(row_idx, col_idx, val, cell_fmt)

    # AI Transparency disclaimer (California AI Transparency Act AB 2013)
    ws_ai = workbook.add_worksheet("AI Notice")
    ws_ai.set_column("A:A", 60)
    ai_note_fmt = workbook.add_format({
        "font_size": 10,
        "italic": True,
        "font_color": "#888888",
        "valign": "vcenter",
    })
    ws_ai.write(0, 0, "Analysis powered by AI (OpenAI GPT-4o-mini)", ai_note_fmt)
    ws_ai.write(1, 0, "AI 生成分析 · 基于 OpenAI GPT-4o-mini", ai_note_fmt)

    workbook.close()
    output.seek(0)
    return output.getvalue(), filename


def export_to_csv(
    session_id: int,
    user_id: int,
    date_range: tuple[str, str] | None = None,
) -> tuple[bytes, str]:
    """
    生成 CSV 文件（评论明细）。
    返回 (bytes, filename)。
    """
    import csv

    session = get_session_by_id(user_id, session_id)
    if not session:
        raise ValueError("未找到该分析记录")

    comments = _decorate_comments_for_export(get_comments(user_id, session_id=session_id))
    filename = _build_filename(session, "csv")

    headers, rows = _build_comments_data(comments, include_specific_issue=True)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)

    csv_bytes = output.getvalue().encode("utf-8-sig")
    return csv_bytes, filename
