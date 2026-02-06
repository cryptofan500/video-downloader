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

echo [1/4] Installing uv package manager...
pip install uv --quiet

echo [2/4] Creating virtual environment...
uv venv .venv

echo [3/4] Installing dependencies...
call .venv\Scripts\activate.bat
uv pip install -e ".[dev]"

echo [4/4] Creating downloads folder...
if not exist "downloads" mkdir downloads

echo.
echo ==========================================
echo   SETUP COMPLETE
echo ==========================================
echo.
echo To run: double-click run.bat
echo.
pause
