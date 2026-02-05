"""
Custom exceptions for video downloader application.

Provides a hierarchy of exceptions for different error scenarios.
"""


class VideoDownloaderError(Exception):
    """Base exception for all application errors."""

    pass


class NetworkError(VideoDownloaderError):
    """Raised when network operations fail."""

    pass


class DownloadError(VideoDownloaderError):
    """Raised when download operations fail."""

    pass


class ValidationError(VideoDownloaderError):
    """Raised when input validation fails."""

    pass


class ConfigurationError(VideoDownloaderError):
    """Raised when configuration is invalid or missing."""

    pass


class RuntimeNotFoundError(VideoDownloaderError):
    """Raised when required runtime (Deno, FFmpeg) is not found."""

    def __init__(self, runtime_name: str, message: str = ""):
        self.runtime_name = runtime_name
        if not message:
            message = (
                f"{runtime_name} not found. Please install {runtime_name} or ensure it's bundled."
            )
        super().__init__(message)
