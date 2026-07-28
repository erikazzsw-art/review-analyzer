from __future__ import annotations

from types import SimpleNamespace

from backend_api.app.services.llm_router import LLMRouter
from workers.jobs import _fallback_aspects_json_for_error


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
    )

    assert model_name == "gpt-4o-mini"
