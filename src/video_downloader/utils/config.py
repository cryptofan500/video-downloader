"""
Configuration management using TOML.

Provides type-safe configuration loading with defaults.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from video_downloader.utils.exceptions import ConfigurationError


def get_default_downloads_folder() -> Path:
    """
    Get the user's default Downloads folder.

    Works across different Windows usernames and platforms.

    Returns:
        Path to user's Downloads folder
    """
    downloads = Path.home() / "Downloads"
    if downloads.exists():
        return downloads
    # Fallback to home directory if Downloads doesn't exist
    return Path.home()


@dataclass
class DownloadConfig:
    """Download-specific configuration."""

    output_dir: Path
    max_concurrent: int
    timeout: int
    retry_attempts: int
    quality: str

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.max_concurrent < 1:
            raise ConfigurationError("max_concurrent must be at least 1")
        if self.timeout < 1:
            raise ConfigurationError("timeout must be positive")
        if self.retry_attempts < 0:
            raise ConfigurationError("retry_attempts cannot be negative")

        # Resolve special path placeholders
        output_str = str(self.output_dir)
        if output_str == "downloads" or output_str == "~/Downloads":
            # Use user's actual Downloads folder
            self.output_dir = get_default_downloads_folder()
        elif output_str.startswith("~"):
            # Expand home directory
            self.output_dir = Path(output_str).expanduser()

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class AppConfig:
    """
    Application configuration loaded from TOML file.

    Provides type-safe access to all configuration values with validation.
    """

    title: str
    version: str
    download: DownloadConfig

    @classmethod
    def from_toml(cls, config_path: Path) -> "AppConfig":
        """
        Load configuration from TOML file.

        Args:
            config_path: Path to TOML configuration file

        Returns:
            AppConfig instance

        Raises:
            ConfigurationError: If config file is invalid or missing
        """
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)

            return cls._from_dict(data)

        except tomllib.TOMLDecodeError as e:
            raise ConfigurationError(f"Invalid TOML syntax: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        """Create AppConfig from dictionary."""
        try:
            app_data = data.get("app", {})
            download_data = data.get("download", {})

            return cls(
                title=app_data.get("title", "Video Downloader"),
                version=app_data.get("version", "1.0.0"),
                download=DownloadConfig(
                    output_dir=Path(download_data.get("output_dir", "downloads")),
                    max_concurrent=download_data.get("max_concurrent", 3),
                    timeout=download_data.get("timeout", 300),
                    retry_attempts=download_data.get("retry_attempts", 3),
                    quality=download_data.get("quality", "best"),
                ),
            )
        except Exception as e:
            raise ConfigurationError(f"Invalid configuration structure: {e}")

    @classmethod
    def create_default(cls, config_path: Path) -> "AppConfig":
        """
        Create default configuration file.

        Args:
            config_path: Path where config file should be created

        Returns:
            AppConfig instance with defaults
        """
        default_toml = """# Video Downloader Configuration

[app]
title = "Video Downloader"
version = "1.0.0"

[download]
# Output directory for downloaded videos
# Use "downloads" for user's Downloads folder (recommended)
# Or specify an absolute path like "C:/Videos" or "~/Videos"
output_dir = "downloads"

# Maximum concurrent downloads
max_concurrent = 3

# Download timeout in seconds
timeout = 300

# Number of retry attempts on failure
retry_attempts = 3

# Default quality (best, 1080p, 720p, 480p, audio)
quality = "best"
"""

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(default_toml, encoding="utf-8")
            return cls.from_toml(config_path)
        except Exception as e:
            raise ConfigurationError(f"Failed to create default config: {e}")
