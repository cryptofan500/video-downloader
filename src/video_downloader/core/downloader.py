"""
Core video downloader using yt-dlp.

Provides video downloading functionality with progress callbacks and error handling.
"""

import logging
import os
import random
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yt_dlp

from video_downloader.core.runtime_manager import RuntimeManager
from video_downloader.utils.config import AppConfig
from video_downloader.utils.constants import (
    AUDIO_FORMATS,
    VIDEO_QUALITIES,
    get_matching_user_agent,
    get_random_user_agent,
)
from video_downloader.utils.exceptions import DownloadError, NetworkError

logger = logging.getLogger(__name__)


class VideoDownloader:
    """
    Main video downloader using yt-dlp with Deno runtime.

    Supports progress callbacks and proper error handling.
    """

    # YouTube Mix playlist prefixes - these are INFINITE and must be limited
    MIX_PREFIXES = ("RD", "RDAMVM", "RDCMUC", "RDEM", "RDMM", "RDQM", "RDVM")

    # Complete list of supported browsers in PRIORITY ORDER
    SUPPORTED_BROWSERS: tuple[str, ...] = (
        "chrome",
        "edge",
        "brave",
        "opera",
        "vivaldi",
        "chromium",
        "whale",
        "firefox",
        "safari",
    )

    # Browser profile paths for existence checking (Windows + Linux)
    BROWSER_PROFILE_PATHS: dict[str, list[Path]] = {
        "firefox": [
            Path.home() / "AppData/Roaming/Mozilla/Firefox/Profiles",
            Path.home() / ".mozilla/firefox",
        ],
        "chrome": [
            Path.home() / "AppData/Local/Google/Chrome/User Data",
            Path.home() / ".config/google-chrome",
        ],
        "edge": [
            Path.home() / "AppData/Local/Microsoft/Edge/User Data",
        ],
        "brave": [
            Path.home() / "AppData/Local/BraveSoftware/Brave-Browser/User Data",
            Path.home() / ".config/BraveSoftware/Brave-Browser",
        ],
        "opera": [
            Path.home() / "AppData/Roaming/Opera Software/Opera Stable",
            Path.home() / ".config/opera",
        ],
        "vivaldi": [
            Path.home() / "AppData/Local/Vivaldi/User Data",
            Path.home() / ".config/vivaldi",
        ],
        "chromium": [
            Path.home() / "AppData/Local/Chromium/User Data",
            Path.home() / ".config/chromium",
        ],
        "whale": [
            Path.home() / "AppData/Local/Naver/Naver Whale/User Data",
        ],
    }

    # Browser process names for running detection (Windows)
    BROWSER_PROCESSES: dict[str, str] = {
        "chrome": "chrome.exe",
        "edge": "msedge.exe",
        "brave": "brave.exe",
        "opera": "opera.exe",
        "vivaldi": "vivaldi.exe",
        "chromium": "chromium.exe",
        "whale": "whale.exe",
    }

    def __init__(self, runtime_manager: RuntimeManager, config: AppConfig) -> None:
        """
        Initialize downloader.

        Args:
            runtime_manager: RuntimeManager instance for Deno configuration
            config: Application configuration
        """
        self.runtime_manager = runtime_manager
        self.config = config
        self._cancelled = False
        self._fallback_browsers: list[str] = []  # Store fallback browsers for retry
        self._selected_browser: str | None = None  # Track selected browser for User-Agent matching

    def _is_mix_playlist(self, url: str) -> bool:
        """
        Check if URL is a YouTube Mix (Radio) playlist.

        Mix playlists are dynamically generated and effectively infinite.
        They require special handling to prevent endless downloads.

        Args:
            url: URL to check

        Returns:
            True if URL is a Mix playlist
        """
        try:
            query = parse_qs(urlparse(url).query)
            if "list" not in query:
                return False
            playlist_id = query["list"][0]
            return any(playlist_id.startswith(prefix) for prefix in self.MIX_PREFIXES)
        except Exception:
            return False

    def _is_browser_installed(self, browser: str) -> bool:
        """
        Check if browser appears to be installed by checking profile paths.

        Args:
            browser: Browser name to check

        Returns:
            True if browser profile directory exists
        """
        if browser not in self.BROWSER_PROFILE_PATHS:
            # For unknown browsers (safari), assume installed and let yt-dlp handle
            return True

        for profile_path in self.BROWSER_PROFILE_PATHS[browser]:
            if profile_path.exists():
                return True
        return False

    def _is_browser_running(self, browser: str) -> bool:
        """
        Check if a Chromium-based browser is running (has database lock).

        Firefox and Safari don't lock their databases, so always return False.

        Args:
            browser: Browser name to check

        Returns:
            True if browser is running and would have locked cookies
        """
        # Firefox and Safari don't lock their databases
        if browser in ("firefox", "safari"):
            return False

        process_name = self.BROWSER_PROCESSES.get(browser)
        if not process_name:
            return False

        # Windows: check tasklist
        if os.name == "nt":
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                return process_name.lower() in result.stdout.lower()
            except Exception:
                return False
        else:
            # Linux/macOS: use pgrep
            try:
                unix_name = process_name.replace(".exe", "")
                result = subprocess.run(
                    ["pgrep", "-x", unix_name],
                    capture_output=True,
                    timeout=5,
                )
                return result.returncode == 0
            except Exception:
                return False

    def _get_available_browsers(self) -> list[str]:
        """
        Get list of browsers that are installed AND not locked.

        Returns browsers in priority order (Firefox first, then others).

        Returns:
            List of available browser names
        """
        available = []
        locked_browsers = []

        for browser in self.SUPPORTED_BROWSERS:
            if not self._is_browser_installed(browser):
                logger.debug(f"Browser not installed: {browser}")
                continue

            if self._is_browser_running(browser):
                locked_browsers.append(browser)
                logger.debug(f"Browser running (locked): {browser}")
                continue

            available.append(browser)

        if locked_browsers:
            logger.warning(
                f"Browsers with locked cookies (close for better auth): {', '.join(locked_browsers)}"
            )

        return available

    def _find_cookies_file(self) -> Path | None:
        """
        Search for manual cookies.txt file in common locations.

        Returns:
            Path to cookies.txt if found and valid, None otherwise
        """
        from video_downloader.utils.path_utils import get_application_path
        from video_downloader.utils.user_dirs import get_downloads_folder

        search_locations = [
            get_application_path() / "cookies.txt",
            Path.home() / "cookies.txt",
            get_downloads_folder() / "cookies.txt",
        ]

        for location in search_locations:
            if location.exists():
                try:
                    with location.open(encoding="utf-8") as f:
                        first_line = f.readline().strip().lower()
                        # Validate it's a Netscape cookie file
                        if "cookie" in first_line or first_line.startswith("#"):
                            logger.debug(f"Found valid cookies.txt: {location}")
                            return location
                except Exception:
                    continue

        return None

    def _configure_browser_cookies(self, ydl_opts: dict[str, Any]) -> dict[str, Any]:
        """
        Configure browser cookies with intelligent fallback.

        Priority:
        1. Available unlocked browsers (Firefox first - no locking issues)
        2. Manual cookies.txt file
        3. No cookies (anonymous - some videos may fail)

        Args:
            ydl_opts: Current yt-dlp options

        Returns:
            Updated options with browser cookie configuration
        """
        available_browsers = self._get_available_browsers()

        # Try available browsers in priority order
        if available_browsers:
            browser = available_browsers[0]
            ydl_opts["cookiesfrombrowser"] = (browser, None, None, None)
            logger.info(f"Using {browser} cookies for authentication")

            # Store selected browser for User-Agent matching
            self._selected_browser = browser
            # Store fallback browsers for retry logic
            self._fallback_browsers = available_browsers[1:]
            return ydl_opts

        # Fallback: Check for manual cookies.txt
        cookies_file = self._find_cookies_file()
        if cookies_file:
            ydl_opts["cookiefile"] = str(cookies_file)
            logger.info(f"Using manual cookies file: {cookies_file}")
            if "cookiesfrombrowser" in ydl_opts:
                del ydl_opts["cookiesfrombrowser"]
            return ydl_opts

        # No cookies available
        logger.warning(
            "No browser cookies available. Some videos may require authentication. "
            "Try: (1) Close your browser and retry, (2) Use Firefox, "
            "(3) Export cookies to cookies.txt"
        )
        if "cookiesfrombrowser" in ydl_opts:
            del ydl_opts["cookiesfrombrowser"]
        return ydl_opts

    def _build_output_template(self, output_dir: Path, audio_format: str | None = None) -> str:
        """
        Build safe output template for yt-dlp.

        Uses yt-dlp's built-in sanitization instead of manual filename generation.
        Always uses %(ext)s to let yt-dlp handle extensions properly, especially
        when postprocessors (like ExtractAudio) change the file format.

        Args:
            output_dir: Directory for output files
            audio_format: Unused, kept for API compatibility

        Returns:
            Output template string for yt-dlp
        """
        # Always use %(ext)s - yt-dlp handles extension changes from postprocessors
        # This prevents double extensions like .flac.flac when ExtractAudio runs
        template = str(output_dir / "%(title).100s_%(id)s.%(ext)s")

        return template

    def _get_format_config(
        self,
        quality: str,
        audio_only: bool = False,
    ) -> dict[str, Any]:
        """
        Build format configuration for yt-dlp.

        Args:
            quality: Quality preset or audio format (mp3, wav, flac, best, 1080p, etc.)
            audio_only: Force audio-only download

        Returns:
            Dictionary with format, postprocessors, and merge settings
        """
        config: dict[str, Any] = {
            "format": "bestvideo+bestaudio/best",
            "postprocessors": [],
            "merge_output_format": "mp4",
        }

        # Native quality: no re-encoding, no postprocessors
        quality_lower = quality.lower()
        if quality_lower == "native":
            return {
                "format": "bestvideo+bestaudio/best",
                "merge_output_format": "mkv",
                "postprocessors": [],
            }

        # Check if audio format requested
        if audio_only or quality_lower in AUDIO_FORMATS:
            audio_config = AUDIO_FORMATS.get(quality_lower, AUDIO_FORMATS["mp3"])

            config["format"] = "bestaudio/best"
            config["merge_output_format"] = None  # No video merge
            config["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_config["codec"],
                    "preferredquality": audio_config["quality"],
                }
            ]

            # Add metadata
            config["postprocessors"].append(
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                }
            )

            # Embed thumbnail only for formats that support it
            # Supported: mp3, mkv/mka, ogg/opus/flac, m4a/mp4/m4v/mov
            # NOT supported: wav
            thumbnail_supported_codecs = {"mp3", "opus", "flac", "aac", "m4a"}
            if audio_config["codec"] in thumbnail_supported_codecs:
                config["postprocessors"].append(
                    {
                        "key": "EmbedThumbnail",
                    }
                )
                config["writethumbnail"] = True

        else:
            # Video quality
            config["format"] = VIDEO_QUALITIES.get(quality_lower, VIDEO_QUALITIES["best"])
            config["merge_output_format"] = "mp4"

            # Add metadata to video
            config["postprocessors"].append(
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                }
            )

        return config

    def download(
        self,
        url: str,
        output_path: Path,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        quality: str = "best",
        audio_only: bool = False,
    ) -> bool:
        """
        Download video with progress callbacks.

        Args:
            url: Video URL to download
            output_path: Output directory (NOT file path - let yt-dlp handle filename)
            progress_callback: Optional callback for progress updates
            quality: Video quality or audio format (best, 1080p, 720p, mp3, wav, flac)
            audio_only: Download audio only (deprecated - use quality='mp3' instead)

        Returns:
            True if download succeeded, False otherwise

        Raises:
            DownloadError: If download fails with specific error
        """
        self._cancelled = False

        # Ensure output_path is a directory
        if output_path.suffix:
            # If a file path was passed, use its parent directory
            output_dir = output_path.parent
        else:
            output_dir = output_path

        output_dir.mkdir(parents=True, exist_ok=True)

        # Get format configuration
        format_config = self._get_format_config(quality, audio_only)

        # Determine audio format for template
        quality_lower = quality.lower()
        audio_format = None
        if audio_only or quality_lower in AUDIO_FORMATS:
            audio_format = AUDIO_FORMATS.get(quality_lower, AUDIO_FORMATS["mp3"])["codec"]

        # Build yt-dlp options
        ydl_opts: dict[str, Any] = {
            **self.runtime_manager.get_ytdlp_options(),
            "outtmpl": self._build_output_template(output_dir, audio_format),
            "restrictfilenames": True,  # CRITICAL: Makes filenames Windows-safe
            "windowsfilenames": True,  # CRITICAL: Extra Windows safety
            "format": format_config["format"],
            "postprocessors": format_config["postprocessors"],
            "ignoreerrors": False,
            "no_warnings": False,
            "quiet": False,
            "no_color": True,
            "retries": 10,
            "fragment_retries": "infinite",
            "socket_timeout": 15,
            "file_access_retries": 3,
            "noplaylist": True,  # Default: download single video for safety
            # Enable remote EJS components for YouTube challenge solving
            "remote_components": ["ejs:github"],
        }

        # Configure cookies from available browsers (also sets _selected_browser)
        ydl_opts = self._configure_browser_cookies(ydl_opts)

        # Set User-Agent matching the cookie source browser (helps avoid detection)
        if self._selected_browser:
            user_agent = get_matching_user_agent(self._selected_browser)
        else:
            user_agent = get_random_user_agent()
        ydl_opts["http_headers"] = {"User-Agent": user_agent}
        logger.debug(f"Using User-Agent for {self._selected_browser or 'anonymous'}")

        # Detect Mix playlists and log warning
        if self._is_mix_playlist(url):
            logger.info(
                "Detected YouTube Mix playlist - downloading single video only. "
                "Mix playlists are dynamically generated and effectively infinite."
            )

        # Only set merge_output_format for video
        if format_config.get("merge_output_format"):
            ydl_opts["merge_output_format"] = format_config["merge_output_format"]

        # Add thumbnail writing for audio
        if format_config.get("writethumbnail"):
            ydl_opts["writethumbnail"] = True

        # Add progress hook if callback provided
        if progress_callback:
            ydl_opts["progress_hooks"] = [self._create_progress_hook(progress_callback)]

        try:
            logger.info(f"Starting download: {url}")
            logger.info(f"Output directory: {output_dir}")
            logger.info(f"Quality: {quality} (format: {format_config['format']})")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                retcode = ydl.download([url])

            if self._cancelled:
                logger.info("Download cancelled by user")
                return False

            if retcode != 0:
                logger.error(f"yt-dlp returned non-zero exit code: {retcode}")
                raise DownloadError(f"Download failed (yt-dlp exit code {retcode})")

            logger.info("Download complete")
            return True

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.error(f"Download failed: {error_msg}")

            # Categorize errors
            if "unable to download" in error_msg.lower():
                raise NetworkError(f"Network error: {error_msg}") from e
            elif "video unavailable" in error_msg.lower():
                raise DownloadError(f"Video unavailable: {error_msg}") from e
            else:
                raise DownloadError(f"Download failed: {error_msg}") from e

        except KeyboardInterrupt:
            logger.info("Download interrupted by user")
            self._cancelled = True
            return False

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise DownloadError(f"Unexpected error: {e}") from e

    def _create_progress_hook(
        self, callback: Callable[[dict[str, Any]], None]
    ) -> Callable[[dict[str, Any]], None]:
        """
        Create progress hook for yt-dlp.

        Args:
            callback: User-provided progress callback

        Returns:
            Progress hook function for yt-dlp
        """

        def hook(d: dict[str, Any]) -> None:
            """Progress hook called by yt-dlp."""
            if self._cancelled:
                raise KeyboardInterrupt("Download cancelled")

            try:
                if d["status"] == "downloading":
                    progress_info = {
                        "status": "downloading",
                        "percentage": d.get("_percent_str", "0%").strip(),
                        "speed": d.get("_speed_str", "N/A").strip(),
                        "eta": d.get("_eta_str", "N/A").strip(),
                        "downloaded_bytes": d.get("downloaded_bytes", 0),
                        "total_bytes": d.get("total_bytes") or d.get("total_bytes_estimate", 0),
                    }
                    callback(progress_info)

                elif d["status"] == "finished":
                    callback(
                        {
                            "status": "complete",
                            "filename": d.get(
                                "filename", str(d.get("info_dict", {}).get("filepath", ""))
                            ),
                        }
                    )

                elif d["status"] == "error":
                    callback(
                        {
                            "status": "error",
                            "message": "Download error occurred",
                        }
                    )

            except Exception as e:
                logger.error(f"Progress callback error: {e}")

        return hook

    def cancel(self) -> None:
        """Cancel ongoing download."""
        self._cancelled = True
        logger.info("Download cancellation requested")

    def _calculate_backoff(
        self, attempt: int, base_delay: float = 2.0, max_delay: float = 30.0
    ) -> float:
        """
        Calculate exponential backoff delay with jitter.

        Args:
            attempt: Current attempt number (0-indexed)
            base_delay: Base delay in seconds
            max_delay: Maximum delay cap

        Returns:
            Delay in seconds
        """
        delay = min(base_delay * (2**attempt), max_delay)
        # Add jitter (0-50% of delay) to prevent thundering herd
        jitter = random.uniform(0, delay * 0.5)
        return delay + jitter

    def _classify_error(self, error_msg: str) -> tuple[bool, str]:
        """
        Classify an error as recoverable or fatal.

        Args:
            error_msg: Error message string

        Returns:
            Tuple of (is_recoverable, error_category)
        """
        error_lower = error_msg.lower()

        # Fatal errors - don't retry
        if any(x in error_lower for x in ["unavailable", "private", "deleted", "removed"]):
            return False, "video_unavailable"
        if any(x in error_lower for x in ["copyright", "blocked", "not available in your country"]):
            return False, "geo_blocked"
        if "drm" in error_lower or "protected" in error_lower:
            return False, "drm_protected"

        # Recoverable errors - retry with different strategy
        if any(x in error_lower for x in ["403", "forbidden"]):
            return True, "forbidden"
        if any(x in error_lower for x in ["bot", "sign in", "confirm you"]):
            return True, "bot_detection"
        if any(x in error_lower for x in ["429", "too many", "rate limit"]):
            return True, "rate_limited"
        if any(x in error_lower for x in ["timeout", "timed out", "connection"]):
            return True, "network"

        # Unknown error - try to recover
        return True, "unknown"

    def download_with_retry(
        self,
        url: str,
        output_path: Path,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        quality: str = "best",
        audio_only: bool = False,
        max_retries: int = 3,
    ) -> bool:
        """
        Download with automatic retry and exponential backoff.

        Args:
            url: Video URL to download
            output_path: Output directory
            progress_callback: Optional progress callback
            quality: Quality preset
            audio_only: Audio-only download
            max_retries: Maximum number of retry attempts

        Returns:
            True if download succeeded

        Raises:
            DownloadError: If all retries fail
        """
        self._cancelled = False
        last_error: Exception | None = None

        for attempt in range(max_retries):
            if self._cancelled:
                logger.info("Download cancelled by user")
                return False

            logger.info(f"Attempt {attempt + 1}/{max_retries}")

            # Apply backoff delay (except for first attempt)
            if attempt > 0:
                delay = self._calculate_backoff(attempt - 1)
                logger.info(f"Waiting {delay:.1f}s before retry...")
                time.sleep(delay)

            try:
                success = self.download(
                    url=url,
                    output_path=output_path,
                    progress_callback=progress_callback,
                    quality=quality,
                    audio_only=audio_only,
                )
                if success:
                    return True

                # download() returned False (cancelled)
                return False

            except DownloadError as e:
                last_error = e
                error_msg = str(e)
                is_recoverable, error_category = self._classify_error(error_msg)

                if not is_recoverable:
                    logger.error(f"Fatal error ({error_category}): {error_msg}")
                    raise

                logger.warning(
                    f"Recoverable error ({error_category}) on attempt "
                    f"{attempt + 1}: {error_msg[:100]}..."
                )
                continue

            except KeyboardInterrupt:
                logger.info("Download interrupted by user")
                self._cancelled = True
                return False

            except Exception as e:
                last_error = e
                logger.warning(f"Unexpected error on attempt {attempt + 1}: {e}")
                continue

        # All retries exhausted
        raise DownloadError(
            f"All {max_retries} download attempts failed. Last error: {last_error}"
        ) from last_error
