"""
Video Downloader - Modern video downloading application.

A production-ready video downloader using yt-dlp with Deno runtime,
FFmpeg integration, and CustomTkinter GUI.
"""

__version__ = "1.1.0"
__author__ = "Pawel Zawadzki"
__license__ = "MIT"

# Expose main API
from video_downloader.core import (
    RuntimeManager,
    ThreadedDownloadManager,
    VideoDownloader,
)
from video_downloader.gui import DiagnosticsPane, MainWindow, main
from video_downloader.utils import (
    AppConfig,
    ConfigurationError,
    DownloadConfig,
    DownloadError,
    FFmpegManager,
    NetworkError,
    PathValidator,
    RuntimeNotFoundError,
    URLValidator,
    ValidationError,
    VideoDownloaderError,
)

__all__ = [
    # Core
    "VideoDownloader",
    "RuntimeManager",
    "ThreadedDownloadManager",
    # GUI
    "MainWindow",
    "DiagnosticsPane",
    "main",
    # Utils
    "AppConfig",
    "DownloadConfig",
    "FFmpegManager",
    "URLValidator",
    "PathValidator",
    # Exceptions
    "VideoDownloaderError",
    "NetworkError",
    "DownloadError",
    "ValidationError",
    "ConfigurationError",
    "RuntimeNotFoundError",
]
