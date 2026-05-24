@echo off
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5055') do taskkill /PID %%a /F
echo Gmail Manager stopped.
