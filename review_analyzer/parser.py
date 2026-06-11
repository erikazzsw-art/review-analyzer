"""文件解析（含非结构化文档）"""

from __future__ import annotations

import hashlib
import json
import os
import re

import pandas as pd
from dateutil import parser as dateutil_parser

from review_analyzer.config import (
    CONTENT_COLUMN_ALIASES,
    DATE_COLUMN_ALIASES,
    RATING_COLUMN_ALIASES,
    SOURCE_COLUMN_ALIASES,
    USER_COLUMN_ALIASES,
)
from review_analyzer.database import get_connection

# ============================================================
# Column detection
# ============================================================

def detect_columns(df: pd.DataFrame) -> dict[str, str | None]:
    """自动识别 DataFrame 列名到标准字段的映射（模糊匹配）。"""
    cols_lower = {c.strip().lower(): c for c in df.columns}

    def _is_id_column(col_lower: str) -> bool:
        return col_lower.endswith("_id") or col_lower == "id"

    def _find(aliases: list[str]) -> str | None:
        # 第一轮：精确匹配
        for alias in aliases:
            for col_lower, col_orig in cols_lower.items():
                if col_lower == alias.lower():
                    return col_orig
        # 第二轮：子串匹配（排除 ID 列）
        for alias in aliases:
            for col_lower, col_orig in cols_lower.items():
                if _is_id_column(col_lower):
                    continue
                if alias.lower() in col_lower:
                    return col_orig
        return None

    return {
        "content": _find(CONTENT_COLUMN_ALIASES),
        "date": _find(DATE_COLUMN_ALIASES),
        "rating": _find(RATING_COLUMN_ALIASES),
        "reviewer": _find(USER_COLUMN_ALIASES),
        "source": _find(SOURCE_COLUMN_ALIASES),
    }


# ============================================================
# Date normalization
# ============================================================

