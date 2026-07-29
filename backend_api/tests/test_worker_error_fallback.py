from __future__ import annotations

from types import SimpleNamespace

from backend_api.app.services.job_trace import JobTrace
from backend_api.app.services.llm_router import LLMRouter
from workers.jobs import _fallback_aspects_json_for_error


def test_job_trace_records_decisions_events_and_warnings_safely() -> None:
    trace = JobTrace(job_id=7, user_id=1)

    trace.begin_stage("cache")
    trace.end_stage(meta={"source_ids": {3, 2, 1}, "long": "x" * 800})
    trace.record_decision("cache_lookup", hit_sources={"user_history": 2})
    trace.record_event("llm_provider_attempt", provider="openai")
    trace.record_warning("llm_quality", schema_invalid=1)

    payload = trace.to_dict()

    assert payload["stages"][0]["name"] == "cache"
    assert payload["stages"][0]["meta"]["long"] == "x" * 500
    assert payload["decisions"][0]["name"] == "cache_lookup"
    assert payload["events"][0]["details"]["provider"] == "openai"
    assert payload["warnings"][0]["details"]["schema_invalid"] == 1


def test_error_fallback_aspects_json_is_structured_and_non_cacheable() -> None:
    payload = _fallback_aspects_json_for_error(
        {"error": "schema_invalid: sentiment"},
        sub_category="USB C Charger Block",
        prompt_version="v2.4",
    )

    assert payload["analysis_fallback"] is True
    assert payload["analysis_error"] == "schema_invalid: sentiment"
    assert payload["aspects"] == []
    assert payload["customer_label_occurrences"] == []
    assert payload["sub_category"] == "USB C Charger Block"
    assert payload["customer_label_occurrence_schema_version"] == "1.0"


def test_llm_router_returns_model_id_not_provider_name(monkeypatch) -> None:
    router = LLMRouter()
    trace_events = []

    class _Client:
        class chat:
            class completions:
                @staticmethod
                def create(**_kwargs):
                    return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=1))

    monkeypatch.setattr(router, "_get_client", lambda _model: _Client())

    _response, model_name = router.completion(
        messages=[{"role": "user", "content": "ping"}],
        locale="en",
        max_model_attempts=1,
        trace_callback=lambda kind, name, details: trace_events.append((kind, name, details)),
    )

    assert model_name == "gpt-4o-mini"
    assert ("event", "llm_router_chain") in [(kind, name) for kind, name, _details in trace_events]
    assert ("event", "llm_provider_attempt") in [(kind, name) for kind, name, _details in trace_events]
    assert ("event", "llm_provider_success") in [(kind, name) for kind, name, _details in trace_events]
