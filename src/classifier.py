from __future__ import annotations

import re

from models import ClassificationResult, EmailMessage


CATEGORY_KEYWORDS = {
    "Complaint / Issue": [
        "complaint",
        "issue",
        "problem",
        "not working",
        "delay",
        "unhappy",
        "refund",
        "no response",
    ],
    "Payment Follow-up": [
        "payment",
        "paid",
        "pending",
        "invoice",
        "fee",
        "amount",
        "bill",
        "due",
        "receipt",
    ],
    "Appointment Request": [
        "appointment",
        "book",
        "booking",
        "slot",
        "schedule",
        "reschedule",
        "visit",
        "consultation",
        "available",
    ],
    "New Enquiry": [
        "enquiry",
        "inquiry",
        "interested",
        "details",
        "price",
        "fee",
        "quote",
        "information",
        "service",
    ],
}

NEEDS_REPLY_KEYWORDS = [
    "please reply",
    "call me",
    "waiting",
    "follow up",
    "response",
    "urgent",
]

HIGH_PRIORITY_KEYWORDS = [
    "urgent",
    "complaint",
    "payment pending",
    "appointment today",
    "reschedule",
    "no response",
]

MEDIUM_PRIORITY_KEYWORDS = [
    "enquiry",
    "inquiry",
    "appointment",
    "quote",
    "fee",
    "consultation",
]

IGNORE_SENDERS = [
    "newsletter",
    "promotion",
    "no-reply",
    "noreply",
    "donotreply",
    "do-not-reply",
    "notification",
    "notifications",
    "mailer-daemon",
    "postmaster",
    "alerts",
    "updates",
]

IGNORE_TEXT_KEYWORDS = [
    "unsubscribe",
    "manage your preferences",
    "newsletter",
    "weekly digest",
    "daily digest",
    "promotional",
    "promotion",
    "verification code",
    "security alert",
    "password reset",
    "one-time password",
    "otp",
    "automatic reply",
    "out of office",
    "delivery status notification",
]

PENDING_ACTIONS = {
    "Appointment Request": "Confirm availability and schedule the appointment.",
    "Payment Follow-up": "Review payment status and reply to the customer.",
    "Complaint / Issue": "Investigate the issue and respond urgently.",
    "New Enquiry": "Reply with details, pricing, or next steps.",
    "Needs Reply": "Review the message and respond.",
    "Other": "Review if any action is needed.",
}


def classify_email(email: EmailMessage) -> ClassificationResult:
    if should_ignore_email(email):
        return ClassificationResult(
            category="Other",
            summary=_make_summary(email),
            pending_action=PENDING_ACTIONS["Other"],
            priority="Low",
        )

    text = _combined_text(email)
    category = _detect_category(text, email.is_unread)
    priority = _detect_priority(text, category)
    summary = _make_summary(email)
    return ClassificationResult(
        category=category,
        summary=summary,
        pending_action=PENDING_ACTIONS[category],
        priority=priority,
    )


def should_ignore_email(email: EmailMessage) -> bool:
    sender = f"{email.sender_name} {email.sender_email}".lower()
    if _contains_any(sender, IGNORE_SENDERS):
        return True

    text = _combined_text(email)
    return _contains_any(text, IGNORE_TEXT_KEYWORDS)


def _combined_text(email: EmailMessage) -> str:
    return " ".join([email.subject, email.snippet, email.body_preview]).lower()


def _detect_category(text: str, is_unread: bool) -> str:
    for category, keywords in CATEGORY_KEYWORDS.items():
        if _contains_any(text, keywords):
            return category
    if is_unread or _contains_any(text, NEEDS_REPLY_KEYWORDS):
        return "Needs Reply"
    return "Other"


def _detect_priority(text: str, category: str) -> str:
    if "appointment" in text and "today" in text:
        return "High"
    if _contains_any(text, HIGH_PRIORITY_KEYWORDS):
        return "High"
    if category in {"Complaint / Issue", "Payment Follow-up"}:
        return "High" if "pending" in text else "Medium"
    if category in {"Appointment Request", "New Enquiry"} or _contains_any(text, MEDIUM_PRIORITY_KEYWORDS):
        return "Medium"
    return "Low"


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _make_summary(email: EmailMessage) -> str:
    preview = email.snippet or email.body_preview or email.subject
    preview = re.sub(r"\s+", " ", preview).strip()
    if len(preview) <= 140:
        return preview
    return preview[:137].rstrip() + "..."