def _normalize_date(value: object) -> str | None:
    """将任意日期格式解析为 YYYY-MM-DD 字符串。"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return dateutil_parser.parse(text).strftime("%Y-%m-%d")
    except (ValueError, OverflowError):
        return text


# ============================================================
# CSV / Excel parsing
# ============================================================

def _parse_csv_excel(file_path: str, file_type: str) -> pd.DataFrame:
    """解析 CSV / Excel 文件为标准化 DataFrame。"""
    if file_type == "csv":
        df = pd.read_csv(file_path, encoding="utf-8-sig")
    else:
        df = pd.read_excel(file_path)

    mapping = detect_columns(df)
    if not mapping["content"]:
        raise ValueError("上传失败：未找到评论内容字段，请确认文件包含评论文字")
    if not mapping["date"]:
        raise ValueError("上传失败：未找到日期字段，评论日期为必填项，用于时间维度分析和环比对比")

    standard_cols = {v for v in mapping.values() if v}
    rows: list[dict] = []

    for _, row in df.iterrows():
        raw_extra = {
            c: row[c] for c in df.columns
            if c not in standard_cols and pd.notna(row[c])
        }

        rating_raw = row.get(mapping["rating"]) if mapping["rating"] else None
        try:
            rating = int(float(rating_raw)) if rating_raw is not None and pd.notna(rating_raw) else None
        except (ValueError, TypeError):
            rating = None

        reviewer_col = mapping["reviewer"]
        source_col = mapping["source"]

        rows.append({
            "content": str(row[mapping["content"]]).strip(),
            "date": _normalize_date(row[mapping["date"]]),
            "rating": rating,
            "reviewer": str(row[reviewer_col]).strip() if reviewer_col and pd.notna(row.get(reviewer_col)) else None,
            "source": str(row[source_col]).strip() if source_col and pd.notna(row.get(source_col)) else None,
            "raw_data": json.dumps(raw_extra, ensure_ascii=False, default=str) if raw_extra else None,
        })

    return pd.DataFrame(rows)


# ============================================================
# Walmart format parser
# ============================================================

_WALMART_DATE_RE = re.compile(
    r"^((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4})",
    re.IGNORECASE,
)
_WALMART_RATING_RE = re.compile(r"(\d)\s+out\s+of\s+5\s+stars", re.IGNORECASE)
_WALMART_HELPFUL_RE = re.compile(r"Helpful\?\(\d+\)\(\d+\)Report", re.IGNORECASE)


def parse_walmart_format(text: str) -> list[dict]:
    """解析 Walmart 复制粘贴格式的评论文本。"""
    reviews: list[dict] = []
    blocks = re.split(
        r"(?=(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4})",
        text,
        flags=re.IGNORECASE,
    )

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue

        date_match = _WALMART_DATE_RE.match(lines[0])
        if not date_match:
            continue

        date_str = date_match.group(1)
        remainder = lines[0][len(date_str):].strip()
        # Reviewer is the first token after the date (separated by 2+ spaces)
        reviewer = re.split(r"\s{2,}", remainder)[0].strip() or None

        rating: int | None = None
        content_start = 1
        if len(lines) > 1:
            rm = _WALMART_RATING_RE.search(lines[1])
            if rm:
                rating = int(rm.group(1))
                content_start = 2

        content_lines: list[str] = []
        for line in lines[content_start:]:
            if _WALMART_HELPFUL_RE.search(line):
                break
            content_lines.append(line)

        content = " ".join(content_lines).strip()
        if not content:
            continue

        reviews.append({
            "content": content,
            "date": _normalize_date(date_str),
            "rating": rating,
            "reviewer": reviewer,
            "source": "Walmart",
            "raw_data": None,
        })

    return reviews


# ============================================================
# Amazon format parser
# ============================================================

_AMAZON_RATING_RE = re.compile(r"(\d(?:\.\d)?)\s+out\s+of\s+5\s+stars", re.IGNORECASE)
_AMAZON_DATE_RE = re.compile(
    r"Reviewed in .+ on ((?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{1,2},\s+\d{4})",
    re.IGNORECASE,
)
_AMAZON_SKIP_RE = re.compile(r"^(Verified Purchase|Helpful|Report|Top reviews?)$", re.IGNORECASE)


def parse_amazon_format(text: str) -> list[dict]:
    """解析 Amazon 复制粘贴格式的评论文本。"""
    all_lines = [ln.strip() for ln in text.splitlines()]

    # 以 "Reviewed in ... on [Date]" 行为锚点
    date_anchors: list[tuple[int, str]] = []
    for i, line in enumerate(all_lines):
        dm = _AMAZON_DATE_RE.search(line)
        if dm:
            date_anchors.append((i, dm.group(1)))

    reviews: list[dict] = []
    for idx, (date_idx, date_str) in enumerate(date_anchors):
        # 向前查找 rating（日期行前 5 行内）
        rating: int | None = None
        reviewer: str | None = None
        for j in range(date_idx - 1, max(date_idx - 6, -1), -1):
            rm = _AMAZON_RATING_RE.search(all_lines[j])
            if rm:
                rating = round(float(rm.group(1)))
                # reviewer 是 rating 行前第一个非空、非跳过行
                for k in range(j - 1, max(j - 4, -1), -1):
                    candidate = all_lines[k]
                    if candidate and not _AMAZON_SKIP_RE.match(candidate) and not _AMAZON_RATING_RE.search(candidate):
                        reviewer = candidate
                        break
                break

        # 内容：日期行之后到下一个锚点之前，跳过元数据行
        next_idx = date_anchors[idx + 1][0] if idx + 1 < len(date_anchors) else len(all_lines)
        content_lines: list[str] = []
        for line in all_lines[date_idx + 1: next_idx]:
            if line and not _AMAZON_SKIP_RE.match(line) and not _AMAZON_RATING_RE.search(line):
                content_lines.append(line)

        content = " ".join(content_lines).strip()
        if not content:
            continue

        reviews.append({
            "content": content,
            "date": _normalize_date(date_str),
            "rating": rating,
            "reviewer": reviewer,
            "source": "Amazon",
            "raw_data": None,
        })

    return reviews


# ============================================================
# AI fallback parser
# ============================================================

def _parse_unstructured_ai(text: str) -> list[dict]:
    """调用 DeepSeek API 解析无固定格式的评论文本（兜底方案）。"""
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("未配置 DEEPSEEK_API_KEY，无法解析非结构化文档")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    prompt = (
        "从以下文本中提取所有用户评论，以 JSON 数组返回，每条评论包含字段：\n"
        "content（评论内容，必须）、date（日期 YYYY-MM-DD，必须）、"
        "rating（评分 1-5 整数，无则 null）、reviewer（评论者，无则 null）、source（来源，无则 null）\n"
        "只返回 JSON 数组，不要其他文字。\n\n"
        f"文本：\n{text[:4000]}"
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()

    result: list[dict] = []
    for item in json.loads(raw):
        if not item.get("content") or not item.get("date"):
            continue
        result.append({
            "content": str(item["content"]).strip(),
            "date": _normalize_date(item.get("date")),
            "rating": int(item["rating"]) if item.get("rating") else None,
            "reviewer": item.get("reviewer"),
            "source": item.get("source"),
            "raw_data": None,
        })
    return result


# ============================================================
# Word / TXT parsing
# ============================================================

def _parse_docx_txt(file_path: str, file_type: str) -> pd.DataFrame:
    """解析 Word / TXT 文件，自动识别 Walmart / Amazon / 无固定格式。"""
    if file_type == "docx":
        from docx import Document
        doc = Document(file_path)
        text = "\n".join(p.text for p in doc.paragraphs)
    else:
        with open(file_path, encoding="utf-8-sig") as f:
            text = f.read()

    if _WALMART_DATE_RE.search(text) and _WALMART_RATING_RE.search(text):
        reviews = parse_walmart_format(text)
    elif _AMAZON_DATE_RE.search(text) and _AMAZON_RATING_RE.search(text):
        reviews = parse_amazon_format(text)
    else:
        reviews = _parse_unstructured_ai(text)

    if not reviews:
        raise ValueError("上传失败：未找到评论内容字段，请确认文件包含评论文字")

    df = pd.DataFrame(reviews)
    if df["content"].isna().all():
        raise ValueError("上传失败：未找到评论内容字段，请确认文件包含评论文字")
    if df["date"].isna().all():
        raise ValueError("上传失败：未找到日期字段，评论日期为必填项，用于时间维度分析和环比对比")

    return df


# ============================================================
# Main entry
# ============================================================

def parse_file(file_path: str, file_type: str) -> pd.DataFrame:
    """解析上传文件为标准化 DataFrame。

    Args:
        file_path: 文件绝对路径。
        file_type: 文件类型，支持 csv / xlsx / xls / docx / txt。

    Returns:
        包含 content / date / rating / reviewer / source / raw_data 列的 DataFrame。

    Raises:
        ValueError: 找不到必须字段（content 或 date）时抛出。
    """
    ft = file_type.lower().lstrip(".")
    if ft == "csv":
        return _parse_csv_excel(file_path, "csv")
    if ft in ("xlsx", "xls"):
        return _parse_csv_excel(file_path, "excel")
    if ft in ("docx", "txt"):
        return _parse_docx_txt(file_path, ft)
    raise ValueError(f"不支持的文件格式：{file_type}")


# ============================================================
# Duplicate detection
# ============================================================

def _compute_hash(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def check_duplicates(
    comments_list: list[dict],
    product_id: str,
    version: str,
    user_id: int,
) -> dict:
    """检测评论列表中与数据库已有记录重复的条目。

    Returns:
        dict with keys: new_count, duplicate_count, duplicates (list[dict]).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT content_hash FROM comments "
                "WHERE user_id = %s AND product_id = %s AND version = %s AND content_hash IS NOT NULL",
                (user_id, product_id, version),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    existing_hashes: set[str] = {r[0] for r in rows}

    duplicates: list[dict] = []
    new_count = 0
    for comment in comments_list:
        h = _compute_hash(comment.get("content", ""))
        comment["content_hash"] = h
        if h in existing_hashes:
            duplicates.append(comment)
        else:
            new_count += 1

    return {
        "new_count": new_count,
        "duplicate_count": len(duplicates),
        "duplicates": duplicates,
    }


def deduplicate_comments(
    comments_list: list[dict],
    product_id: str,
    version: str,
    user_id: int,
    action: str,
) -> list[dict]:
    """根据去重策略过滤评论列表。

    Args:
        action: 'append'（跳过重复）/ 'overwrite'（保留全部，调用方负责删除旧记录）/ 'cancel'（返回空列表）。

    Returns:
        过滤后待导入的评论列表。
    """
    if action == "cancel":
        return []

    result = check_duplicates(comments_list, product_id, version, user_id)
    if action == "append":
        dup_hashes = {c["content_hash"] for c in result["duplicates"]}
        return [c for c in comments_list if c.get("content_hash") not in dup_hashes]

    # overwrite: 返回全部，调用方负责先删除数据库中的重复记录
    return comments_list
