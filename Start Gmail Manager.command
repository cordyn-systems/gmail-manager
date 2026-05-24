#!/bin/zsh
cd "$(dirname "$0")"
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
venv/bin/pip install -r requirements.txt >/dev/null
open "http://127.0.0.1:5055"
venv/bin/python web_app.py

