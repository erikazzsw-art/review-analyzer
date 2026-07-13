from __future__ import annotations

import io
from datetime import datetime
from typing import Any

import xlsxwriter


def export_result_module_to_xlsx(
    module_name: str,
    module_payload: dict[str, Any],
    context: dict[str, Any],
) -> tuple[bytes, str]:
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    sheet = workbook.add_worksheet(module_name[:31] or "Module")

    header_fmt = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#f36f8f",
            "font_color": "#ffffff",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        }
    )
    label_fmt = workbook.add_format({"bold": True, "border": 1, "bg_color": "#fff1f5"})
    cell_fmt = workbook.add_format({"border": 1, "text_wrap": True, "valign": "top"})
    title_fmt = workbook.add_format({"bold": True, "font_size": 14})

    sheet.set_column("A:A", 24)
    sheet.set_column("B:B", 64)
    sheet.set_column("C:C", 64)

    sheet.write(0, 0, module_name, title_fmt)
    metadata_rows = [
        ("产品编号", context.get("product_id", "--")),
        ("版本", context.get("version", "--")),
        ("时间范围", context.get("time_label", "--")),
        ("导出时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    ]
    for row_idx, (label, value) in enumerate(metadata_rows, 2):
        sheet.write(row_idx, 0, label, label_fmt)
        sheet.write(row_idx, 1, str(value), cell_fmt)

    content_start = 7
    rows = _flatten_module_payload(module_payload)
    sheet.write(content_start, 0, "字段", header_fmt)
    sheet.write(content_start, 1, "内容", header_fmt)
    sheet.write(content_start, 2, "补充", header_fmt)
    for offset, row in enumerate(rows, 1):
        sheet.write(content_start + offset, 0, row[0], cell_fmt)
        sheet.write(content_start + offset, 1, row[1], cell_fmt)
        sheet.write(content_start + offset, 2, row[2], cell_fmt)

    _add_ai_disclaimer_sheet(workbook)

    workbook.close()
    output.seek(0)
    filename = (
        f"{context.get('product_id', 'UNKNOWN')}-{context.get('version', 'V1')}-"
        f"{module_name}-{datetime.now().strftime('%Y%m%d')}.xlsx"
    )
    return output.getvalue(), filename


def _add_ai_disclaimer_sheet(workbook: xlsxwriter.Workbook) -> None:
    """Add AI transparency disclaimer sheet (California AI Transparency Act AB 2013)."""
    ws = workbook.add_worksheet("AI Notice / AI 标注")
    ws.set_column("A:A", 60)
    note_fmt = workbook.add_format({
        "font_size": 10,
        "italic": True,
        "font_color": "#888888",
        "valign": "vcenter",
    })
    ws.write(0, 0, "Analysis powered by AI (OpenAI GPT-4o-mini)", note_fmt)
    ws.write(1, 0, "AI 生成分析 · 基于 OpenAI GPT-4o-mini", note_fmt)


def export_compare_page_to_xlsx(dataset: dict[str, Any], context: dict[str, Any]) -> tuple[bytes, str]:
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    sheet = workbook.add_worksheet("对比分析")
    header_fmt = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#4fb99f",
            "font_color": "#ffffff",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        }
    )
    section_fmt = workbook.add_format({"bold": True, "border": 1, "bg_color": "#eef8f5"})
    cell_fmt = workbook.add_format({"border": 1, "text_wrap": True, "valign": "top"})
    title_fmt = workbook.add_format({"bold": True, "font_size": 14})

    columns = dataset.get("columns", [])
    objects = dataset.get("objects", [])
    sheet.write(0, 0, context.get("title", "对比分析"), title_fmt)
    for idx, label in enumerate(columns):
        sheet.set_column(idx, idx, 28 if idx == 0 else 36)
        sheet.write(2, idx, label, header_fmt)

    row_index = 3
    for section in objects:
        sheet.write(row_index, 0, section.get("section", ""), section_fmt)
        header_values = section.get("values") or columns[1:]
        for idx, value in enumerate(header_values, 1):
            sheet.write(row_index, idx, value, section_fmt)
        row_index += 1
        for child in section.get("children", []):
            if "label" in child and "values" in child:
                sheet.write(row_index, 0, child.get("label", ""), cell_fmt)
                for idx, value in enumerate(child.get("values", []), 1):
                    sheet.write(row_index, idx, value, cell_fmt)
            else:
                for idx, column in enumerate(columns):
                    sheet.write(row_index, idx, str(child.get(column, "")), cell_fmt)
            row_index += 1

    _add_ai_disclaimer_sheet(workbook)

    workbook.close()
    output.seek(0)
    filename = f"compare-{datetime.now().strftime('%Y%m%d')}.xlsx"
    return output.getvalue(), filename


def _flatten_module_payload(module_payload: dict[str, Any]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for key, value in module_payload.items():
        if isinstance(value, str):
            rows.append((key, value, ""))
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    label = str(item.get("label") or item.get("tag") or item.get("title") or key)
                    main = str(item.get("detail") or item.get("reason") or item.get("summary") or item)
                    extra = str(item.get("pct") or item.get("value") or item.get("quote") or "")
                    rows.append((label, main, extra))
                else:
                    rows.append((key, str(item), ""))
            continue
        if isinstance(value, dict):
            summary = str(value.get("summary") or "")
            if summary:
                rows.append((key, summary, ""))
            for sub_key, sub_value in value.items():
                if sub_key == "summary":
                    continue
                rows.append((f"{key}.{sub_key}", str(sub_value), ""))
            continue
        rows.append((key, str(value), ""))
    return rows or [("内容", "暂无内容", "")]
