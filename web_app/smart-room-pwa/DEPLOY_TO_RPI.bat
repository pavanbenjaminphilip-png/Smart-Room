@echo off
REM ============================================================
REM Smart Room - One-Click Deployment to Raspberry Pi 5
REM ============================================================

echo.
echo ========================================================================
echo  Smart Room - Deploying to Raspberry Pi 5
echo ========================================================================
echo.
echo This will:
echo   1. Copy all files to your Raspberry Pi
echo   2. Install dependencies
echo   3. Setup auto-start service
echo   4. Reboot the Pi
echo.
echo You will be prompted for the SSH password (default: raspberry)
echo.
pause

powershell.exe -ExecutionPolicy Bypass -File "%~dp0deploy_to_rpi.ps1"

echo.
pause
