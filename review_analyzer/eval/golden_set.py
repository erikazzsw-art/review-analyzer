"""Golden Set 加载器.

读取 data/golden_set/{version}/ai_annotated_500.csv + review_progress.json，
派生 gold_sentiment（accept → AI 标注；reject → 由 rating + note 推导）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent


def load_golden_set(version: str = "v1.0") -> pd.DataFrame:
    """加载 Golden Set 评测集，返回带 gold_sentiment 列的 DataFrame.

    Args:
        version: golden_set 子目录名（默认 v1.0）

    Returns:
        DataFrame with columns: review_id, sub_category, rating, title, content,
        ai_sentiment, gold_sentiment, review_action

    Raises:
        FileNotFoundError: 目录或文件缺失
    """
    base = ROOT / "data" / "golden_set" / version
    annotated_path = base / "ai_annotated_500.csv"
    progress_path = base / "review_progress.json"

    if not annotated_path.exists():
        raise FileNotFoundError(f"找不到标注文件: {annotated_path}")
    if not progress_path.exists():
        raise FileNotFoundError(f"找不到 review 进度: {progress_path}")

    df = pd.read_csv(annotated_path)
    df = df[df["annotation_status"] == "ai_pending_review"].copy()
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    reviewed_ids = set(progress.get("reviewed_ids", []))
    modifications: dict[str, dict[str, Any]] = progress.get("modifications", {})
    df = df[df["review_id"].isin(reviewed_ids)].copy()

    def _derive_gold(row: pd.Series) -> str | None:
        rid = row["review_id"]
        mod = modifications.get(rid, {})
        if mod.get("action") == "accept":
            return row["ai_sentiment"]

        # reject 时优先解析 note 中"情感应为 X / should be X"等显式声明
        note_lower = (mod.get("note") or "").lower()
        explicit_markers = [
            ("情感应为 neutral", "neutral"),
            ("情感应为 positive", "positive"),
            ("情感应为 negative", "negative"),
            ("情感判断为中性", "neutral"),
            ("情感判断为 neutral", "neutral"),
            ("情感判断为 positive", "positive"),
            ("情感判断为 negative", "negative"),
            ("应改为 neutral", "neutral"),
            ("应改为 positive", "positive"),
            ("应改为 negative", "negative"),
            ("应为 neutral", "neutral"),
            ("应为 positive", "positive"),
            ("应为 negative", "negative"),
            ("should be neutral", "neutral"),
            ("should be positive", "positive"),
            ("should be negative", "negative"),
            ("sentiment: neutral", "neutral"),
            ("sentiment: positive", "positive"),
            ("sentiment: negative", "negative"),
        ]
        for keyword, label in explicit_markers:
            if keyword in note_lower:
                return label

        # 没有显式声明时回退到评分启发式
        rating = row.get("rating")
        if pd.isna(rating):
            return None
        rating = int(rating)
        if rating >= 4:
            return "positive"
        if rating <= 2:
            if any(k in note_lower for k in ["positive", "正面", "love", "nothing wrong"]):
                return "positive"
            return "negative"
        # 3 星且 note 无显式声明 → 默认 neutral（不再默认 negative）
        return "neutral"

    df["gold_sentiment"] = df.apply(_derive_gold, axis=1)
    df["review_action"] = df["review_id"].map(
        lambda rid: modifications.get(rid, {}).get("action", "accept")
    )
    return df.reset_index(drop=True)


def get_golden_set_path(version: str = "v1.0") -> Path:
    return ROOT / "data" / "golden_set" / version
