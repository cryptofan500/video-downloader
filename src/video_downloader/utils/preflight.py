"""
Pre-download validation checks.

Runs connectivity, YouTube access, and disk space checks before downloading.
"""

import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from video_downloader.utils.constants import get_random_user_agent


@dataclass
class PreflightResult:
    """Result of pre-flight checks."""

    passed: bool
    issues: list[str]
    warnings: list[str]

    @property
    def has_issues(self) -> bool:
        """Check if there are any issues."""
        return len(self.issues) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


def check_internet_connectivity(timeout: float = 5.0) -> tuple[bool, str]:
    """
    Check if internet is accessible.

    Tests multiple reliable endpoints to avoid false negatives.

    Args:
        timeout: Request timeout in seconds

    Returns:
        Tuple of (is_connected, status_message)
    """
    test_urls = [
        "https://www.google.com",
        "https://1.1.1.1",
        "https://www.cloudflare.com",
    ]

    for url in test_urls:
        try:
            urllib.request.urlopen(url, timeout=timeout)
            return True, "Internet connection OK"
        except Exception:
            continue

    return False, "No internet connection detected"


def check_youtube_accessible(timeout: float = 10.0) -> tuple[bool, str]:
    """
    Check if YouTube is accessible and not blocking.

    Uses robots.txt as a lightweight check endpoint.

    Args:
        timeout: Request timeout in seconds

    Returns:
        Tuple of (is_accessible, status_message)
    """
    try:
        req = urllib.request.Request(
            "https://www.youtube.com/robots.txt",
            headers={"User-Agent": get_random_user_agent()},
        )
        response = urllib.request.urlopen(req, timeout=timeout)

        if response.status == 200:
            return True, "YouTube accessible"
        else:
            return False, f"YouTube returned status {response.status}"

    except urllib.error.HTTPError as e:
        if e.code == 429:
            return False, "YouTube is rate limiting this IP - wait before retrying"
        elif e.code == 403:
            return False, "YouTube is blocking this IP - try using a VPN"
        else:
            return False, f"YouTube HTTP error: {e.code}"
    except urllib.error.URLError as e:
        return False, f"Cannot reach YouTube: {e.reason}"
    except Exception as e:
        return False, f"YouTube check failed: {e}"


def check_disk_space(path: Path, min_gb: float = 2.0) -> tuple[bool, float, str]:
    """
    Check available disk space at the given path.

    Args:
        path: Path to check (uses its mount point)
        min_gb: Minimum required space in GB

    Returns:
        Tuple of (has_enough_space, available_gb, status_message)
    """
    try:
        # Use parent if path doesn't exist yet
        check_path = path
        while not check_path.exists() and check_path.parent != check_path:
            check_path = check_path.parent

        usage = shutil.disk_usage(check_path)
        available_gb = usage.free / (1024**3)

        if available_gb >= min_gb:
            return True, available_gb, f"{available_gb:.1f} GB available"
        else:
            return (
                False,
                available_gb,
                f"Low disk space: {available_gb:.1f} GB available (need {min_gb} GB)",
            )
    except Exception as e:
        # If we can't check, assume OK but warn
        return True, 0.0, f"Could not check disk space: {e}"


def run_preflight_checks(
    output_dir: Path,
    min_disk_gb: float = 2.0,
    check_youtube: bool = True,
) -> PreflightResult:
    """
    Run all pre-flight checks before downloading.

    Args:
        output_dir: Directory where files will be downloaded
        min_disk_gb: Minimum required disk space in GB
        check_youtube: Whether to check YouTube accessibility

    Returns:
        PreflightResult with pass/fail status and any issues/warnings
    """
    issues: list[str] = []
    warnings: list[str] = []

    # Check 1: Internet connectivity
    internet_ok, internet_msg = check_internet_connectivity()
    if not internet_ok:
        issues.append(internet_msg)
    else:
        # Check 2: YouTube accessibility (only if internet works)
        if check_youtube:
            yt_ok, yt_msg = check_youtube_accessible()
            if not yt_ok:
                # Rate limiting is a warning, not a hard failure
                if "rate limit" in yt_msg.lower():
                    warnings.append(yt_msg)
                else:
                    issues.append(yt_msg)

    # Check 3: Disk space
    space_ok, available_gb, space_msg = check_disk_space(output_dir, min_disk_gb)
    if not space_ok:
        issues.append(space_msg)
    elif available_gb < min_disk_gb * 2:
        # Warn if space is getting low
        warnings.append(f"Disk space is limited: {available_gb:.1f} GB remaining")

    return PreflightResult(
        passed=len(issues) == 0,
        issues=issues,
        warnings=warnings,
    )
