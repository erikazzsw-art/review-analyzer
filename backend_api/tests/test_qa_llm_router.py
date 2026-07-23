from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from review_analyzer import qa_handlers
from review_analyzer.rag import answer_question


def _router_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _aggregation_comments() -> list[dict[str, Any]]:
    tags = ["durability", "size", "packaging", "durability", "size", "packaging"]
    return [
        {
            "id": idx,
            "product_id": "PARENT-1",
            "rating": 2,
            "date": "2026-01-01",
            "sentiment": "negative",
            "content": f"Review {idx} mentions {tag}.",
            "issue_tag": tag,
            "highlight_tag": "",
        }
        for idx, tag in enumerate(tags, 1)
    ]


def test_answer_question_passes_locale_to_handler(monkeypatch):
    captured: dict[str, Any] = {"locales": []}

    monkeypatch.setattr(
        "review_analyzer.qa_intent.classify_intent",
        lambda question, products_meta=None, history=None: {
            "intent": "specific_retrieval",
            "confidence": 0.5,
            "slots": {},
            "source": "test",
        },
    )

    def fake_handler(
        user_id: int,
        question: str,
        comments: list[dict[str, Any]],
        top_k: int,
        history: list[dict] | None,
        intent_result: dict[str, Any],
        fallback=None,
        locale: str = "en",
    ) -> qa_handlers.HandlerResult:
        captured["locales"].append(locale)
        captured["fallback"] = fallback
        return {
            "answer": "ok",
            "citations": [],
            "retrieval_method": "test",
            "aggregation_snapshot": None,
        }

    monkeypatch.setitem(
        qa_handlers.INTENT_HANDLERS,
        "specific_retrieval",
        fake_handler,
    )

    result = answer_question(1, "What do buyers mention?", [], locale="en")
    default_result = answer_question(1, "What do buyers mention?", [])

    assert result["answer"] == "ok"
    assert default_result["answer"] == "ok"
    assert captured["locales"] == ["en", "en"]
    assert captured["fallback"] is qa_handlers.retrieval_handler


def test_aggregate_feedback_handler_calls_router_completion_with_locale(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_router_completion(**kwargs):
        captured.update(kwargs)
        return _router_response("router answer"), "openai"

    monkeypatch.setattr(qa_handlers, "router_completion", fake_router_completion)

    result = qa_handlers.aggregate_feedback_handler(
        user_id=1,
        question="最常见的问题是什么？",
        comments=_aggregation_comments(),
        top_k=5,
        history=None,
        intent_result={"slots": {"polarity": "negative"}},
        locale="en",
    )

    assert result["answer"] == "router answer"
    assert captured["locale"] == "en"
    assert captured["temperature"] == 0.2
    assert captured["max_tokens"] == 800
    assert "model" not in captured


def test_aggregate_feedback_handler_falls_back_when_router_fails(monkeypatch):
    def failing_router_completion(**kwargs):
        raise RuntimeError("router unavailable")

    monkeypatch.setattr(qa_handlers, "router_completion", failing_router_completion)

    result = qa_handlers.aggregate_feedback_handler(
        user_id=1,
        question="最常见的问题是什么？",
        comments=_aggregation_comments(),
        top_k=5,
        history=None,
        intent_result={"slots": {"polarity": "negative"}},
        locale="en",
    )

    assert result["retrieval_method"] == "aggregation"
    assert result["answer"].startswith("根据评论标签聚合")
    assert "Top 5" in result["answer"]
    assert result["citations"]
