@echo off
:: Video Downloader - Setup Script

echo ==========================================
echo   VIDEO DOWNLOADER - SETUP
echo ==========================================
echo.

cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.12+
    pause
    exit /b 1
)

echo [1/5] Installing uv package manager...
pip install uv --quiet

echo [2/5] Creating virtual environment...
uv venv .venv

echo [3/5] Installing dependencies...
call .venv\Scripts\activate.bat
uv pip install -e ".[dev]"

echo [4/5] Fetching FFmpeg and Deno binaries...
python scripts/fetch_binaries.py

echo [5/5] Creating downloads folder...
if not exist "downloads" mkdir downloads

echo.
echo ==========================================
echo   SETUP COMPLETE
echo ==========================================
echo.
echo To run: double-click run.bat
echo.
pause
