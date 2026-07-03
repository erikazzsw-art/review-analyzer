from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import HTTPException, Request, Response, status

from backend_api.app.config import get_settings
from review_analyzer.database import get_user_by_id


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(payload: str) -> str:
    settings = get_settings()
    digest = hmac.new(
        settings.session_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _b64encode(digest)


def _serialize_token(data: dict[str, Any]) -> str:
    payload = json.dumps(data, separators=(",", ":"), sort_keys=True)
    encoded_payload = _b64encode(payload.encode("utf-8"))
    signature = _sign(encoded_payload)
    return f"{encoded_payload}.{signature}"


def _deserialize_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        encoded_payload, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token.",
        ) from exc

    expected_signature = _sign(encoded_payload)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session signature.",
        )

    payload = json.loads(_b64decode(encoded_payload).decode("utf-8"))
    if str(payload.get("token_type")) != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unexpected session token type.",
        )

    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token expired.",
        )

    return payload


def create_access_token(user_id: int, username: str) -> str:
    settings = get_settings()
    return _serialize_token(
        {
            "user_id": user_id,
            "username": username,
            "token_type": "access",
            "exp": int(time.time()) + settings.access_ttl_seconds,
        }
    )


def create_refresh_token(user_id: int, username: str) -> str:
    settings = get_settings()
    return _serialize_token(
        {
            "user_id": user_id,
            "username": username,
            "token_type": "refresh",
            "exp": int(time.time()) + settings.refresh_ttl_seconds,
        }
    )


def set_auth_cookies(response: Response, user_id: int, username: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.access_cookie_name,
        value=create_access_token(user_id, username),
        max_age=settings.access_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        domain=settings.cookie_domain,
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=create_refresh_token(user_id, username),
        max_age=settings.refresh_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        domain=settings.cookie_domain,
    )


def clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.access_cookie_name,
        path="/",
        domain=settings.cookie_domain,
    )
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path="/",
        domain=settings.cookie_domain,
    )


def _get_authenticated_user(
    access_token: str | None,
    refresh_token: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] | None = None
    if access_token:
        try:
            payload = _deserialize_token(access_token, "access")
        except HTTPException:
            payload = None

    if payload is None and refresh_token:
        payload = _deserialize_token(refresh_token, "refresh")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    user_id = int(payload["user_id"])
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not exist.",
        )
    # V4-出海-M3.2: 拒绝已软删的用户 (即使 cookie 仍有效)
    if user.get("deleted_at") is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account has been deleted.",
        )
    return user


def get_current_user(request: Request) -> dict[str, Any]:
    settings = get_settings()
    access_token = request.cookies.get(settings.access_cookie_name)
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    return _get_authenticated_user(access_token, refresh_token)


def get_admin_user(request: Request) -> dict[str, Any]:
    user = get_current_user(request)
    from review_analyzer.database import get_connection

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT is_admin FROM users WHERE id = %s", (int(user["id"]),))
            row = cur.fetchone()
    finally:
        conn.close()

    if not (row and row[0]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user
