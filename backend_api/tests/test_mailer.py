"""mailer 单元测试 —— locale 双语渲染 + unsubscribe token 生成/校验.

不发真实邮件,通过 monkey-patch resend.Emails.send 断言 payload。
"""
# ruff: noqa: E402, I001
# — 有意的 late import 顺序:必须在 os.environ.setdefault 之后再 import mailer,
#   否则 API_SESSION_SECRET 缺失会让 generate_unsubscribe_token 首次调用报错。

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

os.environ.setdefault("API_SESSION_SECRET", "test-secret-for-unit-tests-only")

from review_analyzer import mailer


# ---------------------------------------------------------------------------
# _normalize_locale
# ---------------------------------------------------------------------------


def test_normalize_locale_zh_variants():
    assert mailer._normalize_locale("zh-CN") == "zh-CN"
    assert mailer._normalize_locale("zh") == "zh-CN"
    assert mailer._normalize_locale("zh-Hans") == "zh-CN"
    assert mailer._normalize_locale("zh_TW") == "zh-CN"


def test_normalize_locale_en_variants():
    assert mailer._normalize_locale("en-US") == "en-US"
    assert mailer._normalize_locale("en") == "en-US"
    assert mailer._normalize_locale("en-GB") == "en-US"


def test_normalize_locale_falls_back_to_default():
    assert mailer._normalize_locale(None) == "en-US"
    assert mailer._normalize_locale("") == "en-US"
    assert mailer._normalize_locale("fr-FR") == "en-US"
    assert mailer._normalize_locale("ja-JP") == "en-US"


# ---------------------------------------------------------------------------
# 模板渲染
# ---------------------------------------------------------------------------


def test_render_reset_code_zh_contains_chinese_text():
    html = mailer._render_template("reset_code", "zh-CN", code="123456")
    assert "123456" in html
    assert "密码重置验证码" in html
    assert "ClueAI" in html


def test_render_reset_code_en_contains_english_text():
    html = mailer._render_template("reset_code", "en-US", code="123456")
    assert "123456" in html
    assert "password reset" in html.lower()
    assert "ClueAI" in html


def test_render_verification_zh_and_en_have_new_email():
    zh = mailer._render_template("verification", "zh-CN", code="ABC", new_email="foo@bar.com")
    en = mailer._render_template("verification", "en-US", code="ABC", new_email="foo@bar.com")
    for html in (zh, en):
        assert "foo@bar.com" in html
        assert "ABC" in html
    assert "邮箱" in zh
    assert "email" in en.lower()


def test_render_subscription_confirmed_dual_locale_substitution():
    zh = mailer._render_template(
        "subscription_confirmed",
        "zh-CN",
        username="Erika",
        plan_name="Pro",
        next_billing_date="2026-08-03",
    )
    en = mailer._render_template(
        "subscription_confirmed",
        "en-US",
        username="Erika",
        plan_name="Pro",
        next_billing_date="2026-08-03",
    )
    for html in (zh, en):
        assert "Erika" in html
        assert "Pro" in html
        assert "2026-08-03" in html


# ---------------------------------------------------------------------------
# 端到端 send_* (mock resend)
# ---------------------------------------------------------------------------


class _RecordingResend:
    """monkey-patch resend.Emails.send 用,记录调用 payload。"""

    def __init__(self):
        self.calls: list[dict] = []

    def send(self, payload: dict):
        self.calls.append(payload)
        return {"id": "test-email-id"}


def _install_mock(monkeypatch) -> _RecordingResend:
    rec = _RecordingResend()
    # 确保 _resend_send 里 api_key 检查能通过
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setattr(mailer.resend, "Emails", rec)
    return rec


def test_send_reset_code_zh_uses_transactional_from(monkeypatch):
    rec = _install_mock(monkeypatch)
    ok, err = mailer.send_reset_code("user@example.com", "654321", locale="zh-CN")
    assert ok, err
    assert len(rec.calls) == 1
    call = rec.calls[0]
    assert call["from"] == mailer.FROM_TRANSACTIONAL
    assert call["to"] == ["user@example.com"]
    assert call["subject"] == "ClueAI 密码重置验证码"
    assert "654321" in call["html"]


