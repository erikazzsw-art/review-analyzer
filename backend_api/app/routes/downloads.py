from __future__ import annotations

from typing import Any

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend_api.app.deps import get_current_user
from review_analyzer.database import get_connection

router = APIRouter(prefix="/downloads", tags=["downloads"])


class DownloadRecordCreate(BaseModel):
    name: str
    source: str
    status: str = "completed"
    file_url: str | None = None


class DownloadRecordOut(BaseModel):
    id: int
    name: str
    source: str
    status: str
    file_url: str | None
    created_at: str


@router.get("", response_model=list[DownloadRecordOut])
def list_downloads(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    user_id = int(current_user["id"])
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, name, source, status, file_url,
                       created_at::text AS created_at
                FROM download_records
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 200
                """,
                (user_id,),
            )
            return cur.fetchall()
    finally:
        conn.close()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DownloadRecordOut)
def create_download(
    body: DownloadRecordCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = int(current_user["id"])
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO download_records (user_id, name, source, status, file_url)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, name, source, status, file_url, created_at::text AS created_at
                """,
                (user_id, body.name, body.source, body.status, body.file_url),
            )
            row = cur.fetchone()
            conn.commit()
            if not row:
                raise HTTPException(status_code=500, detail="Insert failed")
            return row
    finally:
        conn.close()
