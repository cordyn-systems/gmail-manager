# Gmail to Action Sheet

Convert business Gmail messages into a daily Google Sheet action list.

Gmail to Action Sheet is an open-source MVP by Qorvia Systems. It reads recent business Gmail messages in read-only mode, uses local Ollama to detect appointment-related emails, and writes only appointment action items into Google Sheets.

## Use Case

This project is for small businesses, clinics, coaching centers, consultants, and service providers that receive customer messages through Gmail and need a clear daily follow-up list.

## What It Does

- Connects to Gmail with the Gmail API using read-only access.
- Reads emails from the last N days. The default is 1 day.
- Extracts message ID, received date, sender, subject, and snippet/body preview.
- Uses local Ollama to decide whether each email is appointment-related.
- Generates a short summary, pending action, and priority.
- Writes only appointment-related rows into a Google Sheet.
- Avoids duplicate processing using Gmail message IDs.
- Maintains a processed email log.
- Includes sample mode for testing without Google credentials.

## What It Does Not Do

- Does not send emails.
- Does not delete emails.
- Does not modify Gmail labels.
- Does not archive messages.
- Does not change anything inside Gmail.
- Does not act as a CRM.

## Project Structure

```text
gmail-to-action-sheet/
  README.md
  LICENSE
  .gitignore
  .env.example
  requirements.txt
  pyproject.toml
  web_app.py
  Start Gmail Action Sheet.command
  Stop Gmail Action Sheet.command
  Start Gmail Action Sheet.bat
  Stop Gmail Action Sheet.bat
  templates/
    dashboard.html
  static/
    styles.css
  src/
    appointment_llm.py
    main.py
    config.py
    gmail_client.py
    sheets_client.py
    classifier.py
    models.py
    dedupe.py
    sample_runner.py
  data/
    sample_emails.csv
  tests/
    test_classifier.py
    test_dedupe.py
```

## Setup

1. Create and activate a virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the example environment file:

```bash
cp .env.example .env
```

4. Edit `.env` if you want to set a default Google Sheet ID or custom file paths.

## Google Cloud Credential Setup

1. Open Google Cloud Console.
2. Create or select a project.
3. Enable these APIs:
   - Gmail API
   - Google Sheets API
4. Configure the OAuth consent screen.
5. Create OAuth Client credentials for a Desktop app.
6. Download the JSON credentials file.
7. Save it in the project root as `credentials.json`.
8. Keep `credentials.json` and `token.json` private. They are ignored by git.

The Gmail integration uses this read-only scope only:

```text
https://www.googleapis.com/auth/gmail.readonly
```

The Sheets integration uses:

```text
https://www.googleapis.com/auth/spreadsheets
```

Use the `--sheet-id` CLI option or `GOOGLE_SHEET_ID` environment variable to control which spreadsheet is updated.

## Environment Variables

```text
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json
GOOGLE_SHEET_ID=
PROCESSED_LOG_FILE=processed_emails.csv
OUTPUT_CSV_FILE=output_action_list.csv
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=gemma4:e4b
```

## Ollama Setup

This version uses a local Ollama model to keep only appointment-related emails.

```bash
ollama list
```

Set the model in `.env`:

```text
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=gemma4:e4b
```

## Browser App

For non-developer use, start the local browser app.

One-click install on macOS:

```text
Double-click Install Gmail Action Sheet.command
```

One-click install on Windows:

```text
Double-click Install Gmail Action Sheet.bat
```

On macOS:

```text
Double-click Start Gmail Action Sheet.command
```

On Windows:

```text
Double-click Start Gmail Action Sheet.bat
```

The app opens at:

```text
http://127.0.0.1:5055
```

The browser app lets users:

- Create a local PIN/password on first run.
- Upload the Google OAuth JSON file.
- Paste a Google Sheet link or ID.
- Check Gmail, Google Sheet, and Ollama connection status.
- Connect Gmail through the browser OAuth flow.
- Scan Gmail for genuine appointment-related messages.
- Preview appointment rows before writing to Google Sheets.
- Rebuild the action list while ignoring automated emails.
- Clear local tokens, credentials, pending previews, and processed logs when needed.

Stop the local app with:

```text
Stop Gmail Action Sheet.command
```

or:

```text
Stop Gmail Action Sheet.bat
```

## Sample Mode

Sample mode does not require Google credentials, but it does require Ollama to be running.

```bash
python src/main.py --mode sample
```

Write the classified action list to a local CSV:

```bash
python src/main.py --mode sample --output-csv output_action_list.csv
```

## Gmail Mode

Read Gmail from the last 1 day and update the configured sheet:

```bash
python src/main.py --mode gmail --days 1
```

Read Gmail from the last 7 days and pass a sheet ID explicitly:

```bash
python src/main.py --mode gmail --days 7 --sheet-id <GOOGLE_SHEET_ID>
```

Rebuild the action sheet from recent emails using the appointment-only Ollama filter:

```bash
python src/main.py --mode gmail --days 1 --reprocess --reset-action-list
```

This clears existing `Today Action List` rows, rechecks recent Gmail messages with Ollama, and writes back only appointment-related rows. It does not duplicate existing `Processed Emails` rows.

On first run, a browser window opens for Google OAuth consent. The local OAuth token is saved in `token.json`.

## Google Sheet Tab Format

The script creates or updates 3 tabs.

### Today Action List

```text
Date
Customer Name
Customer Email
Category
Subject
Summary
Pending Action
Priority
Status
Gmail Message ID
Added On
```

### Processed Emails

```text
Gmail Message ID
Date
From
Subject
Snippet
Category
Added On
```

### Settings

```text
Setting
Value
```

Default settings:

```text
Scan Days = 1
Business Type = Clinic / Coaching / Service
High Priority Keywords = urgent, appointment, payment, booking, complaint, reschedule, not replied
Ignore Senders = newsletter, promotion, no-reply
```

## Appointment Filtering

The MVP uses local Ollama for appointment-only filtering. It does not use OpenAI or any paid AI API.

Only emails that are truly appointment-related are added to `Today Action List`.

Included examples:

- booking an appointment
- scheduling or rescheduling
- asking for available slots or timing
- confirming, cancelling, or changing a visit, consultation, or meeting
- a customer asking to call or meet at a specific time

Excluded examples:

- newsletters
- promotions
- alerts
- OTPs
- receipts
- invoices
- reports
- automatic notifications
- payment-only emails
- complaints without scheduling intent

## Run Tests

```bash
pytest
```

## Roadmap

V1:

- Gmail read-only reader
- Rule-based classification
- Google Sheet update
- Duplicate prevention

V2:

- Google Calendar integration
- Better action extraction
- Configurable business-specific keywords

V3:

- Optional local LLM/AI classification
- Daily digest
- Streamlit dashboard

## Support & Customization

This repository is built as an open-source experiment for practical business process automation. For customization, pilot implementation, or business workflow adaptation, contact: qorviasystems@gmail.com
