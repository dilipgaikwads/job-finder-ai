"""Notification delivery.

Adapter pattern: pluggable channels. Default is `LogNotifier` (writes to
structured log — safe for dev). `SMTPNotifier` is provided for real email.

Notification content is deliberately terse: title, employer, URL, verification
status, top match dimensions. No secrets, no PII beyond what the user provided.
"""
from __future__ import annotations

import logging
import os
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Protocol

from app.models.job import Job
from app.models.match import MatchAnalysis
from app.models.verification import VerificationReport


log = logging.getLogger(__name__)


@dataclass
class NotificationPayload:
    user_email: str
    subject: str
    body_text: str
    job_id: str
    created_at: datetime


class Notifier(Protocol):
    def send(self, payload: NotificationPayload) -> bool: ...


class LogNotifier:
    """Writes the notification to logs. Default and safe for local/dev."""

    def __init__(self) -> None:
        self.sent: list[NotificationPayload] = []  # inspectable for tests

    def send(self, payload: NotificationPayload) -> bool:
        self.sent.append(payload)
        log.info(
            "notification.log_only",
            extra={
                "user_email": payload.user_email,
                "job_id": payload.job_id,
                "subject": payload.subject,
            },
        )
        return True


class SMTPNotifier:
    """Real email via SMTP. Reads credentials from env at construction.

    Env vars:
      SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD,
      SMTP_FROM, SMTP_STARTTLS (default "true")
    """

    def __init__(self) -> None:
        self.host = os.environ["SMTP_HOST"]
        self.port = int(os.environ.get("SMTP_PORT", "587"))
        self.user = os.environ["SMTP_USER"]
        self.password = os.environ["SMTP_PASSWORD"]
        self.from_addr = os.environ.get("SMTP_FROM", self.user)
        self.starttls = os.environ.get("SMTP_STARTTLS", "true").lower() == "true"

    def send(self, payload: NotificationPayload) -> bool:
        msg = EmailMessage()
        msg["Subject"] = payload.subject
        msg["From"] = self.from_addr
        msg["To"] = payload.user_email
        msg.set_content(payload.body_text)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=15) as s:
                if self.starttls:
                    s.starttls()
                s.login(self.user, self.password)
                s.send_message(msg)
            return True
        except Exception:  # noqa: BLE001
            log.exception("smtp_send_failed", extra={"user_email": payload.user_email})
            return False


def build_payload(
    user_email: str, job: Job, verification: VerificationReport, match: MatchAnalysis
) -> NotificationPayload:
    top_dims = sorted(match.dimensions, key=lambda d: d.score * d.weight, reverse=True)[:3]
    lines = [
        f"New match: {job.title} at {job.employer}",
        f"Location: {job.location or 'unspecified'} — {job.remote_status.value}",
        f"Apply: {job.application_url}",
        "",
        f"Verification: {verification.composite_status.value.upper()} — {verification.summary}",
    ]
    if verification.risk_flags:
        lines.append(f"Risk flags: {', '.join(verification.risk_flags)}")
    lines += [
        "",
        "Why we matched this to you:",
        *[f"  - {d.name}: {round(d.score, 2)} — {d.explanation}" for d in top_dims],
        "",
        "You will not be subscribed to any other list. Reply STOP to disable future alerts for this profile.",
    ]
    return NotificationPayload(
        user_email=user_email,
        subject=f"[Job Finder AI] {job.title} — {job.employer} ({verification.composite_status.value})",
        body_text="\n".join(lines),
        job_id=job.id,
        created_at=datetime.now(timezone.utc),
    )
