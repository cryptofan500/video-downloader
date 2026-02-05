"""Utility modules."""

from video_downloader.utils.config import AppConfig, DownloadConfig
from video_downloader.utils.constants import (
    APP_NAME,
    APP_VERSION,
    AUDIO_FORMATS,
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_TIMEOUT,
    GUI_QUALITY_OPTIONS,
    VIDEO_QUALITIES,
)
from video_downloader.utils.exceptions import (
    ConfigurationError,
    DownloadError,
    NetworkError,
    RuntimeNotFoundError,
    ValidationError,
    VideoDownloaderError,
)
from video_downloader.utils.ffmpeg_manager import FFmpegManager
from video_downloader.utils.path_utils import (
    get_application_path,
    get_bin_path,
    get_config_path,
    get_default_output_dir,
    get_resource_path,
    is_frozen,
    safe_path_str,
    setup_environment_paths,
)
from video_downloader.utils.validators import PathValidator, URLValidator

__all__ = [
    # Config
    "AppConfig",
    "DownloadConfig",
    # Constants
    "APP_NAME",
    "APP_VERSION",
    "VIDEO_QUALITIES",
    "AUDIO_FORMATS",
    "GUI_QUALITY_OPTIONS",
    "DEFAULT_TIMEOUT",
    "DEFAULT_RETRY_ATTEMPTS",
    "DEFAULT_MAX_CONCURRENT",
    "DEFAULT_OUTPUT_DIR",
    # FFmpeg
    "FFmpegManager",
    # Validators
    "URLValidator",
    "PathValidator",
    # Path utilities
    "get_application_path",
    "get_bin_path",
    "get_config_path",
    "get_default_output_dir",
    "get_resource_path",
    "is_frozen",
    "safe_path_str",
    "setup_environment_paths",
    # Exceptions
    "VideoDownloaderError",
    "NetworkError",
    "DownloadError",
    "ValidationError",
    "ConfigurationError",
    "RuntimeNotFoundError",
]
