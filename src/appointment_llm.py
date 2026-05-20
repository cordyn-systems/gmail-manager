from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from models import ClassificationResult, EmailMessage


@dataclass(frozen=True)
class AppointmentDecision:
    appointment_related: bool
    category: str
    summary: str
    pending_action: str
    priority: str
    reason: str

    def to_classification(self) -> ClassificationResult:
        return ClassificationResult(
            category=self.category,
            summary=self.summary,
            pending_action=self.pending_action,
            priority=self.priority,
        )


class AppointmentAnalyzer(Protocol):
    def analyze(self, email: EmailMessage) -> AppointmentDecision:
        ...


class OllamaAppointmentAnalyzer:
    def __init__(self, host: str, model: str, timeout_seconds: int = 60):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def analyze(self, email: EmailMessage) -> AppointmentDecision:
        prompt = _build_prompt(email)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You classify business emails for appointment relevance only. "
                        "Return only valid JSON. Do not include markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }

        request = Request(
            f"{self.host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except URLError as exc:
            raise RuntimeError(f"Could not reach Ollama at {self.host}: {exc}") from exc

        content = raw.get("message", {}).get("content", "")
        return _parse_decision(content)


def _build_prompt(email: EmailMessage) -> str:
    return f"""
Decide whether this email is a real appointment-related message that a human should review.

Only mark appointment_related=true if the email is about:
- booking an appointment
- scheduling or rescheduling
- asking for available slots/timing
- confirming, cancelling, or changing a visit/consultation/meeting
- a customer asking to call/meet at a specific time

Mark appointment_related=false for:
- newsletters, promotions, alerts, OTPs, receipts, invoices, reports, notifications
- general updates
- payment-only emails
- complaints without scheduling intent
- automatic emails
- anything unclear

Return JSON with exactly these keys:
{{
  "appointment_related": true or false,
  "category": "Appointment Request" or "Not Appointment",
  "summary": "short summary, max 140 characters",
  "pending_action": "specific next action if appointment-related, otherwise empty string",
  "priority": "High" or "Medium" or "Low",
  "reason": "short reason for the decision"
}}

Priority rules:
- High: appointment is today, urgent, reschedule/cancel, missed/no response
- Medium: normal appointment booking, consultation, availability request
- Low: tentative or unclear appointment mention

Email:
From: {email.sender_name} <{email.sender_email}>
Received: {email.received_at}
Subject: {email.subject}
Snippet: {email.snippet}
Preview: {email.body_preview[:500]}
Unread: {email.is_unread}
""".strip()


def _parse_decision(content: str) -> AppointmentDecision:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Ollama returned invalid JSON: {content[:200]}") from exc

    appointment_related = bool(data.get("appointment_related"))
    category = "Appointment Request" if appointment_related else "Not Appointment"
    summary = str(data.get("summary") or "").strip()
    pending_action = str(data.get("pending_action") or "").strip()
    priority = str(data.get("priority") or "Low").strip().title()
    reason = str(data.get("reason") or "").strip()

    if priority not in {"High", "Medium", "Low"}:
        priority = "Low"
    if appointment_related and not pending_action:
        pending_action = "Review and respond to the appointment request."
    if not appointment_related:
        pending_action = ""
        priority = "Low"
    if not summary:
        summary = reason or "No appointment action needed."

    return AppointmentDecision(
        appointment_related=appointment_related,
        category=category,
        summary=summary[:140],
        pending_action=pending_action[:180],
        priority=priority,
        reason=reason[:180],
    )

