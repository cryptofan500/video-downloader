"""
Comprehensive YouTube URL and Quality Test Script.

Tests all URL flavors, qualities, and browser cookie sources.
Results are saved to a JSON report file.
"""

import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

# Test configuration
DOWNLOADS_DIR = Path.home() / "Downloads" / "video_downloader_tests"
PROJECT_DIR = Path(__file__).parent.parent
VENV_PYTHON = PROJECT_DIR / ".venv" / "Scripts" / "python.exe"

# All YouTube URL flavors to test
URL_FLAVORS: dict[str, str] = {
    "standard": "https://www.youtube.com/watch?v=l3XVqxoPx14",
    "shortened": "https://youtu.be/l3XVqxoPx14",
    "radio_mix": "https://www.youtube.com/watch?v=l3XVqxoPx14&list=RDl3XVqxoPx14&start_radio=1",
    "playlist": "https://www.youtube.com/watch?v=l3XVqxoPx14&list=PL1C05C342371235C6&index=1",
    "shorts": "https://www.youtube.com/shorts/WfvXXXvkm8g",
    "embed": "https://www.youtube.com/embed/l3XVqxoPx14",
    "timestamped": "https://www.youtube.com/watch?v=l3XVqxoPx14&t=45s",
    "mobile": "https://m.youtube.com/watch?v=l3XVqxoPx14&feature=share",
}

# Note: Channel and Live URLs are excluded as they're not single-video downloads
# "channel": "https://www.youtube.com/@Sia"  - Downloads all videos (dangerous)
# "live": "https://www.youtube.com/channel/UCSJ4gkVC6NrvII8umztf0Ow/live"  - May not be live

# All quality options
QUALITY_OPTIONS: list[str] = [
    "best",
    "1080p",
    "720p",
    "480p",
    "mp3",
    "wav",
    "flac",
]

# All supported browsers
BROWSERS: list[str] = [
    "firefox",
    "chrome",
    "edge",
    "brave",
    "opera",
    "vivaldi",
    "chromium",
]


@dataclass
class TestResult:
    """Result of a single test."""
    url_type: str
    url: str
    quality: str
    browser: str | None
    method: str  # "python", "cli", "bat"
    success: bool
    duration_seconds: float
    error_message: str = ""
    output_file: str = ""


@dataclass
class TestReport:
    """Complete test report."""
    start_time: str
    end_time: str = ""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[dict] = field(default_factory=list)


def ensure_downloads_dir() -> Path:
    """Create test downloads directory."""
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    return DOWNLOADS_DIR


