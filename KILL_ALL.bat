@echo off
echo ==================================================
echo   STOPPING ALL SMART ROOM PROCESSES
echo ==================================================

echo 1. Stopping Python Servers...
taskkill /F /IM python.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo    - Python stopped
) else (
    echo    - No Python processes found
)

echo 2. Stopping Ngrok Tunnels...
taskkill /F /IM ngrok.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo    - Ngrok stopped
) else (
    echo    - No Ngrok processes found
)

echo.
echo ==================================================
echo   ALL PORTS CLEARED
echo ==================================================
echo You can now run START_SERVER.bat cleanly.
pause
