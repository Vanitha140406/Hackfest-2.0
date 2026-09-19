@echo off
cd /d "%~dp0"
echo ===================================================================
echo   CAMPUS BITES: Indian College Canteen Smart Queue System
echo   Starting server at http://127.0.0.1:5000
echo ===================================================================
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
) else (
    python app.py
)
pause
