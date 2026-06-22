from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from openai import APIError, APITimeoutError, AuthenticationError, OpenAI
from pydantic import BaseModel

from backend_api.app.deps import get_current_user
from review_analyzer.analyzer import get_api_key

router = APIRouter(prefix="/translate", tags=["translate"])


class TranslateModuleRequest(BaseModel):
    session_id: int
    module_key: str
    content: dict[str, Any]
    target_lang: str = "zh"


class TranslateModuleResponse(BaseModel):
    translated: dict[str, Any]


@router.post("/module", response_model=TranslateModuleResponse)
def translate_module(
    body: TranslateModuleRequest,
    current_user: dict = Depends(get_current_user),
) -> TranslateModuleResponse:
    user_id = int(current_user["id"])
    translated = _translate_payload(user_id, body.content, body.target_lang)
    if translated is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Translation failed. Please try again.",
        )
    return TranslateModuleResponse(translated=translated)


def _translate_payload(
    user_id: int,
    content: dict[str, Any],
    target_lang: str,
) -> dict[str, Any] | None:
    lang_name = "Chinese" if target_lang == "zh" else "English"
    try:
        client = OpenAI(
            api_key=get_api_key(user_id),
            base_url="https://api.deepseek.com/v1",
            timeout=30.0,
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Translate ALL text values in the following JSON to {lang_name}. "
                        "Keep the JSON structure and keys exactly the same. "
                        "Only translate string values — leave numbers, booleans, nulls unchanged. "
                        "Return ONLY the translated JSON object, no markdown."
                    ),
                },
                {"role": "user", "content": json.dumps(content, ensure_ascii=False)},
            ],
            temperature=0.1,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )
        payload = json.loads(response.choices[0].message.content.strip())
        return payload if isinstance(payload, dict) else None
    except (APIError, APITimeoutError, AuthenticationError, json.JSONDecodeError, ValueError, TypeError):
        return None
