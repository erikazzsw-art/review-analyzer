"""M3.5 retention_cleanup 单元测试.

用 monkeypatch 替换 get_connection / send_inactivity_warning / anonymize_user,
测试每块的核心行为 + 边界 case。不连真实数据库,不发真实邮件。
"""
# ruff: noqa: E402, I001

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

os.environ.setdefault("API_SESSION_SECRET", "test-secret-for-unit-tests-only")

from workers import retention_cleanup


# ---------------------------------------------------------------------------
# 假 psycopg2 连接:记录所有 SQL + 提供可配置 fetchall/rowcount
# ---------------------------------------------------------------------------


class FakeCursor:
    """最小 DBAPI 游标 —— 记录 execute 调用,fetchall 返回预置数据。"""

    def __init__(self, script: list):
        # script: 依次消费的 fetchall 结果 / rowcount 值
        self._script = list(script)
        self.executed: list[tuple[str, tuple | None]] = []
        self._last_fetch: list | None = None
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql: str, params: tuple | None = None):
        # 兼容 psycopg2 传单参数(无 params)
        self.executed.append((sql.strip(), params))
        if not self._script:
            self._last_fetch = []
            self.rowcount = 0
            return
        item = self._script.pop(0)
        if isinstance(item, list):
            self._last_fetch = item
            self.rowcount = len(item)
        elif isinstance(item, int):
            self._last_fetch = []
            self.rowcount = item
        else:
            raise TypeError(f"unknown script item: {item!r}")

    def fetchall(self):
        return self._last_fetch or []

    def fetchone(self):
        return (self._last_fetch or [None])[0]


class FakeConn:
    def __init__(self, script: list):
        self._script = script
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.cursor_calls = 0
        self.last_cursor: FakeCursor | None = None

    def cursor(self, cursor_factory=None):
        self.cursor_calls += 1
        cur = FakeCursor(self._script)
        self.last_cursor = cur
        return cur

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def _fake_conn_factory(script_batches: list[list]):
    """返回一个可以被 monkeypatch 到 get_connection 的工厂,依次交付连接。"""
    batches = list(script_batches)

    def _factory():
        script = batches.pop(0) if batches else []
        return FakeConn(script)

    return _factory


# ---------------------------------------------------------------------------
# Block 1: notify inactive
# ---------------------------------------------------------------------------


def test_block1_no_candidates_returns_zero(monkeypatch):
    from review_analyzer import database

    monkeypatch.setattr(database, "get_connection", _fake_conn_factory([[[]]]))
    result = retention_cleanup._block1_notify_inactive()
    assert result == {"ok": True, "candidates": 0, "sent": 0, "failed": 0}


def test_block1_sends_and_marks_notified(monkeypatch):
    from review_analyzer import database, mailer

    # 第一次连接: SELECT 拿到 1 个候选; 第二次连接: UPDATE 标记 notified
    select_result = [{"id": 42, "username": "alice", "email": "alice@example.com"}]
    monkeypatch.setattr(
        database,
        "get_connection",
        _fake_conn_factory([[select_result], [1]]),
    )

    sent_calls: list[dict] = []

    def fake_send(to_email, username, deletion_date, locale=None):
        sent_calls.append({"to": to_email, "user": username, "when": deletion_date})
        return True, "sent"

    monkeypatch.setattr(mailer, "send_inactivity_warning", fake_send)

    result = retention_cleanup._block1_notify_inactive()
    assert result["sent"] == 1
    assert result["failed"] == 0
    assert result["candidates"] == 1
    assert sent_calls[0]["to"] == "alice@example.com"


def test_block1_send_failure_does_not_mark(monkeypatch):
    """发信失败 → 不标记时间戳,下一天可以再试。"""
    from review_analyzer import database, mailer

    select_result = [{"id": 7, "username": "bob", "email": "bob@example.com"}]
    # 只需要 1 个连接(SELECT),不该发生第二次连接(UPDATE)
    conn_factory = _fake_conn_factory([[select_result]])

    calls = {"count": 0}

    def factory():
        calls["count"] += 1
        return conn_factory()

    monkeypatch.setattr(database, "get_connection", factory)
    monkeypatch.setattr(
        mailer,
        "send_inactivity_warning",
        lambda to_email, username, deletion_date, locale=None: (False, "resend down"),
    )

    result = retention_cleanup._block1_notify_inactive()
    assert result["sent"] == 0
    assert result["failed"] == 1
    # 只有 SELECT 那 1 次拿连接,发信失败后没有 UPDATE 连接
    assert calls["count"] == 1


# ---------------------------------------------------------------------------
# Block 2: anonymize notified
# ---------------------------------------------------------------------------


def test_block2_no_candidates(monkeypatch):
    from review_analyzer import database

    monkeypatch.setattr(database, "get_connection", _fake_conn_factory([[[]]]))
    result = retention_cleanup._block2_anonymize_notified()
    assert result == {"ok": True, "candidates": 0, "anonymized": 0, "failed": 0}


