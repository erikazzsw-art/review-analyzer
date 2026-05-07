"""导出 CSV / XLSX — 多 Sheet 结构化输出"""

import io
from collections import Counter
from datetime import datetime
from typing import Optional

import xlsxwriter

from .database import get_session_by_id, get_comments


def _build_filename(session: dict, ext: str) -> str:
    """按命名规范生成文件名：[产品标识]-[版本]-[时间范围]-分析结果-[导出日期].ext"""
    product_id = session.get("product_id", "UNKNOWN")
    version = session.get("version", "V1")

    start = session.get("date_range_start", "")
    end = session.get("date_range_end", "")
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
        ["分析时间段", f"{session.get('date_range_start', '')} ~ {session.get('date_range_end', '')}"],
        ["创建时间", session.get("created_at", "")],
        ["总评论数", str(total)],
        ["正面评论数", str(pos)],
        ["正面率", pos_rate],
        ["负面评论数", str(neg)],
        ["负面率", neg_rate],
        ["中性 / 其他", str(neutral)],
    ]
    return rows


def _build_comments_data(comments: list[dict]) -> tuple[list[str], list[list[str]]]:
    """构建评论明细数据"""
    headers = [
        "序号", "评论内容", "评分", "日期", "评论者", "来源",
        "情感", "分类", "优先级", "分析理由", "改进建议",
        "问题标签", "亮点标签",
    ]
    rows = []
    for i, c in enumerate(comments, 1):
        rows.append([
            str(i),
            c.get("content", ""),
            str(c.get("rating", "")) if c.get("rating") else "",
            c.get("date", ""),
            c.get("reviewer", "") or "",
            c.get("source", "") or "",
            c.get("sentiment", ""),
            c.get("category", ""),
            c.get("priority", ""),
            c.get("reason", ""),
            c.get("improvement", ""),
            c.get("issue_tag", ""),
            c.get("highlight_tag", ""),
        ])
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
        for tag in raw_tags.split(","):
            tag = tag.strip()
            if tag:
                tag_counter[tag] += 1
                if tag not in tag_sources:
                    tag_sources[tag] = []
                content = c.get("content", "")[:120]
                if len(tag_sources[tag]) < 20:
                    tag_sources[tag].append(content)

    pool_size = len(pool_comments) if pool_comments else 1
    headers = ["排名", "标签", "出现次数", "占比", "代表性评论（前20条摘要）"]
    rows = []
    for rank, (tag, count) in enumerate(tag_counter.most_common(10), 1):
        pct = f"{count / pool_size * 100:.1f}%"
        source_text = " | ".join(tag_sources.get(tag, []))
        rows.append([str(rank), tag, str(count), pct, source_text])

    return headers, rows


def export_to_xlsx(
    session_id: int,
    user_id: int,
    date_range: Optional[tuple[str, str]] = None,
) -> tuple[bytes, str]:
    """
    生成多 Sheet XLSX 文件。
    返回 (bytes, filename)。
    """
    session = get_session_by_id(user_id, session_id)
    if not session:
        raise ValueError("未找到该分析记录")

    comments = get_comments(user_id, session_id=session_id)
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
    headers, rows = _build_comments_data(comments)

    col_widths = [6, 50, 6, 12, 12, 10, 8, 10, 8, 30, 30, 15, 15]
    for i, w in enumerate(col_widths):
        ws2.set_column(i, i, w)

    for col_idx, h in enumerate(headers):
        ws2.write(0, col_idx, h, header_fmt)

    for row_idx, row_data in enumerate(rows, 1):
        for col_idx, val in enumerate(row_data):
            ws2.write(row_idx, col_idx, val, cell_fmt)

    # Sheet3: TOP10 核心问题点
    negative_comments = [c for c in comments if c.get("sentiment") == "negative"]
    ws3 = workbook.add_worksheet("TOP10 核心问题点")
    ws3.set_column("A:A", 6)
    ws3.set_column("B:B", 15)
    ws3.set_column("C:C", 10)
    ws3.set_column("D:D", 8)
    ws3.set_column("E:E", 80)

    t3_headers, t3_rows = _build_top10_data(comments, "issue_tag", negative_comments)
    for col_idx, h in enumerate(t3_headers):
        ws3.write(0, col_idx, h, header_fmt)
    for row_idx, row_data in enumerate(t3_rows, 1):
        for col_idx, val in enumerate(row_data):
            ws3.write(row_idx, col_idx, val, cell_fmt)

    # Sheet4: TOP10 产品亮点
    positive_comments = [c for c in comments if c.get("sentiment") == "positive"]
    ws4 = workbook.add_worksheet("TOP10 产品亮点")
    ws4.set_column("A:A", 6)
    ws4.set_column("B:B", 15)
    ws4.set_column("C:C", 10)
    ws4.set_column("D:D", 8)
    ws4.set_column("E:E", 80)

    t4_headers, t4_rows = _build_top10_data(comments, "highlight_tag", positive_comments)
    for col_idx, h in enumerate(t4_headers):
        ws4.write(0, col_idx, h, header_fmt)
    for row_idx, row_data in enumerate(t4_rows, 1):
        for col_idx, val in enumerate(row_data):
            ws4.write(row_idx, col_idx, val, cell_fmt)

    workbook.close()
    output.seek(0)
    return output.getvalue(), filename


def export_to_csv(
    session_id: int,
    user_id: int,
    date_range: Optional[tuple[str, str]] = None,
) -> tuple[bytes, str]:
    """
    生成 CSV 文件（评论明细）。
    返回 (bytes, filename)。
    """
    import csv

    session = get_session_by_id(user_id, session_id)
    if not session:
        raise ValueError("未找到该分析记录")

    comments = get_comments(user_id, session_id=session_id)
    filename = _build_filename(session, "csv")

    headers, rows = _build_comments_data(comments)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)

    csv_bytes = output.getvalue().encode("utf-8-sig")
    return csv_bytes, filename
