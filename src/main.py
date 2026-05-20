from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from appointment_llm import AppointmentAnalyzer, OllamaAppointmentAnalyzer
from classifier import should_ignore_email
from config import ROOT_DIR, load_config
from dedupe import ProcessedLog
from models import ActionItem, EmailMessage, ProcessedEmail
from sample_runner import run_sample


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert business Gmail messages into a daily Google Sheet action list."
    )
    parser.add_argument("--mode", choices=["sample", "gmail"], required=True)
    parser.add_argument("--days", type=int, default=1, help="Number of recent days to scan.")
    parser.add_argument("--sheet-id", default="", help="Google Sheet ID for Gmail mode.")
    parser.add_argument(
        "--sample-file",
        default=str(ROOT_DIR / "data" / "sample_emails.csv"),
        help="Sample CSV file path.",
    )
    parser.add_argument(
        "--output-csv",
        nargs="?",
        const="",
        default=None,
        help="Write sample output to CSV. Uses OUTPUT_CSV_FILE when no path is provided.",
    )
    parser.add_argument("--max-results", type=int, default=100, help="Maximum Gmail messages to read.")
    parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Re-evaluate recent emails even if their Gmail IDs were already processed.",
    )
    parser.add_argument(
        "--reset-action-list",
        action="store_true",
        help="Clear existing Today Action List rows before writing new appointment rows.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()

    if args.mode == "sample":
        output_csv = None
        if args.output_csv is not None:
            output_csv = Path(args.output_csv) if args.output_csv else config.output_csv_file
        analyzer = OllamaAppointmentAnalyzer(config.ollama_host, config.ollama_model)
        run_sample(Path(args.sample_file), output_csv, analyzer)
        return

    sheet_id = args.sheet_id or config.google_sheet_id
    if not sheet_id:
        raise SystemExit("Missing Google Sheet ID. Pass --sheet-id or set GOOGLE_SHEET_ID in .env.")

    analyzer = OllamaAppointmentAnalyzer(config.ollama_host, config.ollama_model)
    run_gmail_mode(
        config,
        sheet_id,
        days=args.days,
        max_results=args.max_results,
        analyzer=analyzer,
        reprocess=args.reprocess,
        reset_action_list=args.reset_action_list,
    )


def run_gmail_mode(
    config,
    sheet_id: str,
    days: int,
    max_results: int,
    analyzer: AppointmentAnalyzer,
    reprocess: bool = False,
    reset_action_list: bool = False,
) -> None:
    from gmail_client import GmailClient
    from sheets_client import SheetsClient

    gmail = GmailClient(config.google_credentials_file, config.google_token_file)
    sheets = SheetsClient(config.google_credentials_file, config.google_token_file, sheet_id)
    sheets.setup_workbook()
    if reset_action_list:
        sheets.clear_action_list_rows()

    processed_log = ProcessedLog(config.processed_log_file)
    sheet_processed_ids = sheets.get_processed_message_ids()
    processed_ids = processed_log.load_ids() | sheet_processed_ids

    emails = gmail.fetch_recent_emails(days=days, max_results=max_results)
    new_emails = emails if reprocess else [email for email in emails if email.message_id not in processed_ids]

    action_items, processed_emails, not_appointment_count = build_rows(new_emails, analyzer)
    processed_emails_to_append = [
        email for email in processed_emails if email.gmail_message_id not in processed_ids
    ]
    sheets.append_action_items(action_items)
    sheets.append_processed_emails(processed_emails_to_append)
    processed_log.add_many([email.gmail_message_id for email in processed_emails_to_append])

    print(f"Read {len(emails)} Gmail messages.")
    print(f"Added {len(action_items)} appointment action rows.")
    print(f"Ignored {not_appointment_count} non-appointment messages.")
    print(f"Skipped {0 if reprocess else len(emails) - len(new_emails)} duplicate messages.")
    if reprocess:
        print("Reprocessed existing message IDs without duplicating processed-log rows.")


def build_rows(
    emails: list[EmailMessage],
    analyzer: AppointmentAnalyzer,
) -> tuple[list[ActionItem], list[ProcessedEmail], int]:
    added_on = datetime.now().isoformat(timespec="seconds")
    action_items = []
    processed_emails = []
    not_appointment_count = 0

    for email in emails:
        if should_ignore_email(email):
            not_appointment_count += 1
            processed_emails.append(
                ProcessedEmail(
                    gmail_message_id=email.message_id,
                    date=email.received_at,
                    from_value=f"{email.sender_name} <{email.sender_email}>",
                    subject=email.subject,
                    snippet=email.snippet[:300],
                    category="Ignored / Automated",
                    added_on=added_on,
                )
            )
            continue

        decision = analyzer.analyze(email)
        if not decision.appointment_related:
            not_appointment_count += 1
            processed_emails.append(
                ProcessedEmail(
                    gmail_message_id=email.message_id,
                    date=email.received_at,
                    from_value=f"{email.sender_name} <{email.sender_email}>",
                    subject=email.subject,
                    snippet=email.snippet[:300],
                    category="Not Appointment",
                    added_on=added_on,
                )
            )
            continue

        classification = decision.to_classification()
        action_items.append(
            ActionItem(
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
        )
        processed_emails.append(
            ProcessedEmail(
                gmail_message_id=email.message_id,
                date=email.received_at,
                from_value=f"{email.sender_name} <{email.sender_email}>",
                subject=email.subject,
                snippet=email.snippet[:300],
                category=classification.category,
                added_on=added_on,
            )
        )

    return action_items, processed_emails, not_appointment_count


if __name__ == "__main__":
    main()
