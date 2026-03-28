"""
Runtime manager for external dependencies (JavaScript runtimes, FFmpeg).

Handles discovery in both development and frozen (PyInstaller) environments.
Supports multiple JS runtimes: Deno, Node.js, and Bun.
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from video_downloader.utils.exceptions import RuntimeNotFoundError
from video_downloader.utils.path_utils import get_bin_path

logger = logging.getLogger(__name__)


class RuntimeManager:
    """
    Manages external runtime dependencies.

    Discovers and configures:
    - JavaScript runtimes (Deno, Node.js, Bun) for yt-dlp extractors
    - FFmpeg (video/audio processing)
    """

    # JS runtimes in priority order: (name, windows_exe, unix_exe)
    JS_RUNTIMES: list[tuple[str, str, str]] = [
        ("deno", "deno.exe", "deno"),
        ("node", "node.exe", "node"),
        ("bun", "bun.exe", "bun"),
    ]

    def __init__(self) -> None:
        """Initialize and discover runtimes."""
        self.js_runtime_path: Path | None = None
        self.js_runtime_name: str | None = None
        # Keep deno_path for backward compatibility
        self.deno_path: Path | None = None
        self.ffmpeg_path: Path | None = None
        self.ffprobe_path: Path | None = None

        self._discover_js_runtime()
        self._discover_ffmpeg()

    def _discover_js_runtime(self) -> None:
        """
        Discover any available JavaScript runtime.

        Tries in order: Deno, Node.js, Bun.
        Checks bundled bin/ directory first, then system PATH.
        """
        bin_path = get_bin_path()

        for name, win_exe, unix_exe in self.JS_RUNTIMES:
            exe_name = win_exe if os.name == "nt" else unix_exe

            # 1. Check bundled/local bin directory
            bundled = bin_path / exe_name
            if bundled.exists():
                self.js_runtime_path = bundled
                self.js_runtime_name = name
                # Keep deno_path for backward compatibility
                if name == "deno":
                    self.deno_path = bundled
                logger.info(f"Using bundled {name}: {bundled}")
                return

            # 2. Check system PATH
            system_path = shutil.which(exe_name.replace(".exe", ""))
            if system_path:
                self.js_runtime_path = Path(system_path)
                self.js_runtime_name = name
                if name == "deno":
                    self.deno_path = Path(system_path)
                logger.info(f"Using system {name}: {system_path}")
                return

        # No JS runtime found - warn but don't crash
        logger.warning(
            "No JavaScript runtime found (Deno, Node.js, or Bun). "
            "Some extractors may not work. "
            "Recommended: Install Deno from https://deno.com/"
        )

    def _discover_ffmpeg(self) -> None:
        """Discover FFmpeg and FFprobe."""
        bin_path = get_bin_path()

        # 1. Check bundled/local bin directory
        bundled_ffmpeg = bin_path / "ffmpeg.exe"
        bundled_ffprobe = bin_path / "ffprobe.exe"

        if bundled_ffmpeg.exists():
            self.ffmpeg_path = bundled_ffmpeg
            logger.info(f"Using bundled FFmpeg: {bundled_ffmpeg}")
        else:
            # 2. Check system PATH
            system_ffmpeg = shutil.which("ffmpeg")
            if system_ffmpeg:
                self.ffmpeg_path = Path(system_ffmpeg)
                logger.info(f"Using system FFmpeg: {system_ffmpeg}")
            else:
                raise RuntimeNotFoundError(
                    "ffmpeg",
                    "FFmpeg not found. Required for video processing. "
                    "Download from: https://ffmpeg.org/download.html",
                )

        if bundled_ffprobe.exists():
            self.ffprobe_path = bundled_ffprobe
        else:
            system_ffprobe = shutil.which("ffprobe")
            if system_ffprobe:
                self.ffprobe_path = Path(system_ffprobe)

        # Verify FFmpeg is functional
        self._verify_ffmpeg_version()

    def _verify_ffmpeg_version(self) -> bool:
        """
        Verify FFmpeg is functional by running version check.

        Returns:
            True if FFmpeg responds correctly
        """
        import os

        if not self.ffmpeg_path:
            return False

        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            result = subprocess.run(
                [str(self.ffmpeg_path), "-version"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=creationflags,
            )
            if result.returncode == 0 and "ffmpeg version" in result.stdout.lower():
                logger.info(f"FFmpeg verified: {result.stdout.split(chr(10))[0]}")
                return True
            else:
                logger.warning("FFmpeg found but version check returned unexpected output")
                return True  # Still usable
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg version check timed out - proceeding anyway")
            return True
        except Exception as e:
            logger.warning(f"FFmpeg version check failed: {e}")
            return True  # Assume usable if file exists

    def get_ytdlp_options(self) -> dict[str, Any]:
        """
        Get yt-dlp options configured for discovered runtimes.

        Returns:
            Dictionary of yt-dlp options
        """
        opts: dict[str, Any] = {}

        # Configure JavaScript runtime if available
        # CRITICAL: Python API requires dict format, NOT list format
        # CLI uses: --js-runtimes deno:/path/to/deno
        # API uses: {'deno': {'path': '/path/to/deno'}}
        if self.js_runtime_path and self.js_runtime_path.exists():
            runtime_abs = str(self.js_runtime_path.resolve())
            opts["js_runtimes"] = {self.js_runtime_name: {"path": runtime_abs}}
            logger.debug(f"Configured {self.js_runtime_name} runtime for yt-dlp")
        else:
            # Allow auto-detection if runtime is on PATH
            opts["js_runtimes"] = None

        # Configure FFmpeg location
        if self.ffmpeg_path:
            # Point to directory containing ffmpeg, not the exe itself
            opts["ffmpeg_location"] = str(self.ffmpeg_path.parent.resolve())

        return opts

    def is_js_runtime_available(self) -> bool:
        """Check if any JavaScript runtime is available."""
        return self.js_runtime_path is not None and self.js_runtime_path.exists()

    def is_deno_available(self) -> bool:
        """Check if Deno runtime is available (backward compatibility)."""
        return self.deno_path is not None and self.deno_path.exists()

    def is_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available."""
        return self.ffmpeg_path is not None and self.ffmpeg_path.exists()

    def is_available(self) -> bool:
        """Check if any JS runtime is available (backward compatibility)."""
        return self.is_js_runtime_available()

    def get_js_runtime_version(self) -> str | None:
        """Get version string for the active JavaScript runtime."""
        if not self.is_js_runtime_available():
            return None

        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            result = subprocess.run(
                [str(self.js_runtime_path), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=creationflags,
            )
            if result.returncode == 0:
                version = result.stdout.split("\n")[0].strip()
                return f"{self.js_runtime_name} {version}"
        except Exception as e:
            logger.warning(f"Failed to get {self.js_runtime_name} version: {e}")
        return None

    def get_deno_version(self) -> str | None:
        """Get Deno version string (backward compatibility)."""
        if not self.is_deno_available():
            return None

        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            result = subprocess.run(
                [str(self.deno_path), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=creationflags,
            )
            if result.returncode == 0:
                # First line contains "deno X.X.X"
                return result.stdout.split("\n")[0].strip()
        except Exception as e:
            logger.warning(f"Failed to get Deno version: {e}")

        return None

    def get_ffmpeg_version(self) -> str | None:
        """Get FFmpeg version string."""
        if not self.is_ffmpeg_available():
            return None

        try:
            result = subprocess.run(
                [str(self.ffmpeg_path), "-version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # First line contains version info
                return result.stdout.split("\n")[0].strip()
        except Exception as e:
            logger.warning(f"Failed to get FFmpeg version: {e}")

        return None
