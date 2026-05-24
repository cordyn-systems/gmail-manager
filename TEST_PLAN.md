# Gmail Manager Local Test Plan

This test plan validates the local Gmail Manager application before sharing it with a small business pilot user.

## 1. Scope

Validate that Gmail Manager can be installed and used locally by a non-developer to:

- connect Gmail with read-only OAuth
- detect genuine appointment-related emails using local Ollama
- ignore automated/no-action emails
- preview appointment actions
- write approved rows to Google Sheets
- protect local access with a PIN
- avoid committing or exposing local secrets

## 2. Test Environment

Recommended local test environment:

```text
Operating system: macOS first, Windows second
Python: 3.11+
Ollama: installed and running
Ollama model: gemma4:e4b
Browser: Chrome, Safari, or Edge
Google account: test Gmail account
Google Sheet: blank test spreadsheet
```

Project path:

```text
/Users/shaileshshashi/Shailesh/Codex-Projects/GmailManager/coredyn-systems/gmail-manager
```

Local app URL:

```text
http://127.0.0.1:5055
```

## 3. Pre-Test Checklist

Before testing:

- Confirm Google Cloud project exists.
- Confirm Gmail API is enabled.
- Confirm Google Sheets API is enabled.
- Confirm OAuth Desktop credentials JSON is available.
- Confirm test Gmail account is added as OAuth test user if app is in External testing mode.
- Confirm test Google Sheet exists.
- Confirm Ollama is running:

```bash
ollama list
```

- Confirm `gemma4:e4b` is available.

## 4. Automated Regression Tests

Run from the repo root:

```bash
venv/bin/python -m pytest
```

Expected result:

```text
All tests pass
```

Current expected count:

```text
16 passed
```

Regression coverage includes:

- automated email detection
- dedupe log behavior
- Gmail HTML body extraction
- appointment signal row building
- Sheet URL extraction

## 5. Install Flow Test

### 5.1 macOS Installer

Steps:

1. Double-click:

```text
Install Gmail Manager.command
```

2. Confirm Terminal opens.
3. Confirm virtual environment is created or reused.
4. Confirm dependencies install successfully.
5. Confirm Ollama check runs.
6. Confirm setup guide opens.
7. Confirm local app opens at `http://127.0.0.1:5055`.

Expected result:

- Installer completes without errors.
- Browser app opens.
- Terminal shows Flask server running.

### 5.2 Start Script

Steps:

1. Stop the app.
2. Double-click:

```text
Start Gmail Manager.command
```

Expected result:

- App starts without reinstall confusion.
- Browser opens to the local dashboard or PIN screen.

### 5.3 Stop Script

Steps:

1. Double-click:

```text
Stop Gmail Manager.command
```

2. Visit `http://127.0.0.1:5055`.

Expected result:

- App server stops.
- Browser can no longer reach the local app.

## 6. First-Run Security Test

### 6.1 PIN Creation

Steps:

1. Start the app.
2. Open `http://127.0.0.1:5055`.
3. Confirm first screen is `Create Local PIN`.
4. Enter a PIN shorter than 6 characters.
5. Submit.
6. Enter mismatched PIN and confirmation.
7. Submit.
8. Enter a valid PIN/password with at least 6 characters.

Expected result:

- Short PIN is rejected.
- Mismatched PIN is rejected.
- Valid PIN is accepted.
- User lands on dashboard.

### 6.2 Lock And Login

Steps:

1. Click `Lock App`.
2. Confirm login screen appears.
3. Try incorrect PIN.
4. Try correct PIN.

Expected result:

- Incorrect PIN is rejected.
- Correct PIN unlocks dashboard.

## 7. Setup Screen Test

Steps:

1. Upload Google OAuth JSON file.
2. Paste full Google Sheet URL.
3. Save settings.
4. Confirm dashboard status cards update.

Expected result:

- Any `.json` OAuth file upload is accepted.
- App saves it locally as `credentials.json`.
- Full Sheet URL is converted into Sheet ID.
- `Google credentials` status becomes green.
- `Google Sheet` status becomes green.

Also test plain Sheet ID input:

```text
YOUR_GOOGLE_SHEET_ID
```

Expected result:

- Plain ID is accepted unchanged.

## 8. Gmail OAuth Test

Steps:

1. Click `Connect Gmail`.
2. Complete Google OAuth flow.
3. Approve requested permissions.
4. Return to app.

Expected result:

- `token.json` is created locally.
- Gmail status becomes green.
- App does not request Gmail write permissions.

Required Gmail scope:

```text
https://www.googleapis.com/auth/gmail.readonly
```

Failure cases to test:

- missing `credentials.json`
- OAuth test user not added
- Gmail API disabled

Expected result:

- App shows a friendly error and does not crash.

## 9. Ollama Test

### 9.1 Ollama Running

Steps:

1. Start Ollama.
2. Open dashboard.

Expected result:

- Ollama status is green.
- Model list includes `gemma4:e4b`.

### 9.2 Ollama Stopped

Steps:

1. Stop Ollama.
2. Refresh dashboard.
3. Click `Test Sample Data`.

Expected result:

- Ollama status is red.
- Sample scan fails with a clear error.
- App does not crash.

