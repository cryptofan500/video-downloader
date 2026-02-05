@echo off
:: Video Downloader - Standard Launcher
:: Shows console window for debugging

cd /d "%~dp0"

:: Check for virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] Virtual environment not found.
    echo Run: uv venv .venv ^&^& uv pip install -e ".[dev]"
    pause
    exit /b 1
)

:: Run application
python -m video_downloader

:: Keep window open on error
if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with error code %errorlevel%
    pause
)
