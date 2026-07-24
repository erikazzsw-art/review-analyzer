"""跨用户 LLM 分析结果复用 —— 单元测试（migration 043）.

覆盖：
- get_analyzed_by_content_hash 的 include_global 分支
- analyzer_version 校验隔离
- L1 缓存能正确带出 cache_hit_source 元信息
- CSV 上传 pool_backfill 触发（product_id 有值即回填）

策略：只 mock DB 连接，不真跑 psycopg2 / DeepSeek。
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ============================================================
# get_analyzed_by_content_hash：include_global 分支
# ============================================================


def _mock_conn_with_rows(user_rows: list[dict], pool_rows: list[dict]) -> MagicMock:
    """构造 mock connection：第一次 execute 返回 user_rows，第二次返回 pool_rows."""
    conn = MagicMock()
    cur = MagicMock()

    # 每次调用 fetchall 返回下一批
    fetch_seq = [user_rows, pool_rows]

    def _fetchall():
        return fetch_seq.pop(0) if fetch_seq else []

    cur.fetchall.side_effect = _fetchall
    conn.cursor.return_value.__enter__.return_value = cur
    return conn


def test_l1_user_hit_only():
    """场景：用户自己历史命中，不需要查 pool。"""
    from review_analyzer.database import get_analyzed_by_content_hash

    user_row = {
        "id": 42,
        "content_hash": "abc123",
        "sentiment": "positive",
        "aspects_json": {"aspects": []},
    }
    conn = _mock_conn_with_rows([user_row], [])

    with patch("review_analyzer.database.get_connection", return_value=conn):
        result = get_analyzed_by_content_hash(
            user_id=1,
            content_hashes=["abc123"],
            include_global=True,
            analyzer_version="v4_deep",
        )

    assert "abc123" in result
    assert result["abc123"]["cache_hit_source"] == "user"
    assert result["abc123"]["source_id"] == 42


def test_l1_global_hit_when_user_miss():
    """场景：用户自己没有，从全局 pool 命中（跨用户复用）."""
    from review_analyzer.database import get_analyzed_by_content_hash

    pool_row = {
        "id": 999,
        "content_hash": "xyz789",
        "sentiment": "negative",
        "aspects_json": {"aspects": [{"key": "quality"}]},
    }
    conn = _mock_conn_with_rows([], [pool_row])

    with patch("review_analyzer.database.get_connection", return_value=conn):
        result = get_analyzed_by_content_hash(
            user_id=2,
            content_hashes=["xyz789"],
            include_global=True,
            analyzer_version="v4_deep",
        )

    assert "xyz789" in result
    assert result["xyz789"]["cache_hit_source"] == "global"
    assert result["xyz789"]["source_id"] == 999


def test_include_global_disabled_skips_pool():
    """场景：include_global=False 时不查 pool，用户 miss 就 miss."""
    from review_analyzer.database import get_analyzed_by_content_hash

    pool_row = {
        "id": 999,
        "content_hash": "xyz789",
        "sentiment": "negative",
        "aspects_json": {"aspects": []},
    }
    # 即使 pool 有数据，include_global=False 应完全跳过
    conn = _mock_conn_with_rows([], [pool_row])

    with patch("review_analyzer.database.get_connection", return_value=conn):
        result = get_analyzed_by_content_hash(
            user_id=3,
            content_hashes=["xyz789"],
            include_global=False,
        )

    assert "xyz789" not in result


def test_user_hit_shadows_pool():
    """场景：用户自己命中优先于 pool，不会覆盖成 global."""
    from review_analyzer.database import get_analyzed_by_content_hash

    user_row = {
        "id": 42,
        "content_hash": "same_hash",
        "sentiment": "positive",
        "aspects_json": {"aspects": []},
    }
    pool_row = {
        "id": 888,
        "content_hash": "same_hash",
        "sentiment": "negative",  # 故意不同，验证不被 pool 覆盖
        "aspects_json": {"aspects": [{"key": "wrong"}]},
    }
    conn = _mock_conn_with_rows([user_row], [pool_row])

    with patch("review_analyzer.database.get_connection", return_value=conn):
        result = get_analyzed_by_content_hash(
            user_id=1,
            content_hashes=["same_hash"],
            include_global=True,
            analyzer_version="v4_deep",
        )

    # 用户自己的结果优先，不被 pool 覆盖
    assert result["same_hash"]["cache_hit_source"] == "user"
    assert result["same_hash"]["sentiment"] == "positive"
    assert result["same_hash"]["source_id"] == 42


def test_empty_content_hashes_returns_empty():
    """场景：空输入不触发 DB 调用."""
    from review_analyzer.database import get_analyzed_by_content_hash

    with patch("review_analyzer.database.get_connection") as mock_conn:
        result = get_analyzed_by_content_hash(user_id=1, content_hashes=[])
        assert result == {}
        mock_conn.assert_not_called()


# ============================================================
# 端到端：compute_content_hash 稳定性（跨用户前提）
# ============================================================


def test_content_hash_stable_across_users():
    """相同 (content, rating) 在不同调用中 hash 必须一致 —— 跨用户复用的基础."""
    from backend_api.app.services.analysis_cache import compute_content_hash

    h1 = compute_content_hash("This product is great!", 5)
    h2 = compute_content_hash("This product is great!", 5)
    assert h1 == h2

    # 大小写归一化
    h3 = compute_content_hash("THIS PRODUCT IS GREAT!", 5)
    assert h1 == h3

    # rating 变化则 hash 变化
    h4 = compute_content_hash("This product is great!", 4)
    assert h1 != h4


def test_apply_cache_uses_persisted_content_hash_with_category():
    """L1 must use the stored hash when category is part of the cache key."""
    from backend_api.app.services.analysis_cache import apply_cache, compute_content_hash

    content_hash = compute_content_hash("This product is great!", 5, "waders")
    result = apply_cache(
        comments=[
            {
                "id": 1,
                "content": "This product is great!",
                "rating": 5,
                "content_hash": content_hash,
            }
        ],
        existing_analyses={
            content_hash: {
                "sentiment": "positive",
                "aspects_json": {"aspects": [{"key": "fit"}]},
                "source_id": 99,
                "cache_hit_source": "global",
            }
        },
    )

    assert result.hit_count == 1
    assert result.miss_count == 0
    hit = result.hits[1]
    assert hit.level == "L1"
    assert hit.source_comment_id == 99


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
