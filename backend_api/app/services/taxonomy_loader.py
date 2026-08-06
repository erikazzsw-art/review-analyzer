"""V4-T1.5 Taxonomy 加载器（按 sub_category 注入 prompt aspect 块）.

设计要点：
- 进程级 LRU 缓存：taxonomy 数据天级别变化频率，避免每条评论查一次 DB
- 未命中（DB 无该 sub_category） → 回退到通用 base 块（与 data/taxonomy/seeds/base.yaml 同步）
- DB 异常时静默回退，不阻塞分析链路
- `other` 始终存在且固定最后一行（兜底语义）

公开 API：
- resolve_aspects(sub_category) -> (aspects, is_taxonomy_hit)
- render_aspects_block(aspects) -> str
"""
from __future__ import annotations

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


# 通用 base 块（与 data/taxonomy/seeds/base.yaml 内容对齐 v1.0）
# sub_category 在 category_aspect_taxonomy 表未命中时使用
_FALLBACK_BASE_ASPECTS: list[tuple[str, str]] = [
    ("build_quality", "做工"),
    ("durability", "耐用性"),
    ("material", "材质用料"),
    ("ease_of_use", "易用性"),
    ("aesthetics", "外观设计"),
    ("packaging", "包装"),
    ("shipping_damage", "运输损坏"),
    ("customer_service", "客服"),
    ("value_for_money", "性价比"),
    ("other", "其他"),
]


def get_fallback_aspects() -> list[dict[str, str]]:
    """返回 fallback base aspect 列表（通用 9 项 + other 兜底）."""
    return [{"key": k, "label_zh": v} for k, v in _FALLBACK_BASE_ASPECTS]


def render_aspects_block(aspects: list[dict[str, str]]) -> str:
    """把 aspect 列表渲染成 prompt 占位符替换用的多行块.

    格式：每行 `- {aspect_key}: {label_zh}`
    若 aspect 含 boundary_note，追加 `（边界: {boundary_note}）`
    """
    lines: list[str] = []
    for a in aspects:
        line = f"- {a['key']}: {a['label_zh']}"
        if a.get("boundary_note"):
            line += f"（边界: {a['boundary_note']}）"
        lines.append(line)
    return "\n".join(lines)


@lru_cache(maxsize=256)
def _load_aspects_from_db(sub_category: str) -> tuple[tuple[str, str, str], ...]:
    """查 category_aspect_taxonomy 表，返回不可变元组（lru_cache 可哈希要求）.

    未命中或 DB 异常 → 返回空元组（调用方据此走 fallback）.
    """
    if not sub_category:
        return ()

    try:
        import psycopg2.extras

        from review_analyzer.database import get_connection
    except Exception as exc:
        logger.warning("taxonomy_loader: cannot import db deps: %s", exc)
        return ()

    try:
        conn = get_connection()
    except Exception as exc:
        logger.warning("taxonomy_loader: get_connection failed: %s", exc)
        return ()

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT aspect_key, label_zh, boundary_note
                   FROM category_aspect_taxonomy
                   WHERE sub_category = %s
                   ORDER BY total_count DESC NULLS LAST, aspect_key""",
                (sub_category,),
            )
            rows = cur.fetchall()
    except Exception as exc:
        logger.warning(
            "taxonomy_loader: query failed for sub_category=%r: %s",
            sub_category, exc,
        )
        try:
            conn.rollback()
        except Exception:
            pass
        return ()
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return tuple(
        (str(r["aspect_key"]), str(r["label_zh"]), str(r.get("boundary_note") or ""))
        for r in rows
    )


def resolve_aspects(sub_category: str) -> tuple[list[dict[str, str]], bool]:
    """按 sub_category 解析 aspect 清单.

    Returns:
        (aspects, is_taxonomy_hit)
        - aspects: list of {"key": ..., "label_zh": ..., "boundary_note": ...}
        - is_taxonomy_hit: True 表示 category_aspect_taxonomy 表命中，
          False 表示走 fallback（base aspect 通用块）
    """
    rows = _load_aspects_from_db(sub_category)
    if not rows:
        return get_fallback_aspects(), False

    aspects: list[dict[str, str]] = []
    for row in rows:
        k, v = row[0], row[1]
        bn = row[2] if len(row) > 2 else ""
        if k != "other":
            aspects.append({"key": k, "label_zh": v, "boundary_note": bn})
    aspects.append({"key": "other", "label_zh": "其他", "boundary_note": ""})
    return aspects, True


def get_taxonomy_version(sub_category: str) -> str:
    """获取指定 sub_category 的 taxonomy 版本号.

    从 category_aspect_taxonomy 表查该 sub_category 的 taxonomy_version，
    取 MAX 值（正常情况同一 sub_category 的所有行版本一致）。
    未命中或 DB 异常 → 返回 'v1.0'（与 fallback base aspects 版本对齐）。

    Note: 该函数不走 lru_cache（调用频率低，且 resolve_aspects 已有缓存），
    如需缓存可后续加上。
    """
    if not sub_category:
        return "v1.0"

    try:
        from review_analyzer.database import get_connection
    except Exception:
        return "v1.0"

    try:
        conn = get_connection()
    except Exception:
        return "v1.0"

    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT MAX(taxonomy_version) AS version
                   FROM category_aspect_taxonomy
                   WHERE sub_category = %s""",
                (sub_category,),
            )
            row = cur.fetchone()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return "v1.0"
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if row and row[0]:
        return str(row[0])
    return "v1.0"


def clear_cache() -> None:
    """清空进程级缓存（测试 / taxonomy 表更新后调用）."""
    _load_aspects_from_db.cache_clear()