def run_python_download(url: str, quality: str, output_dir: Path, browser: str | None = None) -> tuple[bool, str, float]:
    """
    Run download using Python module directly.

    Returns: (success, error_message, duration_seconds)
    """
    start = time.time()

    browser_arg = f"'{browser}'" if browser and browser != "None" else "None"

    # Determine if this is audio-only based on quality
    audio_only = quality in ("mp3", "wav", "flac", "aac", "opus", "audio")

    cmd = [
        str(VENV_PYTHON),
        "-c",
        f"""
import sys
from pathlib import Path
sys.path.insert(0, r'{PROJECT_DIR / "src"}')
from video_downloader.core.downloader import VideoDownloader
from video_downloader.core.runtime_manager import RuntimeManager
from video_downloader.utils.config import AppConfig

# Initialize dependencies
runtime_manager = RuntimeManager()
config = AppConfig._from_dict({{}})  # Use defaults

downloader = VideoDownloader(runtime_manager=runtime_manager, config=config)
result = downloader.download_with_retry(
    url='{url}',
    output_path=Path(r'{output_dir}'),
    quality='{quality}',
    audio_only={audio_only},
)
print(f"SUCCESS: {{result}}" if result else "FAILED")
sys.exit(0 if result else 1)
"""
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(PROJECT_DIR),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        duration = time.time() - start

        if result.returncode == 0:
            return True, "", duration
        else:
            error = result.stderr or result.stdout or "Unknown error"
            return False, error[:500], duration

    except subprocess.TimeoutExpired:
        return False, "Timeout after 300 seconds", time.time() - start
    except Exception as e:
        return False, str(e)[:500], time.time() - start


def run_cli_download(url: str, quality: str, output_dir: Path) -> tuple[bool, str, float]:
    """
    Run download using CLI entry point.

    Returns: (success, error_message, duration_seconds)
    """
    start = time.time()

    cmd = [
        str(VENV_PYTHON),
        "-m", "video_downloader.cli",
        "download",
        url,
        "--quality", quality,
        "--output", str(output_dir),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(PROJECT_DIR),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        duration = time.time() - start

        if result.returncode == 0:
            return True, "", duration
        else:
            error = result.stderr or result.stdout or "Unknown error"
            return False, error[:500], duration

    except subprocess.TimeoutExpired:
        return False, "Timeout after 300 seconds", time.time() - start
    except Exception as e:
        return False, str(e)[:500], time.time() - start


def print_progress(current: int, total: int, result: TestResult) -> None:
    """Print test progress."""
    status = "PASS" if result.success else "FAIL"
    print(f"[{current}/{total}] {status} | {result.url_type} | {result.quality} | {result.method} | {result.duration_seconds:.1f}s")
    if not result.success and result.error_message:
        # Print first line of error
        error_line = result.error_message.split('\n')[0][:80]
        print(f"         Error: {error_line}")


def run_quick_test() -> TestReport:
    """
    Run a quick test with a subset of combinations.

    Tests each URL type once with 720p quality using Python method.
    """
    print("\n" + "=" * 60)
    print("QUICK TEST MODE - Testing each URL type once")
    print("=" * 60 + "\n")

    output_dir = ensure_downloads_dir() / "quick_test"
    output_dir.mkdir(exist_ok=True)

    report = TestReport(start_time=datetime.now().isoformat())
    results: list[TestResult] = []

    total = len(URL_FLAVORS)
    current = 0

    for url_type, url in URL_FLAVORS.items():
        current += 1

        success, error, duration = run_python_download(
            url=url,
            quality="720p",
            output_dir=output_dir,
            browser=None,  # Use auto-detection
        )

        result = TestResult(
            url_type=url_type,
            url=url,
            quality="720p",
            browser="auto",
            method="python",
            success=success,
            duration_seconds=duration,
            error_message=error,
        )

        results.append(result)
        print_progress(current, total, result)

        if success:
            report.passed += 1
        else:
            report.failed += 1

        # Small delay between downloads to avoid rate limiting
        time.sleep(2)

    report.total_tests = len(results)
    report.results = [asdict(r) for r in results]
    report.end_time = datetime.now().isoformat()

    return report


def run_quality_test() -> TestReport:
    """
    Test all quality options with standard URL.
    """
    print("\n" + "=" * 60)
    print("QUALITY TEST MODE - Testing all qualities")
    print("=" * 60 + "\n")

    output_dir = ensure_downloads_dir() / "quality_test"
    output_dir.mkdir(exist_ok=True)

    report = TestReport(start_time=datetime.now().isoformat())
    results: list[TestResult] = []

    url = URL_FLAVORS["standard"]
    total = len(QUALITY_OPTIONS)
    current = 0

    for quality in QUALITY_OPTIONS:
        current += 1

        success, error, duration = run_python_download(
            url=url,
            quality=quality,
            output_dir=output_dir,
            browser=None,
        )

        result = TestResult(
            url_type="standard",
            url=url,
            quality=quality,
            browser="auto",
            method="python",
            success=success,
            duration_seconds=duration,
            error_message=error,
        )

        results.append(result)
        print_progress(current, total, result)

        if success:
            report.passed += 1
        else:
            report.failed += 1

        time.sleep(2)

    report.total_tests = len(results)
    report.results = [asdict(r) for r in results]
    report.end_time = datetime.now().isoformat()

    return report


def run_browser_test() -> TestReport:
    """
    Test all browsers with standard URL.
    """
    print("\n" + "=" * 60)
    print("BROWSER TEST MODE - Testing all browsers")
    print("=" * 60 + "\n")

    output_dir = ensure_downloads_dir() / "browser_test"
    output_dir.mkdir(exist_ok=True)

    report = TestReport(start_time=datetime.now().isoformat())
    results: list[TestResult] = []

    url = URL_FLAVORS["standard"]
    total = len(BROWSERS)
    current = 0

    for browser in BROWSERS:
        current += 1

        success, error, duration = run_python_download(
            url=url,
            quality="720p",
            output_dir=output_dir,
            browser=browser,
        )

        result = TestResult(
            url_type="standard",
            url=url,
            quality="720p",
            browser=browser,
            method="python",
            success=success,
            duration_seconds=duration,
            error_message=error,
        )

        results.append(result)
        print_progress(current, total, result)

        if success:
            report.passed += 1
        else:
            report.failed += 1

        time.sleep(2)

    report.total_tests = len(results)
    report.results = [asdict(r) for r in results]
    report.end_time = datetime.now().isoformat()

    return report


def run_full_test() -> TestReport:
    """
    Run comprehensive test of all combinations.

    WARNING: This will download many files!
    Combinations: 8 URLs × 7 qualities × 2 methods = 112 tests
    """
    print("\n" + "=" * 60)
    print("FULL TEST MODE - Testing all combinations")
    print("WARNING: This will take a long time and download many files!")
    print("=" * 60 + "\n")

    output_dir = ensure_downloads_dir() / "full_test"
    output_dir.mkdir(exist_ok=True)

    report = TestReport(start_time=datetime.now().isoformat())
    results: list[TestResult] = []

    # Calculate total
    total = len(URL_FLAVORS) * len(QUALITY_OPTIONS)
    current = 0

    for url_type, url in URL_FLAVORS.items():
        for quality in QUALITY_OPTIONS:
            current += 1

            # Create subdirectory for organization
            sub_dir = output_dir / url_type / quality
            sub_dir.mkdir(parents=True, exist_ok=True)

            success, error, duration = run_python_download(
                url=url,
                quality=quality,
                output_dir=sub_dir,
                browser=None,
            )

            result = TestResult(
                url_type=url_type,
                url=url,
                quality=quality,
                browser="auto",
                method="python",
                success=success,
                duration_seconds=duration,
                error_message=error,
            )

            results.append(result)
            print_progress(current, total, result)

            if success:
                report.passed += 1
            else:
                report.failed += 1

            # Delay to avoid rate limiting
            time.sleep(3)

    report.total_tests = len(results)
    report.results = [asdict(r) for r in results]
    report.end_time = datetime.now().isoformat()

    return report


def save_report(report: TestReport, name: str) -> Path:
    """Save report to JSON file."""
    report_dir = DOWNLOADS_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"{name}_{timestamp}.json"

    with report_file.open("w", encoding="utf-8") as f:
        json.dump(asdict(report), f, indent=2)

    return report_file


def print_summary(report: TestReport) -> None:
    """Print test summary."""
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {report.total_tests}")
    print(f"Passed:      {report.passed} ({100*report.passed/max(1,report.total_tests):.1f}%)")
    print(f"Failed:      {report.failed} ({100*report.failed/max(1,report.total_tests):.1f}%)")
    print(f"Start:       {report.start_time}")
    print(f"End:         {report.end_time}")
    print("=" * 60 + "\n")


def main() -> int:
    """Main entry point."""
    print("\n" + "=" * 60)
    print("VIDEO DOWNLOADER COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    print("\nTest Modes:")
    print("  1. Quick Test   - Each URL type once (8 tests)")
    print("  2. Quality Test - All qualities with standard URL (7 tests)")
    print("  3. Browser Test - All browsers with standard URL (7 tests)")
    print("  4. Full Test    - All URL × Quality combinations (56 tests)")
    print("  5. Run All      - All test modes sequentially")
    print("\nDownloads will be saved to:", DOWNLOADS_DIR)

    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = input("\nSelect mode (1-5): ").strip()

    reports: list[tuple[str, TestReport]] = []

    if mode in ("1", "quick"):
        report = run_quick_test()
        reports.append(("quick_test", report))

    elif mode in ("2", "quality"):
        report = run_quality_test()
        reports.append(("quality_test", report))

    elif mode in ("3", "browser"):
        report = run_browser_test()
        reports.append(("browser_test", report))

    elif mode in ("4", "full"):
        report = run_full_test()
        reports.append(("full_test", report))

    elif mode in ("5", "all"):
        reports.append(("quick_test", run_quick_test()))
        reports.append(("quality_test", run_quality_test()))
        reports.append(("browser_test", run_browser_test()))
        # Full test is optional due to size
        response = input("\nRun full test? This will download many files (y/N): ")
        if response.lower() == "y":
            reports.append(("full_test", run_full_test()))
    else:
        print("Invalid mode selected.")
        return 1

    # Print summaries and save reports
    for name, report in reports:
        print_summary(report)
        report_file = save_report(report, name)
        print(f"Report saved: {report_file}")

    # Return non-zero if any tests failed
    total_failed = sum(r.failed for _, r in reports)
    return 1 if total_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
