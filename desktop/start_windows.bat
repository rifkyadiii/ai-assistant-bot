@echo off
REM VoiceBot OS - Windows Desktop Launcher
REM Starts the VoiceBot server and opens the native desktop window.
REM Close this window or press Ctrl+C to stop the application.

setlocal enabledelayedexpansion

cd /d "%~dp0.."

echo ==========================================
echo    VoiceBot OS - Desktop App (Windows)
echo ==========================================
echo    Web console:  http://localhost:5000
echo    Press Ctrl+C to stop
echo ==========================================
echo.

REM Resolve Python from project venv otherwise system python
set "PYTHON=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    set "PYTHON=python"
    where python >nul 2>nul
    if errorlevel 1 (
        echo ERROR: Python not found in PATH or .venv.
        pause
        exit /b 1
    )
)

REM Create venv if missing
if not exist "%~dp0..\.venv\Scripts\python.exe" (
    echo [setup] Creating virtual environment...
    python -m venv "%~dp0..\.venv"
    "%~dp0..\.venv\Scripts\pip.exe" install --upgrade pip
    "%~dp0..\.venv\Scripts\pip.exe" install -r "%~dp0..\requirements.txt"
)

REM Run the VoiceBot server in the foreground.
REM main.py automatically opens the browser window.
"%PYTHON%" "%~dp0..\main.py"

pause