def test_send_reset_code_en_switches_subject_and_body(monkeypatch):
    rec = _install_mock(monkeypatch)
    ok, _ = mailer.send_reset_code("user@example.com", "654321", locale="en-US")
    assert ok
    call = rec.calls[0]
    assert "password reset" in call["subject"].lower()
    assert "password reset" in call["html"].lower()


def test_send_reset_code_defaults_to_zh_for_backcompat(monkeypatch):
    # send_reset_code(email, code) 的老签名仍应工作 → 中文
    rec = _install_mock(monkeypatch)
    ok, _ = mailer.send_reset_code("user@example.com", "111111")
    assert ok
    assert "密码" in rec.calls[0]["subject"]


def test_send_deletion_confirmed_dispatches_transactional(monkeypatch):
    rec = _install_mock(monkeypatch)
    ok, _ = mailer.send_deletion_confirmed(
        "user@example.com",
        deleted_at="2026-07-03T10:00:00Z",
        locale="en-US",
    )
    assert ok
    call = rec.calls[0]
    assert call["from"] == mailer.FROM_TRANSACTIONAL
    assert "2026-07-03T10:00:00Z" in call["html"]


def test_send_marketing_email_blocked_when_opt_in_false(monkeypatch):
    """opt-in 未打开时,marketing 邮件应被静默丢弃(fail-close)。"""
    rec = _install_mock(monkeypatch)
    monkeypatch.setattr(mailer, "_check_marketing_opt_in", lambda uid: False)

    ok, reason = mailer.send_marketing_email(
        "user@example.com",
        subject="Product Update",
        html="<p>Hi</p>",
        locale="en-US",
        user_id=42,
    )
    assert not ok
    assert "opt" in reason.lower()
    assert rec.calls == []  # 没有真的发出


def test_send_marketing_email_appends_unsubscribe_footer(monkeypatch):
    rec = _install_mock(monkeypatch)
    monkeypatch.setattr(mailer, "_check_marketing_opt_in", lambda uid: True)

    ok, _ = mailer.send_marketing_email(
        "user@example.com",
        subject="Product Update",
        html="<p>Hi Erika</p>",
        locale="zh-CN",
        user_id=42,
    )
    assert ok
    call = rec.calls[0]
    assert call["from"] == mailer.FROM_MARKETING
    assert "<p>Hi Erika</p>" in call["html"]
    assert "退订" in call["html"]  # zh footer
    assert "uid=42" in call["html"]
    assert "token=" in call["html"]


# ---------------------------------------------------------------------------
# unsubscribe token
# ---------------------------------------------------------------------------


def test_unsubscribe_token_is_deterministic():
    a = mailer.generate_unsubscribe_token(123)
    b = mailer.generate_unsubscribe_token(123)
    assert a == b
    assert len(a) == 16


def test_unsubscribe_token_differs_across_users():
    assert mailer.generate_unsubscribe_token(1) != mailer.generate_unsubscribe_token(2)


def test_verify_unsubscribe_token_positive():
    token = mailer.generate_unsubscribe_token(99)
    assert mailer.verify_unsubscribe_token(99, token)


def test_verify_unsubscribe_token_negative_on_wrong_uid():
    token = mailer.generate_unsubscribe_token(99)
    # 换成别的 user_id 应该校验不过
    assert not mailer.verify_unsubscribe_token(100, token)


def test_verify_unsubscribe_token_negative_on_tampered_token():
    token = mailer.generate_unsubscribe_token(99)
    tampered = ("0" * 16) if token != "0" * 16 else ("1" * 16)
    assert not mailer.verify_unsubscribe_token(99, tampered)


def test_build_unsubscribe_url_contains_uid_and_token():
    url = mailer.build_unsubscribe_url(7)
    assert "uid=7" in url
    assert "token=" in url
    # 提取 token 段并回验一次
    token = url.split("token=")[1]
    assert mailer.verify_unsubscribe_token(7, token)
