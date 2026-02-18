@echo off
REM Scripts/nativeclaw.bat
REM Launcher for nativeclaw from anywhere in project

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "NATIVECLAW=%PROJECT_ROOT%\tools\nativeclaw\nativeclaw.py"

python "%NATIVECLAW%" %*