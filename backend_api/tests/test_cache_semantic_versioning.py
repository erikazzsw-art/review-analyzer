"""5.9.6-B.1: 缓存语义版本化 + L2 下线 —— 单元测试.

覆盖：
- get_analyzed_by_content_hash 的 JSONB 版本过滤 SQL 构造（4 个维度）
- L2 分支已删除（短文本/极端评分不再跳过 LLM）
- CacheResult.stats() 不再包含 L2
- _cache_observability_summary 不产出 short_text_rating_rule
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ============================================================
# 辅助
# ============================================================

def _version_aspects_json(overrides: dict | None = None) -> dict:
    """构造含全部四个语义版本字段的 aspects_json."""
    base = {
        "sentiment": "neutral",
        "aspects": [],
        "pain_points": [],
        "highlights": [],
        "prompt_version": "v2.4",
        "taxonomy_version": "v1.0",
        "registry_version": "review-fragment-label-registry.5.9.6-A.1",
        "model_name": "gpt-4o-mini",
    }
    if overrides:
        base.update(overrides)
    return base


def compute_content_hash_fn(content: str, rating: int = 0, category: str | None = None) -> str:
    """compute_content_hash 的测试辅助."""
    import hashlib
    normalized = content.strip().lower()
    key = f"{normalized}|{rating}"
    if category:
        key = f"{key}|{category.strip().lower()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


# ============================================================
# 1. get_analyzed_by_content_hash：语义版本校验
# ============================================================

def test_l1_version_filter_in_sql_when_all_four_provided():
    """场景：传入全部四个版本参数 → SQL 含对应 ->> 过滤子句."""
    from review_analyzer.database import get_analyzed_by_content_hash

    user_row = {
        "id": 1,
        "content_hash": "abc123",
        "sentiment": "positive",
        "aspects_json": _version_aspects_json(),
    }
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchall.return_value = [user_row]
    conn.cursor.return_value.__enter__.return_value = cur

    with patch("review_analyzer.database.get_connection", return_value=conn):
        get_analyzed_by_content_hash(
            user_id=1,
            content_hashes=["abc123"],
            include_global=True,
            prompt_version="v2.4",
            taxonomy_version="v1.0",
            registry_version="review-fragment-label-registry.5.9.6-A.1",
            model_name="gpt-4o-mini",
        )

    # 验证 execute 被调用的 SQL 含版本过滤
    user_sql = cur.execute.call_args_list[0][0][0]
    assert "aspects_json->>'prompt_version'" in user_sql
    assert "aspects_json->>'taxonomy_version'" in user_sql
    assert "aspects_json->>'registry_version'" in user_sql
    assert "aspects_json->>'model_name'" in user_sql

    # 验证参数含版本值
    user_params = cur.execute.call_args_list[0][0][1]
    assert "v2.4" in user_params
    assert "v1.0" in user_params
    assert "review-fragment-label-registry.5.9.6-A.1" in user_params
    assert "gpt-4o-mini" in user_params


def test_l1_no_version_filter_when_no_version_params():
    """场景：不传版本参数 → SQL 不含版本过滤子句."""
    from review_analyzer.database import get_analyzed_by_content_hash

    user_row = {
        "id": 1,
        "content_hash": "abc123",
        "sentiment": "positive",
        "aspects_json": {"sentiment": "positive", "aspects": []},
    }
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchall.return_value = [user_row]
    conn.cursor.return_value.__enter__.return_value = cur

    with patch("review_analyzer.database.get_connection", return_value=conn):
        get_analyzed_by_content_hash(
            user_id=1,
            content_hashes=["abc123"],
            include_global=True,
        )

    user_sql = cur.execute.call_args_list[0][0][0]
    assert "aspects_json->>'" not in user_sql, (
        "不传版本参数时 SQL 不应含 ->> 过滤"
    )


def test_l1_single_version_param_adds_single_filter():
    """场景：只传 prompt_version → SQL 只含一个 ->> 过滤."""
    from review_analyzer.database import get_analyzed_by_content_hash

    user_row = {
        "id": 1,
        "content_hash": "abc123",
        "sentiment": "positive",
        "aspects_json": {"sentiment": "positive", "aspects": [], "prompt_version": "v2.4"},
    }
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchall.return_value = [user_row]
    conn.cursor.return_value.__enter__.return_value = cur

    with patch("review_analyzer.database.get_connection", return_value=conn):
        get_analyzed_by_content_hash(
            user_id=1,
            content_hashes=["abc123"],
            include_global=True,
            prompt_version="v2.4",
        )

    user_sql = cur.execute.call_args_list[0][0][0]
    assert "aspects_json->>'prompt_version'" in user_sql
    assert "aspects_json->>'taxonomy_version'" not in user_sql
    assert "aspects_json->>'registry_version'" not in user_sql
    assert "aspects_json->>'model_name'" not in user_sql


def test_l1_pool_query_includes_version_filter():
    """场景：用户 miss 后查 pool → pool 查询也含版本过滤."""
    from review_analyzer.database import get_analyzed_by_content_hash

    pool_row = {
        "id": 999,
        "content_hash": "abc123",
        "sentiment": "neutral",
        "aspects_json": _version_aspects_json(),
    }
    conn = MagicMock()
    cur = MagicMock()
    # 第一次 fetchall: user query 返回空（用户 miss）
    # 第二次 fetchall: pool query 返回 pool row
    cur.fetchall.side_effect = [[], [pool_row]]
    conn.cursor.return_value.__enter__.return_value = cur

    with patch("review_analyzer.database.get_connection", return_value=conn):
        result = get_analyzed_by_content_hash(
            user_id=1,
            content_hashes=["abc123"],
            include_global=True,
            analyzer_version="v4_deep",
            prompt_version="v2.4",
            taxonomy_version="v1.0",
            registry_version="review-fragment-label-registry.5.9.6-A.1",
            model_name="gpt-4o-mini",
        )

    # pool 命中
    assert "abc123" in result
    assert result["abc123"]["cache_hit_source"] == "global"

    # 两次 execute 都被调用
    assert cur.execute.call_count >= 2

    # 第二次调用（pool 查询）的 SQL 应含版本过滤
    pool_sql = cur.execute.call_args_list[1][0][0]
    assert "aspects_json->>'prompt_version'" in pool_sql
    assert "aspects_json->>'taxonomy_version'" in pool_sql
    assert "aspects_json->>'registry_version'" in pool_sql
    assert "aspects_json->>'model_name'" in pool_sql


def test_l1_version_params_backward_compatible():
    """场景：不传版本参数 → 行为与旧调用方一致（不报错）."""
    from review_analyzer.database import get_analyzed_by_content_hash

    user_row = {
        "id": 1,
        "content_hash": "abc123",
        "sentiment": "positive",
        "aspects_json": {"sentiment": "positive", "aspects": []},
    }
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchall.return_value = [user_row]
    conn.cursor.return_value.__enter__.return_value = cur

    with patch("review_analyzer.database.get_connection", return_value=conn):
        result = get_analyzed_by_content_hash(
            user_id=1,
            content_hashes=["abc123"],
            include_global=True,
        )

    assert "abc123" in result


# ============================================================
# 2. L2 分支已删除
# ============================================================


def test_l2_branch_no_longer_exists():
    """确认 _check_l2 函数已删除."""
    from backend_api.app.services import analysis_cache

    assert not hasattr(analysis_cache, "_check_l2"), (
        "L2 分支应在 5.9.6-B.1 删除"
    )


def test_l2_constant_no_longer_exists():
    """确认 L2_MAX_CONTENT_LENGTH 常量已删除."""
    from backend_api.app.services import analysis_cache

    assert not hasattr(analysis_cache, "L2_MAX_CONTENT_LENGTH"), (
        "L2_MAX_CONTENT_LENGTH 常量应在 5.9.6-B.1 删除"
    )


def test_short_text_extreme_rating_not_l2_hit():
    """场景：短文本 + 极端评分 → 不再命中 L2，应进入 LLM 或 miss."""
    from backend_api.app.services.analysis_cache import CacheResult, apply_cache

    comments = [
        {
            "id": 1,
            "content": "Leaks.",
            "rating": 1,
            "embedding": None,
        },
    ]
    existing_analyses: dict[str, dict] = {}

    result: CacheResult = apply_cache(
        comments=comments,
        existing_analyses=existing_analyses,
        reference_embeddings=None,
        reference_ids=None,
        reference_results=None,
    )

    # L2 已删除："Leaks."（6 字，1 星）不应被 L2 捕获，应进入 miss
    assert result.hit_count == 0
    assert result.miss_count == 1
    assert 1 in result.misses


def test_cache_result_stats_no_l2_key():
    """确认 CacheResult.stats() 不返回 L2 键."""
    from backend_api.app.services.analysis_cache import CacheHit, CacheResult

    result = CacheResult()
    result.hits[1] = CacheHit(comment_id=1, level="L1", result={})
    result.hits[2] = CacheHit(comment_id=2, level="L3", result={})

    stats = result.stats()

    assert "L1" in stats
    assert "L3" in stats
    assert "L2" not in stats, "stats() 不应再包含 L2 键"


def test_apply_cache_chain_is_l1_to_l3():
    """确认 apply_cache 链路是 L1→L3（无 L2）."""
    from backend_api.app.services.analysis_cache import CacheResult, apply_cache

    comments = [
        {"id": 1, "content": "Great product.", "rating": 5, "embedding": [0.1, 0.2]},
        {"id": 2, "content": "Bad quality.", "rating": 2, "embedding": [0.3, 0.4]},
        {"id": 3, "content": "OK.", "rating": 3, "embedding": None},
    ]

    # L1 命中第一条
    existing = {
        compute_content_hash_fn("Great product.", 5): {
            "aspects_json": {"sentiment": "positive", "aspects": []},
            "sentiment": "positive",
            "source_id": 100,
            "cache_hit_source": "user",
        },
    }

    result: CacheResult = apply_cache(
        comments=comments,
        existing_analyses=existing,
        reference_embeddings=None,
        reference_ids=None,
        reference_results=None,
    )

    # 只有 L1 命中 1 条，其余 2 条 miss
    assert result.hit_count == 1
    assert result.miss_count == 2
    assert 1 in result.hits
    assert result.hits[1].level == "L1"
    for hit in result.hits.values():
        assert hit.level != "L2", "apply_cache 不应再产出 L2 hit"


# ============================================================
# 3. _cache_observability_summary：无 L2 source
# ============================================================


def test_observability_summary_no_short_text_source():
    """确认 observability summary 不产出 short_text_rating_rule source."""
    from backend_api.app.services.analysis_cache import CacheResult
    from workers.jobs import _cache_observability_summary

    cache_result = CacheResult()
    cache_result.misses = [3]

    cache_input = [
        {"id": 1, "content": "Good.", "rating": 5, "embedding": None},
        {"id": 2, "content": "Bad.", "rating": 1, "embedding": None},
        {"id": 3, "content": "Leaks.", "rating": 1, "embedding": None},
    ]

    summary = _cache_observability_summary(
        cache_result=cache_result,
        cache_input=cache_input,
        existing_analyses={},
        reference_embeddings=None,
        reference_ids=None,
        reference_results=None,
    )

    assert "short_text_rating_rule" not in summary["hit_sources"], (
        "L2 已删除，不应出现 short_text_rating_rule"
    )


def test_observability_miss_for_short_text_shows_embedding_missing():
    """场景：短文本不再被 L2 捕获，miss reason 应为 embedding_missing."""
    from backend_api.app.services.analysis_cache import CacheResult
    from workers.jobs import _cache_observability_summary

    cache_result = CacheResult()
    cache_result.misses = [1]

    cache_input = [
        {"id": 1, "content": "Leaks.", "rating": 1, "embedding": None},
    ]

    summary = _cache_observability_summary(
        cache_result=cache_result,
        cache_input=cache_input,
        existing_analyses={},
        reference_embeddings=None,
        reference_ids=None,
        reference_results=None,
    )

    assert summary["miss_reasons"].get("embedding_missing", 0) == 1, (
        "无 embedding 的短文本应归因为 embedding_missing，不再是 L2 命中"
    )


# ============================================================
# 4. taxonomy_version 解析
# ============================================================


def test_get_taxonomy_version_fallback_on_db_error():
    """DB 异常时返回默认 v1.0."""
    from backend_api.app.services.taxonomy_loader import get_taxonomy_version

    with patch(
        "review_analyzer.database.get_connection",
        side_effect=Exception("no db"),
    ):
        version = get_taxonomy_version("保温杯")
        assert version == "v1.0"


def test_get_taxonomy_version_empty_sub_category():
    """空 sub_category 返回 v1.0."""
    from backend_api.app.services.taxonomy_loader import get_taxonomy_version

    assert get_taxonomy_version("") == "v1.0"
