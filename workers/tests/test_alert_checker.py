"""Focused tests for observability alert checker notification behavior."""
from __future__ import annotations

from workers import alert_checker


def _alert() -> dict:
    return {
        "id": "user:llm_error_rate",
        "dedupe_key": "user:llm_error_rate",
        "type": "llm_error_rate",
        "severity": "critical",
        "title": "LLM 错误率过高",
        "message": "最近 1 小时错误率 25%",
        "metric_value": 25,
        "threshold": 20,
        "unit": "%",
        "details": {},
    }


def test_check_alerts_for_user_sends_once_when_dedupe_allows(monkeypatch):
    config = {"enabled": True, "dedupe_ttl_seconds": 3600}
    locks = iter([True, False])
    sent: list[dict] = []
    recorded: list[dict] = []

    monkeypatch.setattr(alert_checker, "load_alert_config", lambda user_id: config)
    monkeypatch.setattr(alert_checker, "evaluate_alerts", lambda user_id, cfg: [_alert()])
    monkeypatch.setattr(alert_checker, "_acquire_dedupe_lock", lambda user_id, alert, ttl: next(locks))
    monkeypatch.setattr(alert_checker, "_notification_target", lambda cfg: ("feishu", "https://example.test/hook", ""))

    def fake_send(platform, webhook_url, text, signing_key):
        sent.append({"platform": platform, "url": webhook_url, "text": text, "signing_key": signing_key})
        return {"ok": True, "msg": "sent"}

    monkeypatch.setattr(alert_checker, "send_text_notification", fake_send)
    monkeypatch.setattr(
        alert_checker,
        "record_alert_event",
        lambda user_id, alert, notification_status, notification_message="": recorded.append(
            {
                "user_id": user_id,
                "status": notification_status,
                "message": notification_message,
            }
        ),
    )

    first = alert_checker.check_alerts_for_user(7)
    second = alert_checker.check_alerts_for_user(7)

    assert first["sent"] == 1
    assert second["deduped"] == 1
    assert len(sent) == 1
    assert recorded == [{"user_id": 7, "status": "sent", "message": "sent"}]


def test_check_alerts_for_user_records_no_webhook_without_sending(monkeypatch):
    config = {"enabled": True, "dedupe_ttl_seconds": 3600}
    recorded: list[dict] = []

    monkeypatch.setattr(alert_checker, "load_alert_config", lambda user_id: config)
    monkeypatch.setattr(alert_checker, "evaluate_alerts", lambda user_id, cfg: [_alert()])
    monkeypatch.setattr(alert_checker, "_acquire_dedupe_lock", lambda user_id, alert, ttl: True)
    monkeypatch.setattr(alert_checker, "_notification_target", lambda cfg: ("feishu", "", ""))
    monkeypatch.setattr(
        alert_checker,
        "send_text_notification",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not send")),
    )
    monkeypatch.setattr(
        alert_checker,
        "record_alert_event",
        lambda user_id, alert, notification_status, notification_message="": recorded.append(
            {"user_id": user_id, "status": notification_status, "message": notification_message}
        ),
    )

    result = alert_checker.check_alerts_for_user(9)

    assert result["no_webhook"] == 1
    assert recorded == [{"user_id": 9, "status": "no_webhook", "message": "No webhook configured"}]
