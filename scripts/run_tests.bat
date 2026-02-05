@echo off
REM Comprehensive Video Downloader Test Suite
REM Runs all URL flavor, quality, and browser tests

echo ============================================================
echo VIDEO DOWNLOADER COMPREHENSIVE TEST SUITE
echo ============================================================
echo.

cd /d "%~dp0.."

if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo Running test suite...
echo.

python scripts\comprehensive_test.py %*

echo.
echo Test complete. Reports saved to: %USERPROFILE%\Downloads\video_downloader_tests\reports
echo.
pause
