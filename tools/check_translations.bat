@echo off
rem Double-click to check the translations with your Gemini key (uses the app's own Python).
cd /d "%~dp0.."
chcp 65001 >nul
".venv\Scripts\python.exe" "tools\check_translations.py" %*
echo.
pause
