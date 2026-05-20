from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from models import ActionItem, ProcessedEmail


SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"

ACTION_SHEET = "Today Action List"
PROCESSED_SHEET = "Processed Emails"
SETTINGS_SHEET = "Settings"

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

PROCESSED_HEADERS = [
    "Gmail Message ID",
    "Date",
    "From",
    "Subject",
    "Snippet",
    "Category",
    "Added On",
]

SETTINGS_ROWS = [
    ["Setting", "Value"],
    ["Scan Days", "1"],
    ["Business Type", "Clinic / Coaching / Service"],
    [
        "High Priority Keywords",
        "urgent, appointment, payment, booking, complaint, reschedule, not replied",
    ],
    ["Ignore Senders", "newsletter, promotion, no-reply"],
]


class SheetsClient:
    def __init__(self, credentials_file: Path, token_file: Path, spreadsheet_id: str):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.spreadsheet_id = spreadsheet_id
        self.service = build("sheets", "v4", credentials=self._load_credentials())

    def setup_workbook(self) -> None:
        existing_titles = self._get_sheet_titles()
        requests = []
        for title in [ACTION_SHEET, PROCESSED_SHEET, SETTINGS_SHEET]:
            if title not in existing_titles:
                requests.append({"addSheet": {"properties": {"title": title}}})
        if requests:
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": requests},
            ).execute()

        self._ensure_headers(ACTION_SHEET, ACTION_HEADERS)
        self._ensure_headers(PROCESSED_SHEET, PROCESSED_HEADERS)
        self._ensure_settings()

    def get_processed_message_ids(self) -> set[str]:
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{PROCESSED_SHEET}'!A2:A",
        ).execute()
        return {row[0] for row in result.get("values", []) if row}

    def append_action_items(self, action_items: list[ActionItem]) -> None:
        if not action_items:
            return
        self._append_rows(ACTION_SHEET, [item.to_sheet_row() for item in action_items])

    def append_processed_emails(self, processed_emails: list[ProcessedEmail]) -> None:
        if not processed_emails:
            return
        self._append_rows(PROCESSED_SHEET, [email.to_sheet_row() for email in processed_emails])

    def clear_action_list_rows(self) -> None:
        self.service.spreadsheets().values().clear(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{ACTION_SHEET}'!A2:K",
            body={},
        ).execute()

    def _load_credentials(self) -> Credentials:
        credentials = None
        if self.token_file.exists():
            credentials = Credentials.from_authorized_user_file(
                str(self.token_file),
                ["https://www.googleapis.com/auth/gmail.readonly", SHEETS_SCOPE],
            )

        if credentials and credentials.valid:
            return credentials

        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not self.credentials_file.exists():
                raise FileNotFoundError(
                    f"Missing Google credentials file: {self.credentials_file}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file),
                ["https://www.googleapis.com/auth/gmail.readonly", SHEETS_SCOPE],
            )
            credentials = flow.run_local_server(port=0)

        self.token_file.write_text(credentials.to_json(), encoding="utf-8")
        return credentials

    def _get_sheet_titles(self) -> set[str]:
        metadata = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        return {sheet["properties"]["title"] for sheet in metadata.get("sheets", [])}

    def _ensure_headers(self, sheet_name: str, headers: list[str]) -> None:
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{sheet_name}'!A1:Z1",
        ).execute()
        values = result.get("values", [])
        if not values or values[0] != headers:
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{sheet_name}'!A1",
                valueInputOption="RAW",
                body={"values": [headers]},
            ).execute()

    def _ensure_settings(self) -> None:
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{SETTINGS_SHEET}'!A1:B5",
        ).execute()
        if not result.get("values"):
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{SETTINGS_SHEET}'!A1",
                valueInputOption="RAW",
                body={"values": SETTINGS_ROWS},
            ).execute()

    def _append_rows(self, sheet_name: str, rows: list[list[str]]) -> None:
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{sheet_name}'!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ).execute()
