@echo off
cd /d "%~dp0"
echo.
echo Gmail to Action Sheet installer
echo Qorvia Systems
echo --------------------------------

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11+ and run this installer again.
  pause
  exit /b 1
)

echo Creating local Python environment...
if not exist venv (
  python -m venv venv
)

echo Installing required packages...
venv\Scripts\pip install -r requirements.txt

echo Checking Ollama...
where ollama >nul 2>nul
if errorlevel 1 (
  echo Ollama was not found. Install Ollama before using appointment AI filtering.
) else (
  ollama list
)

echo Opening setup guide and local app...
start docs\gmail_setup.html
start http://127.0.0.1:5055

echo.
echo Install complete.
echo The local app is starting at http://127.0.0.1:5055
echo Use Stop Gmail Action Sheet.bat to stop it.
echo.

venv\Scripts\python web_app.py

