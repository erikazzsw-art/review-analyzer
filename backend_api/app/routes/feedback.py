from __future__ import annotations

import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from threading import Thread

from fastapi import APIRouter, Depends, status

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.feedback import FeedbackCreatePayload, FeedbackResponse
from review_analyzer.feedback_store import create_feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])
logger = logging.getLogger(__name__)


def _send_notification_email(feedback_id: int, data: dict) -> None:
    """Send email notification in background thread. Failures are silent."""
    to_email = os.getenv("FEEDBACK_NOTIFY_EMAIL")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")

    if not to_email or not smtp_user:
        logger.info("Feedback email notification skipped: FEEDBACK_NOTIFY_EMAIL or SMTP_USER not set")
        return

    mood_labels = {"frustrated": "Bug", "idea": "Feature Request", "love": "Positive"}
    mood_label = mood_labels.get(data["mood"], data["mood"])

    body = (
        f"New feedback #{feedback_id}\n\n"
        f"Type: {data['feedback_type']}\n"
        f"Mood: {mood_label}\n"
        f"Page: {data['page_path']}\n"
        f"Message: {data.get('message') or '(no message)'}\n"
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"[ClueAI Feedback] {mood_label} - {data['page_path']}"
    msg["From"] = smtp_user
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info("Feedback notification email sent for #%d", feedback_id)
    except Exception:
        logger.warning("Failed to send feedback notification email for #%d", feedback_id, exc_info=True)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=FeedbackResponse)
def submit_feedback(
    payload: FeedbackCreatePayload,
    current_user: dict = Depends(get_current_user),
) -> FeedbackResponse:
    user_id = int(current_user["id"])
    data = payload.model_dump()
    feedback_id = create_feedback(user_id, data)

    Thread(
        target=_send_notification_email,
        args=(feedback_id, data),
        daemon=True,
    ).start()

    return FeedbackResponse(
        id=feedback_id,
        feedback_type=data["feedback_type"],
        mood=data["mood"],
        message=data.get("message"),
        page_path=data["page_path"],
        status="new",
        created_at=datetime.now(timezone.utc),
    )