def test_block2_calls_anonymize_for_each(monkeypatch):
    from review_analyzer import database

    select_result = [{"id": 100}, {"id": 101}, {"id": 102}]
    monkeypatch.setattr(database, "get_connection", _fake_conn_factory([[select_result]]))

    called_with: list[int] = []

    def fake_anon(user_id: int, scrambled_hash: str):
        called_with.append(user_id)
        # 校验 hash 非空且不等于任何真实密码(60 字符 bcrypt hash)
        assert len(scrambled_hash) >= 40

    monkeypatch.setattr(database, "anonymize_user", fake_anon)
    result = retention_cleanup._block2_anonymize_notified()
    assert result["anonymized"] == 3
    assert result["failed"] == 0
    assert called_with == [100, 101, 102]


def test_block2_one_failure_continues(monkeypatch):
    from review_analyzer import database

    monkeypatch.setattr(
        database, "get_connection", _fake_conn_factory([[[{"id": 1}, {"id": 2}, {"id": 3}]]])
    )

    def fake_anon(user_id: int, _hash: str):
        if user_id == 2:
            raise RuntimeError("simulated DB failure")

    monkeypatch.setattr(database, "anonymize_user", fake_anon)
    result = retention_cleanup._block2_anonymize_notified()
    assert result["anonymized"] == 2  # 1 和 3 成功
    assert result["failed"] == 1


# ---------------------------------------------------------------------------
# Block 3: hard delete after grace
# ---------------------------------------------------------------------------


def test_block3_no_candidates(monkeypatch):
    from review_analyzer import database

    monkeypatch.setattr(database, "get_connection", _fake_conn_factory([[[]]]))
    result = retention_cleanup._block3_hard_delete_after_grace()
    assert result["users_purged"] == 0
    assert result["rows_deleted"] == 0


def test_block3_iterates_tables_in_leaf_to_root_order(monkeypatch):
    """确认按 FK 叶子→根顺序删,防止未来重构改乱表顺序。"""
    from review_analyzer import database

    # 第一次 SELECT 拿到 1 个候选 user_id;
    # 后续每次连接对应 1 个 user 的 6 张表 DELETE (每 DELETE rowcount=5)
    select_conn = [[{"id": 999}]]
    delete_conn = [5, 5, 5, 5, 5, 5]  # 6 张表 * 5 rows

    monkeypatch.setattr(
        database, "get_connection", _fake_conn_factory([select_conn, delete_conn])
    )

    result = retention_cleanup._block3_hard_delete_after_grace()
    assert result["users_purged"] == 1
    assert result["rows_deleted"] == 30  # 6 * 5

    # 表顺序: review_trackers → action_items → comments → product_variants → products → sessions
    assert retention_cleanup._HARD_DELETE_TABLES == (
        "review_trackers",
        "action_items",
        "comments",
        "product_variants",
        "products",
        "sessions",
    )


def test_block3_review_pool_not_touched(monkeypatch):
    """用户级硬删不碰 review_pool；全局池由独立保留窗口清理。"""
    assert "review_pool" not in retention_cleanup._HARD_DELETE_TABLES


# ---------------------------------------------------------------------------
# Block 4: review_pool > 2 年
# ---------------------------------------------------------------------------


def test_block4_purges_stale_review_pool(monkeypatch):
    from review_analyzer import database

    monkeypatch.setattr(database, "get_connection", _fake_conn_factory([[88, 1, 1]]))
    result = retention_cleanup._block4_purge_review_pool()
    assert result == {"ok": True, "deleted": 88}


def test_block4_review_pool_uses_2_year_threshold(monkeypatch):
    from review_analyzer import database

    conn = FakeConn([0, 0, 0])
    monkeypatch.setattr(database, "get_connection", lambda: conn)
    retention_cleanup._block4_purge_review_pool()
    assert conn.last_cursor is not None
    delete_sql = conn.last_cursor.executed[0][0]
    assert "review_pool" in delete_sql
    assert "2 years" in delete_sql
    assert "IS NULL" in delete_sql


# ---------------------------------------------------------------------------
# Block 5: analytics_events > 90 天
# ---------------------------------------------------------------------------


def test_block4_purges_stale_events(monkeypatch):
    from review_analyzer import database

    monkeypatch.setattr(database, "get_connection", _fake_conn_factory([[1234]]))
    result = retention_cleanup._block4_purge_analytics_events()
    assert result == {"ok": True, "deleted": 1234}


def test_block4_uses_90_day_threshold(monkeypatch):
    """SQL 里必须写 '90 days',万一未来有人改动口径能被测试捕获。"""
    from review_analyzer import database

    conn = FakeConn([0])
    monkeypatch.setattr(database, "get_connection", lambda: conn)
    retention_cleanup._block4_purge_analytics_events()
    assert conn.last_cursor is not None
    sql = conn.last_cursor.executed[0][0]
    assert "analytics_events" in sql
    assert "90 days" in sql


# ---------------------------------------------------------------------------
# Block 5: llm_usage_log > 6 年
# ---------------------------------------------------------------------------


def test_block5_purges_ancient_llm_logs(monkeypatch):
    from review_analyzer import database

    monkeypatch.setattr(database, "get_connection", _fake_conn_factory([[42]]))
    result = retention_cleanup._block5_purge_llm_usage_log()
    assert result == {"ok": True, "deleted": 42}


