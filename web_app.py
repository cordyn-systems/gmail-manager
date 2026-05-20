from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import re
import secrets
import sys
from urllib.error import URLError
from urllib.request import urlopen

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from appointment_llm import OllamaAppointmentAnalyzer
from config import load_config
from dedupe import ProcessedLog
from gmail_client import GmailClient
from main import build_rows
from models import ActionItem, ProcessedEmail
from sample_runner import load_sample_emails
from sheets_client import SheetsClient


WEB_SETTINGS_FILE = ROOT_DIR / "web_settings.json"
PENDING_RESULTS_FILE = ROOT_DIR / "pending_results.json"

app = Flask(__name__)


def _read_raw_settings() -> dict:
    if not WEB_SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(WEB_SETTINGS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_raw_settings(settings: dict) -> None:
    WEB_SETTINGS_FILE.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def ensure_local_secret_key() -> str:
    settings = _read_raw_settings()
    if not settings.get("local_secret_key"):
        settings["local_secret_key"] = secrets.token_urlsafe(32)
        _write_raw_settings(settings)
    return settings["local_secret_key"]


app.secret_key = ensure_local_secret_key()


def load_web_settings() -> dict:
    defaults = {
        "google_sheet_id": load_config().google_sheet_id,
        "scan_days": 1,
        "max_results": 100,
        "ollama_host": load_config().ollama_host,
        "ollama_model": load_config().ollama_model,
    }
    saved = _read_raw_settings()
    return defaults | saved


def save_web_settings(settings: dict) -> None:
    current = _read_raw_settings()
    current.update(settings)
    _write_raw_settings(current)


def runtime_config():
    settings = load_web_settings()
    config = load_config()
    return replace(
        config,
        google_sheet_id=settings.get("google_sheet_id", ""),
        ollama_host=settings.get("ollama_host", config.ollama_host),
        ollama_model=settings.get("ollama_model", config.ollama_model),
    )


def extract_sheet_id(value: str) -> str:
    value = value.strip()
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", value)
    if match:
        return match.group(1)
    return value


def ollama_status(host: str) -> tuple[bool, str]:
    try:
        with urlopen(f"{host.rstrip('/')}/api/tags", timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return False, f"Cannot reach Ollama: {exc}"
    models = [model.get("name", "") for model in data.get("models", [])]
    return True, ", ".join(models) or "Ollama is running"


def build_status() -> dict:
    config = runtime_config()
    settings = load_web_settings()
    ollama_ok, ollama_message = ollama_status(config.ollama_host)
    pending = load_pending_results()
    return {
        "credentials": config.google_credentials_file.exists(),
        "token": config.google_token_file.exists(),
        "sheet": bool(settings.get("google_sheet_id")),
        "ollama": ollama_ok,
        "ollama_message": ollama_message,
        "pending": pending,
    }


def save_pending_results(
    action_items: list[ActionItem],
    processed_emails: list[ProcessedEmail],
    stats: dict,
) -> None:
    payload = {
        "action_items": [asdict(item) for item in action_items],
        "processed_emails": [asdict(item) for item in processed_emails],
        "stats": stats,
    }
    PENDING_RESULTS_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_pending_results() -> dict | None:
    if not PENDING_RESULTS_FILE.exists():
        return None
    try:
        return json.loads(PENDING_RESULTS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def clear_pending_results() -> None:
    if PENDING_RESULTS_FILE.exists():
        PENDING_RESULTS_FILE.unlink()


def dict_to_action_item(data: dict) -> ActionItem:
    return ActionItem(**data)


def dict_to_processed_email(data: dict) -> ProcessedEmail:
    return ProcessedEmail(**data)


def has_pin() -> bool:
    return bool(load_web_settings().get("pin_hash"))


@app.before_request
def require_local_login():
    if request.endpoint in {"static", "setup_pin", "create_pin", "login", "login_post"}:
        return None
    if not has_pin():
        return redirect(url_for("setup_pin"))
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    return None


@app.get("/setup-pin")
def setup_pin():
    if has_pin():
        return redirect(url_for("login"))
    return render_template("setup_pin.html")


@app.post("/setup-pin")
def create_pin():
    if has_pin():
        return redirect(url_for("login"))
    pin = request.form.get("pin", "")
    confirm_pin = request.form.get("confirm_pin", "")
    if len(pin) < 6:
        flash("Use a PIN or password with at least 6 characters.", "error")
        return redirect(url_for("setup_pin"))
    if pin != confirm_pin:
        flash("PIN entries did not match.", "error")
        return redirect(url_for("setup_pin"))
    settings = load_web_settings()
    settings["pin_hash"] = generate_password_hash(pin)
    save_web_settings(settings)
    session["authenticated"] = True
    flash("Local PIN created.", "success")
    return redirect(url_for("dashboard"))


@app.get("/login")
def login():
    if not has_pin():
        return redirect(url_for("setup_pin"))
    return render_template("login.html")


@app.post("/login")
def login_post():
    pin_hash = load_web_settings().get("pin_hash", "")
    if check_password_hash(pin_hash, request.form.get("pin", "")):
        session["authenticated"] = True
        return redirect(url_for("dashboard"))
    flash("Incorrect PIN.", "error")
    return redirect(url_for("login"))


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
def dashboard():
    settings = load_web_settings()
    return render_template("dashboard.html", settings=settings, status=build_status())


@app.post("/settings")
def update_settings():
    settings = load_web_settings()
    settings["google_sheet_id"] = extract_sheet_id(request.form.get("google_sheet_id", ""))
    settings["scan_days"] = int(request.form.get("scan_days") or 1)
    settings["max_results"] = int(request.form.get("max_results") or 100)
    settings["ollama_host"] = request.form.get("ollama_host", "http://127.0.0.1:11434").strip()
    settings["ollama_model"] = request.form.get("ollama_model", "gemma4:e4b").strip()
    save_web_settings(settings)

    credentials = request.files.get("credentials_file")
    if credentials and credentials.filename:
        if Path(credentials.filename).suffix.lower() != ".json":
            flash("Upload the downloaded Google OAuth JSON file.", "error")
            return redirect(url_for("dashboard"))
        credentials.save(ROOT_DIR / "credentials.json")

    flash("Settings saved.", "success")
    return redirect(url_for("dashboard"))


@app.post("/connect")
def connect_gmail():
    config = runtime_config()
    if not config.google_credentials_file.exists():
        flash("Upload credentials.json first.", "error")
        return redirect(url_for("dashboard"))
    try:
        GmailClient(config.google_credentials_file, config.google_token_file)
    except Exception as exc:
        flash(f"Could not connect Gmail: {exc}", "error")
        return redirect(url_for("dashboard"))
    flash("Gmail connected successfully.", "success")
    return redirect(url_for("dashboard"))


@app.post("/scan")
def scan_gmail():
    config = runtime_config()
    settings = load_web_settings()
    if not settings.get("google_sheet_id"):
        flash("Add a Google Sheet link or ID first.", "error")
        return redirect(url_for("dashboard"))

    days = int(request.form.get("scan_days") or settings.get("scan_days", 1))
    max_results = int(request.form.get("max_results") or settings.get("max_results", 100))
    reprocess = request.form.get("reprocess") == "on"
    reset_action_list = request.form.get("reset_action_list") == "on"

    try:
        gmail = GmailClient(config.google_credentials_file, config.google_token_file)
        sheets = SheetsClient(config.google_credentials_file, config.google_token_file, settings["google_sheet_id"])
        sheets.setup_workbook()
        sheet_processed_ids = sheets.get_processed_message_ids()
        processed_log = ProcessedLog(config.processed_log_file)
        processed_ids = processed_log.load_ids() | sheet_processed_ids
        emails = gmail.fetch_recent_emails(days=days, max_results=max_results)
        candidates = emails if reprocess else [email for email in emails if email.message_id not in processed_ids]
        analyzer = OllamaAppointmentAnalyzer(config.ollama_host, config.ollama_model)
        action_items, processed_emails, ignored_count = build_rows(candidates, analyzer)
        processed_to_append = [
            item for item in processed_emails if item.gmail_message_id not in processed_ids
        ]
    except Exception as exc:
        flash(f"Scan failed: {exc}", "error")
        return redirect(url_for("dashboard"))

    save_pending_results(
        action_items,
        processed_to_append,
        {
            "read": len(emails),
            "candidates": len(candidates),
            "appointments": len(action_items),
            "ignored": ignored_count,
            "duplicates": 0 if reprocess else len(emails) - len(candidates),
            "reprocess": reprocess,
            "reset_action_list": reset_action_list,
        },
    )
    flash("Scan complete. Review the appointment rows before writing to Google Sheets.", "success")
    return redirect(url_for("dashboard"))


@app.post("/write")
def write_results():
    pending = load_pending_results()
    if not pending:
        flash("No pending scan results to write.", "error")
        return redirect(url_for("dashboard"))

    config = runtime_config()
    settings = load_web_settings()
    action_items = [dict_to_action_item(item) for item in pending["action_items"]]
    processed_emails = [dict_to_processed_email(item) for item in pending["processed_emails"]]
    stats = pending.get("stats", {})

    try:
        sheets = SheetsClient(config.google_credentials_file, config.google_token_file, settings["google_sheet_id"])
        sheets.setup_workbook()
        if stats.get("reset_action_list"):
            sheets.clear_action_list_rows()
        sheets.append_action_items(action_items)
        sheets.append_processed_emails(processed_emails)
        ProcessedLog(config.processed_log_file).add_many(
            [item.gmail_message_id for item in processed_emails]
        )
    except Exception as exc:
        flash(f"Write failed: {exc}", "error")
        return redirect(url_for("dashboard"))

    clear_pending_results()
    flash(f"Wrote {len(action_items)} appointment rows to Google Sheets.", "success")
    return redirect(url_for("dashboard"))


@app.post("/sample")
def sample_scan():
    config = runtime_config()
    try:
        emails = load_sample_emails(ROOT_DIR / "data" / "sample_emails.csv")
        analyzer = OllamaAppointmentAnalyzer(config.ollama_host, config.ollama_model)
        action_items, processed_emails, ignored_count = build_rows(emails, analyzer)
    except Exception as exc:
        flash(f"Sample scan failed: {exc}", "error")
        return redirect(url_for("dashboard"))

    save_pending_results(
        action_items,
        processed_emails,
        {
            "read": len(emails),
            "candidates": len(emails),
            "appointments": len(action_items),
            "ignored": ignored_count,
            "duplicates": 0,
            "reprocess": True,
            "reset_action_list": False,
            "sample": True,
        },
    )
    flash("Sample scan complete.", "success")
    return redirect(url_for("dashboard"))


@app.post("/clear-local-data")
def clear_local_data():
    config = runtime_config()
    clear_pending_results()

    if request.form.get("clear_processed_log") == "on" and config.processed_log_file.exists():
        config.processed_log_file.unlink()
    if request.form.get("clear_token") == "on" and config.google_token_file.exists():
        config.google_token_file.unlink()
    if request.form.get("clear_credentials") == "on" and config.google_credentials_file.exists():
        config.google_credentials_file.unlink()

    flash("Selected local data cleared.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5055, debug=False)
