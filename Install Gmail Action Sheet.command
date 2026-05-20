#!/bin/zsh
set -e

cd "$(dirname "$0")"

echo ""
echo "Gmail to Action Sheet installer"
echo "Qorvia Systems"
echo "--------------------------------"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found. Install Python 3.11+ and run this installer again."
  exit 1
fi

echo "Creating local Python environment..."
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

echo "Installing required packages..."
venv/bin/pip install -r requirements.txt

echo "Checking Ollama..."
if command -v ollama >/dev/null 2>&1; then
  ollama list || true
else
  echo "Ollama was not found. Install Ollama before using appointment AI filtering."
fi

echo "Opening setup guide and local app..."
open "docs/gmail_setup.html" || true
open "http://127.0.0.1:5055" || true

echo ""
echo "Install complete."
echo "The local app is starting at http://127.0.0.1:5055"
echo "Use Stop Gmail Action Sheet.command to stop it."
echo ""

venv/bin/python web_app.py