## 10. Sample Data Test

Steps:

1. Start Ollama.
2. Click `Test Sample Data`.

Expected result:

- App scans `data/sample_emails.csv`.
- Only genuine appointment sample is shown.
- Non-appointment samples are ignored.
- No Google credentials are required for sample data.

Expected sample behavior:

```text
1 appointment action
4 ignored non-appointment messages
```

## 11. Gmail Scan Preview Test

Steps:

1. Confirm Gmail is connected.
2. Confirm Sheet ID is saved.
3. Set scan days to `1`.
4. Set max emails to `100`.
5. Click `Scan Gmail`.

Expected result:

- Gmail messages are read.
- Automated emails are filtered before Ollama.
- Ollama evaluates remaining genuine-looking emails.
- Results appear in `Review Results`.
- Nothing is written to Google Sheets yet.

Expected result counters:

```text
Read N emails
Found X appointment actions
Ignored Y
Skipped Z duplicates
```

## 12. Automated Email Filtering Test

Use test emails or real Gmail examples containing:

- unsubscribe
- manage your preferences
- newsletter
- weekly digest
- security alert
- password reset
- OTP
- no-reply sender
- notification sender

Expected result:

- These emails are marked `Ignored / Automated`.
- They do not appear in `Today Action List`.
- They do not call Ollama.

## 13. Appointment Detection Test

Use emails with these intents:

- book an appointment
- ask for available slots
- reschedule a visit
- cancel a consultation
- confirm appointment timing
- ask to meet/call at a specific time

Expected result:

- Emails appear in preview.
- Category is `Appointment Request`.
- Priority is reasonable:
  - High for today/urgent/reschedule/cancel/no response
  - Medium for normal booking or availability
  - Low for tentative/unclear appointment mention

## 14. Non-Appointment Human Email Test

Use genuine human emails that are not appointment-related:

- payment-only email
- general question
- complaint without scheduling
- pricing enquiry
- thank you note

Expected result:

- These emails are marked `Not Appointment`.
- They do not appear in action preview.
- They are tracked in processed emails after writing.

## 15. Write To Google Sheet Test

Steps:

1. Run `Scan Gmail`.
2. Review appointment rows.
3. Click `Write to Google Sheet`.
4. Open the configured Google Sheet.

Expected result:

- `Today Action List` tab exists.
- Appointment rows are appended.
- `Processed Emails` tab exists.
- Processed IDs are recorded.
- `Settings` tab exists.
- No Gmail message is modified.

## 16. Duplicate Prevention Test

Steps:

1. Run scan and write.
2. Run scan again with same days and max results.

Expected result:

- Previously processed Gmail message IDs are skipped.
- Duplicate appointment rows are not added.

## 17. Reprocess And Reset Test

Steps:

1. Check `Recheck already processed emails`.
2. Check `Clear Today Action List before writing`.
3. Scan Gmail.
4. Review results.
5. Write to Google Sheet.

Expected result:

- Existing action rows are cleared.
- Recent Gmail messages are re-evaluated.
- Only current appointment-related rows are written.
- `Processed Emails` rows are not duplicated.

## 18. Clear Local Data Test

Steps:

1. Use Privacy & Local Data section.
2. Select `Clear local processed email log`.
3. Submit.

Expected result:

- `processed_emails.csv` is removed if present.
- App remains usable.

Repeat for:

- `Disconnect Gmail on this computer`
- `Remove uploaded Google OAuth file`

Expected result:

- `token.json` is removed for disconnect.
- `credentials.json` is removed for OAuth file removal.
- Status cards update after refresh.

## 19. Local Secret Handling Test

Confirm these files are git-ignored:

```bash
git status --ignored --short
```

Expected ignored files:

```text
.env
credentials.json
token.json
web_settings.json
pending_results.json
processed_emails.csv
output_action_list.csv
venv/
```

Expected result:

- No secrets or runtime files are staged.

## 20. Browser Compatibility Test

Test the local app in:

- Chrome
- Safari
- Edge

Expected result:

- Dashboard layout is usable.
- Forms submit correctly.
- Scan results table is readable.
- Mobile/narrow browser width does not break layout.

## 21. Error Handling Test Cases

Test these failure states:

- invalid Google Sheet ID
- Sheet API disabled
- Gmail API disabled
- deleted token file
- invalid credentials JSON
- Ollama model not found
- no internet connection for Google APIs
- no Gmail messages in date range

Expected result:

- User sees a clear error message.
- App does not expose stack traces in browser.
- App remains running.

## 22. Acceptance Criteria

The app is ready for a small-business pilot when:

- installer starts app successfully
- first-run PIN works
- credentials upload works
- Gmail connects with read-only scope
- Ollama status is visible
- sample scan returns only appointment emails
- Gmail scan previews results before writing
- Google Sheet write works
- duplicate prevention works
- automated emails are filtered out
- local clear-data controls work
- all automated tests pass
- no secrets are tracked by git

## 23. Known Limits

- Google Cloud OAuth setup still requires manual user steps.
- Ollama must be installed separately.
- The app is local-only and not a hosted SaaS.
- The Flask server is for local desktop use, not public internet deployment.
- Appointment quality depends on the local Ollama model.
