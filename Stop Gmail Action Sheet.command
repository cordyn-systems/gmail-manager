#!/bin/zsh
PORT=5055
PID=$(lsof -ti tcp:$PORT)
if [ -z "$PID" ]; then
  echo "Gmail to Action Sheet is not running on port $PORT."
  exit 0
fi
kill "$PID"
echo "Gmail to Action Sheet stopped."

