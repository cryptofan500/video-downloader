"""
FFmpeg detection and management.

Handles FFmpeg executable detection from bundled location or system PATH.
"""

import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path

from video_downloader.utils.exceptions import RuntimeNotFoundError

logger = logging.getLogger(__name__)


class FFmpegManager:
    """
    Manages FFmpeg executable detection and execution.

    Checks for FFmpeg in bundled location first, then system PATH.
    """

    def __init__(self):
        """Initialize FFmpeg manager and detect executable."""
        self.ffmpeg_path: Path | None = None
        self.ffprobe_path: Path | None = None
        self._detect_ffmpeg()

    def _detect_ffmpeg(self) -> None:
        """
        Detect FFmpeg from bundled location or system PATH.

        Raises:
            RuntimeNotFoundError: If FFmpeg is not found
        """
        # Check bundled location (PyInstaller)
        if getattr(sys, "frozen", False):
            base_path = Path(sys._MEIPASS)  # type: ignore
        else:
            # Development mode: check project bin directory
            base_path = Path(__file__).parent.parent.parent.parent

        # Check bundled FFmpeg
        bundled_ffmpeg = base_path / "bin" / "ffmpeg.exe"
        bundled_ffprobe = base_path / "bin" / "ffprobe.exe"

        if bundled_ffmpeg.exists():
            self.ffmpeg_path = bundled_ffmpeg
            logger.info(f"Using bundled FFmpeg: {bundled_ffmpeg}")

            if bundled_ffprobe.exists():
                self.ffprobe_path = bundled_ffprobe
                logger.info(f"Using bundled FFprobe: {bundled_ffprobe}")

            return

        # Check system PATH
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            self.ffmpeg_path = Path(system_ffmpeg)
            logger.info(f"Using system FFmpeg: {system_ffmpeg}")

            system_ffprobe = shutil.which("ffprobe")
            if system_ffprobe:
                self.ffprobe_path = Path(system_ffprobe)
                logger.info(f"Using system FFprobe: {system_ffprobe}")

            return

        raise RuntimeNotFoundError(
            "ffmpeg",
            "FFmpeg not found. Please install FFmpeg or ensure it's bundled in the 'bin' directory.",
        )

    def check_version(self) -> tuple[bool, str, tuple[int, int, int]]:
        """
        Check FFmpeg version.

        Returns:
            Tuple of (success, version_string, version_tuple)
        """
        if not self.ffmpeg_path:
            return False, "FFmpeg not found", (0, 0, 0)

        try:
            result = subprocess.run(
                [str(self.ffmpeg_path), "-version"],
                capture_output=True,
                text=True,
                timeout=5,
                shell=False,  # CRITICAL: No shell injection
            )

            if result.returncode == 0:
                # Parse version (e.g., "ffmpeg version 4.4.2")
                match = re.search(r"ffmpeg version (\d+)\.(\d+)\.(\d+)", result.stdout)
                if match:
                    version = tuple(map(int, match.groups()))
                    version_str = result.stdout.split("\n")[0]
                    logger.info(f"FFmpeg version: {version_str}")
                    return True, version_str, version

            return False, "Version check failed", (0, 0, 0)

        except subprocess.TimeoutExpired:
            return False, "Version check timed out", (0, 0, 0)
        except Exception as e:
            logger.error(f"FFmpeg version check failed: {e}")
            return False, f"Error: {e}", (0, 0, 0)

    def run_ffmpeg(self, args: list[str], timeout: int = 300) -> tuple[bool, str]:
        """
        Execute FFmpeg with safe subprocess pattern.

        Args:
            args: List of FFmpeg arguments
            timeout: Timeout in seconds

        Returns:
            Tuple of (success, stderr_output)
        """
        if not self.ffmpeg_path:
            return False, "FFmpeg not found"

        cmd = [str(self.ffmpeg_path)] + args

        try:
            result = subprocess.run(
                cmd,
                shell=False,  # CRITICAL: Prevents command injection
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            success = result.returncode == 0
            if not success:
                logger.error(f"FFmpeg failed: {result.stderr}")

            return success, result.stderr

        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg operation timed out after {timeout}s")
            return False, "FFmpeg operation timed out"
        except Exception as e:
            logger.error(f"FFmpeg error: {e}")
            return False, f"FFmpeg error: {e}"

    def is_available(self) -> bool:
        """Check if FFmpeg is available."""
        return self.ffmpeg_path is not None and self.ffmpeg_path.exists()
