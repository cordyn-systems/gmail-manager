from __future__ import annotations

import base64
from datetime import datetime, timedelta
from email.utils import parseaddr, parsedate_to_datetime
import re
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from models import EmailMessage


GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class GmailClient:
    def __init__(self, credentials_file: Path, token_file: Path):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = build("gmail", "v1", credentials=self._load_credentials())

    def fetch_recent_emails(self, days: int = 1, max_results: int = 100) -> list[EmailMessage]:
        after_date = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
        query = f"after:{after_date}"
        response = (
            self.service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        messages = response.get("messages", [])
        return [self._fetch_message(message["id"]) for message in messages]

    def _load_credentials(self) -> Credentials:
        credentials = None
        if self.token_file.exists():
            credentials = Credentials.from_authorized_user_file(
                str(self.token_file),
                [GMAIL_READONLY_SCOPE, "https://www.googleapis.com/auth/spreadsheets"],
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
                [GMAIL_READONLY_SCOPE, "https://www.googleapis.com/auth/spreadsheets"],
            )
            credentials = flow.run_local_server(port=0)

        self.token_file.write_text(credentials.to_json(), encoding="utf-8")
        return credentials

    def _fetch_message(self, message_id: str) -> EmailMessage:
        message = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        headers = {header["name"].lower(): header["value"] for header in message["payload"].get("headers", [])}
        sender_name, sender_email = parseaddr(headers.get("from", ""))
        received_at = self._parse_received_at(headers.get("date", ""))
        labels = set(message.get("labelIds", []))
        return EmailMessage(
            message_id=message["id"],
            received_at=received_at,
            sender_name=sender_name or sender_email,
            sender_email=sender_email,
            subject=headers.get("subject", ""),
            snippet=message.get("snippet", ""),
            body_preview=self._extract_body_preview(message.get("payload", {})),
            is_unread="UNREAD" in labels,
        )

    @staticmethod
    def _parse_received_at(value: str) -> str:
        if not value:
            return ""
        try:
            return parsedate_to_datetime(value).isoformat(timespec="seconds")
        except (TypeError, ValueError):
            return value

    def _extract_body_preview(self, payload: dict) -> str:
        text = self._find_text_part(payload)
        return " ".join(text.split())[:2000]

    def _find_text_part(self, payload: dict) -> str:
        mime_type = payload.get("mimeType", "")
        body = payload.get("body", {})
        data = body.get("data")
        if mime_type == "text/plain" and data:
            return self._decode_base64(data)
        if mime_type == "text/html" and data:
            return self._html_to_text(self._decode_base64(data))

        for part in payload.get("parts", []):
            text = self._find_text_part(part)
            if text:
                return text
        return ""

    @staticmethod
    def _decode_base64(data: str) -> str:
        padded = data + "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="replace")

    @staticmethod
    def _html_to_text(html: str) -> str:
        html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
        html = re.sub(r"(?s)<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", html).strip()
