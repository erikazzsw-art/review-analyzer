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
    """
    return "\n".join(f"- {a['key']}: {a['label_zh']}" for a in aspects)


@lru_cache(maxsize=256)
def _load_aspects_from_db(sub_category: str) -> tuple[tuple[str, str], ...]:
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
                """SELECT aspect_key, label_zh
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

    return tuple((str(r["aspect_key"]), str(r["label_zh"])) for r in rows)


def resolve_aspects(sub_category: str) -> tuple[list[dict[str, str]], bool]:
    """按 sub_category 解析 aspect 清单.

    Returns:
        (aspects, is_taxonomy_hit)
        - aspects: list of {"key": ..., "label_zh": ...}
        - is_taxonomy_hit: True 表示 category_aspect_taxonomy 表命中，
          False 表示走 fallback（base aspect 通用块）
    """
    rows = _load_aspects_from_db(sub_category)
    if not rows:
        return get_fallback_aspects(), False

    aspects = [{"key": k, "label_zh": v} for k, v in rows if k != "other"]
    aspects.append({"key": "other", "label_zh": "其他"})
    return aspects, True


def clear_cache() -> None:
    """清空进程级缓存（测试 / taxonomy 表更新后调用）."""
    _load_aspects_from_db.cache_clear()
