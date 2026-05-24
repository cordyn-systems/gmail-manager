@echo off
cd /d "%~dp0"
if not exist venv (
  python -m venv venv
)
venv\Scripts\pip install -r requirements.txt >nul
start http://127.0.0.1:5055
venv\Scripts\python web_app.py

