@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Splits an AI answer (pasted into ai-answer.txt) into plugins\<id>\ and checks it against PLUGIN_GUIDE.md.
rem The first run installs Python + libraries (see tools\setup.ps1).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\setup.ps1"
if errorlevel 1 goto :err
".venv\Scripts\python.exe" tools\plugin_from_text.py ai-answer.txt
echo.
pause
goto :eof

:err
echo.
echo Setup failed (see the messages above). Internet is needed to download Python and libraries.
pause
