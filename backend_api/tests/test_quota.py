"""配额系统单元测试 — 覆盖 quota.py 核心逻辑，不访问真实数据库."""
from __future__ import annotations

import review_analyzer.quota as quota_mod
from review_analyzer.quota import (
    _format_message,
    _get_limit,
    quota_check,
    quota_check_atomic,
    quota_refund,
)

# ── helpers ──────────────────────────────────────────────────────────────────

def _patch(monkeypatch, plan: str, used: int):
    monkeypatch.setattr(quota_mod, "get_user_plan", lambda uid: plan)
    monkeypatch.setattr(quota_mod, "_get_used_count", lambda uid, dim: used)


# ── _get_limit ────────────────────────────────────────────────────────────────

def test_get_limit_pro_unlimited():
    assert _get_limit("review_analyze", "pro") == 10000

def test_get_limit_unknown_dimension():
    assert _get_limit("nonexistent", "free") == -1

def test_get_limit_free_upload_rows():
    assert _get_limit("upload_rows_per_file", "free") == 500


# ── starter plan (regression: PLAN_LIMITS 曾漏配 starter 导致 fallback 到 free) ──

def test_get_limit_starter_not_fallback_to_free():
    # 抽三个关键维度确认 starter 不再和 free 同值
    assert _get_limit("review_analyze", "starter") == 5000
    assert _get_limit("ask_review", "starter") == 50
    assert _get_limit("upload_rows_per_file", "starter") == 1000

def test_starter_all_dimensions_have_key():
    from review_analyzer.quota import PLAN_LIMITS
    missing = [d for d, cfg in PLAN_LIMITS.items() if "starter" not in cfg["limits"]]
    assert not missing, f"缺 starter key 的维度: {missing}"


# ── per_request (no DB) ───────────────────────────────────────────────────────

def test_per_request_within_limit():
    allowed, _ = quota_check(1, "upload_rows_per_file", amount=300)
    assert allowed  # free limit=500, amount=300 → OK (no DB call needed)

def test_per_request_exceeds_limit(monkeypatch):
    monkeypatch.setattr(quota_mod, "get_user_plan", lambda uid: "free")
    allowed, msg = quota_check(1, "upload_rows_per_file", amount=600)
    assert not allowed
    assert "500" in msg

def test_per_request_pro_has_higher_limit(monkeypatch):
    monkeypatch.setattr(quota_mod, "get_user_plan", lambda uid: "pro")
    allowed, _ = quota_check(1, "upload_rows_per_file", amount=5000)
    assert allowed


# ── unlimited plan (limit = -1) ───────────────────────────────────────────────

def test_pro_unlimited_never_blocked(monkeypatch):
    _patch(monkeypatch, plan="pro", used=999999)
    # ask_review: pro → -1, should always pass
    allowed, _ = quota_check(1, "ask_review", amount=1)
    assert allowed

def test_team_review_analyze_at_limit(monkeypatch):
    # team limit=50000; used=49000 + amount=1000 = 50000 (exactly at limit) → allowed
    _patch(monkeypatch, plan="team", used=49000)
    allowed, _ = quota_check(1, "review_analyze", amount=1000)
    assert allowed


def test_team_review_analyze_over_limit(monkeypatch):
    # team limit=50000; used=49999 + amount=1000 = 50999 → denied
    _patch(monkeypatch, plan="team", used=49999)
    allowed, _ = quota_check(1, "review_analyze", amount=1000)
    assert not allowed


# ── monthly hard quota ────────────────────────────────────────────────────────

def test_free_at_limit_denied(monkeypatch):
    _patch(monkeypatch, plan="free", used=1500)
    allowed, msg = quota_check(1, "review_analyze", amount=1)
    assert not allowed
    assert "1500" in msg

def test_free_one_below_limit_allowed(monkeypatch):
    _patch(monkeypatch, plan="free", used=1499)
    allowed, _ = quota_check(1, "review_analyze", amount=1)
    assert allowed

def test_free_zero_used_allowed(monkeypatch):
    _patch(monkeypatch, plan="free", used=0)
    allowed, _ = quota_check(1, "review_analyze", amount=100)
    assert allowed


# ── concurrent type ───────────────────────────────────────────────────────────

def test_concurrent_free_at_limit_denied(monkeypatch):
    monkeypatch.setattr(quota_mod, "get_user_plan", lambda uid: "free")
    # compare_products: free=2, passing amount=2 means already AT limit
    allowed, msg = quota_check(1, "compare_products", amount=2)
    assert not allowed

def test_concurrent_free_below_limit_allowed(monkeypatch):
    monkeypatch.setattr(quota_mod, "get_user_plan", lambda uid: "free")
    allowed, _ = quota_check(1, "compare_products", amount=1)
    assert allowed


# ── quota_check_atomic ────────────────────────────────────────────────────────

def test_atomic_enough_remaining_allowed(monkeypatch):
    _patch(monkeypatch, plan="free", used=1000)
    # remaining = 1500 - 1000 = 500, amount=300 → OK
    allowed, _ = quota_check_atomic(1, "review_analyze", amount=300)
    assert allowed

def test_atomic_partially_remaining_denied(monkeypatch):
    _patch(monkeypatch, plan="free", used=1200)
    # remaining=300, amount=600 → must reject whole batch
    allowed, msg = quota_check_atomic(1, "review_analyze", amount=600)
    assert not allowed
    assert "300" in msg  # remaining in message

def test_atomic_zero_remaining_denied(monkeypatch):
    _patch(monkeypatch, plan="free", used=1500)
    allowed, _ = quota_check_atomic(1, "review_analyze", amount=1)
    assert not allowed

def test_atomic_pro_unlimited_always_allowed(monkeypatch):
    _patch(monkeypatch, plan="pro", used=0)
    allowed, _ = quota_check_atomic(1, "review_analyze", amount=9999)
    assert allowed


# ── quota_refund ──────────────────────────────────────────────────────────────

def test_refund_decrements_used(monkeypatch):
    calls = []

    def fake_conn():
        class FakeCur:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def execute(self, sql, params):
                calls.append(params)
        class FakeConn:
            def cursor(self): return FakeCur()
            def commit(self): pass
            def close(self): pass
        return FakeConn()

    monkeypatch.setattr(quota_mod, "get_connection", fake_conn)
    quota_refund(1, "review_analyze", amount=50)
    assert calls, "DB update should have been called"
    # first param is amount, then user_id
    assert calls[0][0] == 50

def test_refund_skips_per_request(monkeypatch):
    called = []
    monkeypatch.setattr(quota_mod, "get_connection", lambda: called.append(1))
    quota_refund(1, "upload_rows_per_file", amount=10)
    assert not called, "per_request quota should not touch DB"


# ── _format_message ───────────────────────────────────────────────────────────

def test_format_message_contains_numbers():
    msg = _format_message("review_analyze", used=1400, limit=1500)
    assert "1400" in msg
    assert "1500" in msg

def test_format_message_unknown_dimension():
    msg = _format_message("nonexistent", used=1, limit=10)
    assert "1" in msg and "10" in msg
