@echo off
echo ========================================
echo Restarting Smart Room Server
echo ========================================

REM Kill existing Python processes running the server
echo Stopping existing server...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

REM Start the server
echo Starting server with ESP32 proxy routes...
cd /d "%~dp0"
python server.py