def test_block5_uses_6_year_threshold(monkeypatch):
    """对齐 Shulex 的 6 年口径。"""
    from review_analyzer import database

    conn = FakeConn([0])
    monkeypatch.setattr(database, "get_connection", lambda: conn)
    retention_cleanup._block5_purge_llm_usage_log()
    sql = conn.last_cursor.executed[0][0]
    assert "llm_usage_log" in sql
    assert "6 years" in sql


# ---------------------------------------------------------------------------
# Block 6: soft-delete sessions/comments > 6 年
# ---------------------------------------------------------------------------


def test_block6_soft_deletes_both_tables(monkeypatch):
    from review_analyzer import database

    # 两次连接: sessions 300 行 + comments 500 行
    monkeypatch.setattr(
        database, "get_connection", _fake_conn_factory([[300], [500]])
    )
    result = retention_cleanup._block6_soft_delete_stale_business_data()
    assert result == {"ok": True, "sessions": 300, "comments": 500}


def test_block6_uses_update_not_delete(monkeypatch):
    """Block 6 是软删 → UPDATE...deleted_at = NOW(),不能是 DELETE。"""
    from review_analyzer import database

    conns: list[FakeConn] = []

    def make_conn():
        c = FakeConn([0])
        conns.append(c)
        return c

    monkeypatch.setattr(database, "get_connection", make_conn)
    retention_cleanup._block6_soft_delete_stale_business_data()

    assert len(conns) == 2
    for c in conns:
        sql = c.last_cursor.executed[0][0]
        assert sql.startswith("UPDATE")
        assert "deleted_at = NOW()" in sql
        assert "deleted_at IS NULL" in sql
        assert "6 years" in sql


# ---------------------------------------------------------------------------
# 顶层入口: retention_cleanup_job
# ---------------------------------------------------------------------------


def test_retention_cleanup_job_runs_all_seven_blocks(monkeypatch):
    """一个 block 抛出后,后续 block 仍会跑 + 结果里有 errors。"""
    called: list[str] = []

    def make_block(name: str, raises: bool = False):
        def _fn():
            called.append(name)
            if raises:
                raise RuntimeError(f"{name} failed")
            return {"ok": True, "processed": 0}

        return _fn

    monkeypatch.setattr(retention_cleanup, "_block1_notify_inactive", make_block("b1"))
    monkeypatch.setattr(retention_cleanup, "_block2_anonymize_notified", make_block("b2", raises=True))
    monkeypatch.setattr(retention_cleanup, "_block3_hard_delete_after_grace", make_block("b3"))
    monkeypatch.setattr(retention_cleanup, "_block4_purge_review_pool", make_block("b4_pool"))
    monkeypatch.setattr(retention_cleanup, "_block4_purge_analytics_events", make_block("b4_events"))
    monkeypatch.setattr(retention_cleanup, "_block5_purge_llm_usage_log", make_block("b5"))
    monkeypatch.setattr(
        retention_cleanup, "_block6_soft_delete_stale_business_data", make_block("b6")
    )

    result = retention_cleanup.retention_cleanup_job()

    # 7 块全都被调用了(b2 崩了不影响后续 block)
    assert called == ["b1", "b2", "b3", "b4_pool", "b4_events", "b5", "b6"]
    # 结果结构
    assert result["ok"] is False
    assert len(result["errors"]) == 1
    assert result["errors"][0]["block"] == "anonymize_notified"
    # 其他块的结果保留
    assert result["blocks"]["notify_inactive"] == {"ok": True, "processed": 0}
    assert "started_at" in result and "finished_at" in result


def test_scrambled_password_hash_is_bcrypt_and_unique():
    """匿名化用的 hash 必须是不可预测的 bcrypt 格式。"""
    h1 = retention_cleanup._scrambled_password_hash()
    h2 = retention_cleanup._scrambled_password_hash()
    assert h1 != h2  # random,不可能撞
    assert h1.startswith("$2b$") or h1.startswith("$2a$")  # bcrypt prefix
    assert len(h1) >= 55  # bcrypt hash 长度约 60


# ---------------------------------------------------------------------------
# 常量哨兵 —— 保证关键窗口没被误改
# ---------------------------------------------------------------------------


def test_retention_windows_match_shulex_alignment():
    """M3.5 决策记录: 对齐 Shulex 的 6y / 60d 窗口,inactivity 6m+90d。"""
    assert retention_cleanup._INACTIVE_THRESHOLD_MONTHS == 6
    assert retention_cleanup._NOTIFY_TO_ANONYMIZE_DAYS == 90
    assert retention_cleanup._DELETION_GRACE_DAYS == 60
    assert retention_cleanup._ANALYTICS_EVENTS_RETENTION_DAYS == 90
    assert retention_cleanup._LLM_USAGE_RETENTION_YEARS == 6
    assert retention_cleanup._REVIEW_POOL_RETENTION_YEARS == 2
    assert retention_cleanup._SESSIONS_COMMENTS_RETENTION_YEARS == 6
