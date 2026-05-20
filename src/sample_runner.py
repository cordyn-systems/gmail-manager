from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from appointment_llm import AppointmentAnalyzer
from classifier import should_ignore_email
from models import ActionItem, ClassificationResult, EmailMessage


ACTION_HEADERS = [
    "Date",
    "Customer Name",
    "Customer Email",
    "Category",
    "Subject",
    "Summary",
    "Pending Action",
    "Priority",
    "Status",
    "Gmail Message ID",
    "Added On",
]


def load_sample_emails(sample_csv: Path) -> list[EmailMessage]:
    with sample_csv.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [
            EmailMessage(
                message_id=row["message_id"],
                received_at=row["received_at"],
                sender_name=row["sender_name"],
                sender_email=row["sender_email"],
                subject=row["subject"],
                snippet=row["snippet"],
                body_preview=row.get("body_preview", ""),
                is_unread=row.get("is_unread", "").strip().lower() in {"true", "1", "yes"},
            )
            for row in reader
        ]


def run_sample(
    sample_csv: Path,
    output_csv: Path | None = None,
    analyzer: AppointmentAnalyzer | None = None,
) -> list[ActionItem]:
    if analyzer is None:
        raise ValueError("Sample mode requires an appointment analyzer.")

    emails = load_sample_emails(sample_csv)
    now = datetime.now().isoformat(timespec="seconds")
    action_items = []
    ignored_count = 0
    for email in emails:
        if should_ignore_email(email):
            ignored_count += 1
            continue

        decision = analyzer.analyze(email)
        if not decision.appointment_related:
            ignored_count += 1
            continue
        action_items.append(_to_action_item(email, now, decision.to_classification()))
    _print_action_items(action_items)
    if ignored_count:
        print(f"\nIgnored {ignored_count} non-appointment sample messages.")
    if output_csv:
        write_action_items_csv(action_items, output_csv)
        print(f"\nWrote sample output to: {output_csv}")
    return action_items


def write_action_items_csv(action_items: list[ActionItem], output_csv: Path) -> None:
    with output_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(ACTION_HEADERS)
        for item in action_items:
            writer.writerow(item.to_sheet_row())


def _to_action_item(
    email: EmailMessage,
    added_on: str,
    classification: ClassificationResult,
) -> ActionItem:
    return ActionItem(
        date=email.received_at,
        customer_name=email.sender_name,
        customer_email=email.sender_email,
        category=classification.category,
        subject=email.subject,
        summary=classification.summary,
        pending_action=classification.pending_action,
        priority=classification.priority,
        status="Open",
        gmail_message_id=email.message_id,
        added_on=added_on,
    )


def _print_action_items(action_items: list[ActionItem]) -> None:
    for item in action_items:
        print(
            f"[{item.priority}] {item.category} | {item.customer_name} "
            f"<{item.customer_email}> | {item.subject}"
        )
        print(f"  Summary: {item.summary}")
        print(f"  Action: {item.pending_action}")
