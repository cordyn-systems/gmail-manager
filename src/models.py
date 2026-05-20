from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmailMessage:
    message_id: str
    received_at: str
    sender_name: str
    sender_email: str
    subject: str
    snippet: str
    body_preview: str = ""
    is_unread: bool = False


@dataclass(frozen=True)
class ClassificationResult:
    category: str
    summary: str
    pending_action: str
    priority: str


@dataclass(frozen=True)
class ActionItem:
    date: str
    customer_name: str
    customer_email: str
    category: str
    subject: str
    summary: str
    pending_action: str
    priority: str
    status: str
    gmail_message_id: str
    added_on: str

    def to_sheet_row(self) -> list[str]:
        return [
            self.date,
            self.customer_name,
            self.customer_email,
            self.category,
            self.subject,
            self.summary,
            self.pending_action,
            self.priority,
            self.status,
            self.gmail_message_id,
            self.added_on,
        ]


@dataclass(frozen=True)
class ProcessedEmail:
    gmail_message_id: str
    date: str
    from_value: str
    subject: str
    snippet: str
    category: str
    added_on: str

    def to_sheet_row(self) -> list[str]:
        return [
            self.gmail_message_id,
            self.date,
            self.from_value,
            self.subject,
            self.snippet,
            self.category,
            self.added_on,
        ]

