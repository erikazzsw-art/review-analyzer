from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend_api.app.deps import get_current_user
from backend_api.app.services.budget_guard import assert_budget
from backend_api.app.services.llm_router import router_completion
from review_analyzer.analyzer import get_api_key
from review_analyzer.database import get_connection, log_llm_usage
from review_analyzer.quota import credit_consume, InsufficientCreditsError, quota_check

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

    try:
        credit_consume(user_id, 1, "translate")
    except InsufficientCreditsError as e:
        raise HTTPException(status_code=402, detail=f"Not enough credits: {e.needed} needed, {e.balance} left")
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
        resp, model_name = router_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Translate ALL text values in the following JSON to {lang_name}. "
                        "Keep the JSON structure and keys exactly the same. "
                        "Only translate string values — leave numbers, booleans, nulls unchanged. "
                        "Output raw JSON only. No markdown fences, no explanation outside the JSON object."
                    ),
                },
                {"role": "user", "content": json.dumps(content, ensure_ascii=False)},
            ],
            temperature=0.1,
            max_tokens=3000,
            locale="en",
        )

        # 记录 LLM 用量
        try:
            usage = getattr(resp, "usage", None)
            if usage is not None:
                actual_model = getattr(resp, "model", model_name)
                log_llm_usage(
                    user_id=user_id,
                    model_name=actual_model,
                    tokens_in=int(getattr(usage, "prompt_tokens", 0) or 0),
                    tokens_out=int(getattr(usage, "completion_tokens", 0) or 0),
                    session_id=session_id,
                    sub_category="translate",
                    provider=model_name,
                )
        except Exception:
            logger.exception("translate: log_llm_usage failed")

        # JSON 解析 + 抢救：GPT-4o-mini 偶尔加 markdown fence
        text = resp.choices[0].message.content.strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                payload = json.loads(match.group())
            else:
                logger.error("translate: JSON parse failed, text=%s", text[:200])
                return None
        return payload if isinstance(payload, dict) else None
    except RuntimeError as e:
        logger.error("translate: all LLM models exhausted: %s", e)
        return None
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.error("translate: json decode error: %s", e)
        return None
