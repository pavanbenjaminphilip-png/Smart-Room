@echo off
echo ========================================
echo Smart Room App Server
echo ========================================
echo.
echo Starting web server...
echo Access from phone: http://192.168.0.101:8000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.
python -m http.server 8000
