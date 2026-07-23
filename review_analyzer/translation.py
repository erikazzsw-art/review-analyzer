from __future__ import annotations

import json
from typing import Any

from backend_api.app.services.llm_router import router_completion

LANGUAGE_LABELS = {
    "en": "English",
    "zh": "Chinese",
}


def translate_result_module(user_id: int, module_payload: dict[str, Any], target_lang: str) -> dict[str, Any]:
    """Translate a structured results module while preserving the JSON shape."""
    return _translate_payload(user_id, module_payload, target_lang)


def translate_compare_dataset(user_id: int, dataset: dict[str, Any], target_lang: str) -> dict[str, Any]:
    """Translate a compare dataset while preserving its JSON shape."""
    return _translate_payload(user_id, dataset, target_lang)


def _translate_payload(user_id: int, payload: dict[str, Any], target_lang: str) -> dict[str, Any]:
    target_label = LANGUAGE_LABELS.get(target_lang, "Chinese")
    source_text = json.dumps(payload, ensure_ascii=False)
    locale = "zh" if target_lang == "zh" else "en"
    try:
        response, _model_name = router_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You translate structured JSON content for an ecommerce review analysis app. "
                        "Preserve the exact JSON keys and overall data shape. "
                        f"Translate only user-facing string values into {target_label}. "
                        "Do not remove fields or add commentary."
                    ),
                },
                {
                    "role": "user",
                    "content": source_text,
                },
            ],
            temperature=0.1,
            max_tokens=2200,
            response_format={"type": "json_object"},
            locale=locale,
        )
        translated = json.loads(response.choices[0].message.content.strip())
        if isinstance(translated, dict):
            return translated
    except (json.JSONDecodeError, ValueError, TypeError, RuntimeError):
        pass
    return payload
