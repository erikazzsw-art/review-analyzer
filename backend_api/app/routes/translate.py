from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, status
from openai import APIError, APITimeoutError, AuthenticationError, OpenAI
from pydantic import BaseModel

from backend_api.app.deps import get_current_user
from backend_api.app.services.budget_guard import assert_budget
from review_analyzer.analyzer import get_api_key
from review_analyzer.database import get_connection, log_llm_usage
from review_analyzer.quota import quota_check, quota_consume

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/translate", tags=["translate"])


class TranslateModuleRequest(BaseModel):
    session_id: int
    module_key: str
    content: dict[str, Any]
    target_lang: str = "zh"


class TranslateModuleResponse(BaseModel):
    translated: dict[str, Any]


def _cache_key(
    user_id: int,
    session_id: int,
    module_key: str,
    target_lang: str,
    content: dict[str, Any],
) -> str:
    content_bytes = json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")
    content_hash = hashlib.sha256(content_bytes).hexdigest()
    raw = f"{user_id}:{session_id}:{module_key}:{target_lang}:{content_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_cached(cache_key: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT translated_json FROM translate_cache WHERE cache_key = %s",
                (cache_key,),
            )
            row = cur.fetchone()
            if not row:
                return None
            cur.execute(
                "UPDATE translate_cache SET accessed_at = NOW() WHERE cache_key = %s",
                (cache_key,),
            )
            conn.commit()
            raw = row["translated_json"]
            if isinstance(raw, str):
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return None
            return dict(raw) if isinstance(raw, dict) else None
    finally:
        conn.close()


def _save_cached(
    cache_key: str,
    user_id: int,
    session_id: int,
    module_key: str,
    target_lang: str,
    translated: dict[str, Any],
) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO translate_cache
                    (cache_key, user_id, session_id, module_key, target_lang, translated_json)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (cache_key) DO UPDATE SET
                    translated_json = EXCLUDED.translated_json,
                    accessed_at = NOW()
                """,
                (
                    cache_key,
                    user_id,
                    session_id,
                    module_key,
                    target_lang,
                    json.dumps(translated, ensure_ascii=False),
                ),
            )
            conn.commit()
    finally:
        conn.close()


@router.post("/module", response_model=TranslateModuleResponse)
def translate_module(
    body: TranslateModuleRequest,
    current_user: dict = Depends(get_current_user),
) -> TranslateModuleResponse:
    user_id = int(current_user["id"])

    cache_key = _cache_key(user_id, body.session_id, body.module_key, body.target_lang, body.content)
    cached = _load_cached(cache_key)
    if cached is not None:
        return TranslateModuleResponse(translated=cached)

    ok, msg = quota_check(user_id, "translate", amount=1)
    if not ok:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=msg)

    assert_budget(user_id)

    translated = _translate_payload(user_id, body.session_id, body.content, body.target_lang)
    if translated is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Translation failed. Please try again.",
        )

    quota_consume(user_id, "translate", amount=1)
    _save_cached(cache_key, user_id, body.session_id, body.module_key, body.target_lang, translated)
    return TranslateModuleResponse(translated=translated)


def _translate_payload(
    user_id: int,
    session_id: int,
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
        try:
            usage = getattr(response, "usage", None)
            if usage is not None:
                log_llm_usage(
                    user_id=user_id,
                    model_name="deepseek-chat",
                    tokens_in=int(getattr(usage, "prompt_tokens", 0) or 0),
                    tokens_out=int(getattr(usage, "completion_tokens", 0) or 0),
                    session_id=session_id,
                    sub_category="translate",
                )
        except Exception:
            logger.exception("translate: log_llm_usage failed")
        payload = json.loads(response.choices[0].message.content.strip())
        return payload if isinstance(payload, dict) else None
    except (APIError, APITimeoutError, AuthenticationError, json.JSONDecodeError, ValueError, TypeError):
        return None
