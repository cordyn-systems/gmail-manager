from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None


ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AppConfig:
    google_credentials_file: Path
    google_token_file: Path
    google_sheet_id: str
    processed_log_file: Path
    output_csv_file: Path
    ollama_host: str
    ollama_model: str


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT_DIR / path


def load_config() -> AppConfig:
    if load_dotenv:
        load_dotenv(ROOT_DIR / ".env")
    return AppConfig(
        google_credentials_file=_resolve_path(os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")),
        google_token_file=_resolve_path(os.getenv("GOOGLE_TOKEN_FILE", "token.json")),
        google_sheet_id=os.getenv("GOOGLE_SHEET_ID", ""),
        processed_log_file=_resolve_path(os.getenv("PROCESSED_LOG_FILE", "processed_emails.csv")),
        output_csv_file=_resolve_path(os.getenv("OUTPUT_CSV_FILE", "output_action_list.csv")),
        ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "gemma4:e4b"),
    )
