"""
Centralized constants for the video downloader application.

All hardcoded values should be defined here for easy maintenance.
"""

import random
from typing import Final

# Application metadata
APP_NAME: Final[str] = "Video Downloader"
APP_VERSION: Final[str] = "1.1.0"

# Video quality presets
VIDEO_QUALITIES: Final[dict[str, str]] = {
    "best": "bestvideo+bestaudio/best",
    "native": "bestvideo+bestaudio/best",
    "2160p": "bestvideo[height<=2160]+bestaudio/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best",
    "720p": "bestvideo[height<=720]+bestaudio/best",
    "480p": "bestvideo[height<=480]+bestaudio/best",
    "360p": "bestvideo[height<=360]+bestaudio/best",
}

# Audio format configurations
AUDIO_FORMATS: Final[dict[str, dict[str, str]]] = {
    "mp3": {"codec": "mp3", "quality": "320"},
    "wav": {"codec": "wav", "quality": "0"},  # 0 = lossless
    "flac": {"codec": "flac", "quality": "0"},
    "aac": {"codec": "aac", "quality": "256"},
    "opus": {"codec": "opus", "quality": "128"},
    "audio": {"codec": "mp3", "quality": "320"},  # Default audio
}

# GUI quality dropdown options
GUI_QUALITY_OPTIONS: Final[list[str]] = [
    "best",
    "native",
    "2160p",
    "1080p",
    "720p",
    "480p",
    "mp3",
    "wav",
    "flac",
]

# Download defaults
DEFAULT_TIMEOUT: Final[int] = 300  # seconds
DEFAULT_RETRY_ATTEMPTS: Final[int] = 3
DEFAULT_MAX_CONCURRENT: Final[int] = 3
DEFAULT_OUTPUT_DIR: Final[str] = "downloads"

# Transcription presets
TRANSCRIPTION_PRESETS: Final[dict[str, tuple[str, str, int]]] = {
    "fast": ("tiny.en", "int8", 1),
    "balanced": ("small.en", "int8", 5),
    "accurate": ("medium.en", "int8", 5),
}

# External tool URLs
DENO_DOWNLOAD_URL: Final[str] = "https://deno.com/"
FFMPEG_DOWNLOAD_URL: Final[str] = "https://ffmpeg.org/download.html"

# Windows reserved filenames
WINDOWS_RESERVED_NAMES: Final[frozenset[str]] = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
)

# Illegal filename characters on Windows
ILLEGAL_FILENAME_CHARS: Final[str] = '<>:"/\\|?*'

# Realistic User-Agent pool (updated January 2026)
# Rotating User-Agents helps avoid bot detection
USER_AGENTS: Final[list[str]] = [
    # Chrome on Windows (most common)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
]


def get_random_user_agent() -> str:
    """
    Get a random realistic User-Agent string.

    Returns:
        Random User-Agent from the pool
    """
    return random.choice(USER_AGENTS)


def get_matching_user_agent(browser: str) -> str:
    """
    Get a User-Agent that matches the browser being used for cookies.

    This helps avoid detection by ensuring cookie source matches User-Agent.

    Args:
        browser: Browser name (firefox, chrome, edge, etc.)

    Returns:
        Matching User-Agent string
    """
    browser_lower = browser.lower()

    for ua in USER_AGENTS:
        if browser_lower == "firefox" and "Firefox" in ua:
            return ua
        elif (
            browser_lower in ("chrome", "chromium", "brave", "vivaldi", "opera", "whale")
            and "Chrome" in ua
            and "Edg" not in ua
        ):
            return ua
        elif browser_lower == "edge" and "Edg" in ua:
            return ua
        elif browser_lower == "safari" and "Safari" in ua and "Chrome" not in ua:
            return ua

    # Default to Chrome User-Agent
    return USER_AGENTS[0]
