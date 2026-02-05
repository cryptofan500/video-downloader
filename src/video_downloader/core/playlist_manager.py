"""
Playlist management for batch video downloads.

Provides playlist detection, extraction, and progress tracking.
"""

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

import yt_dlp

from video_downloader.core.runtime_manager import RuntimeManager
from video_downloader.utils.constants import ILLEGAL_FILENAME_CHARS

if TYPE_CHECKING:
    from video_downloader.core.downloader import VideoDownloader

logger = logging.getLogger(__name__)


class DownloadStatus(Enum):
    """Status of a playlist item download."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlaylistItem:
    """Individual video in a playlist."""

    index: int
    video_id: str
    title: str
    url: str
    duration: int | None = None
    status: DownloadStatus = DownloadStatus.PENDING
    error_message: str | None = None
    output_path: Path | None = None


@dataclass
class PlaylistInfo:
    """Playlist metadata and items."""

    playlist_id: str
    title: str
    uploader: str
    url: str
    total_count: int
    items: list[PlaylistItem] = field(default_factory=list)
    current_index: int = 0

    @property
    def completed_count(self) -> int:
        """Count of successfully downloaded items."""
        return sum(1 for item in self.items if item.status == DownloadStatus.COMPLETE)

    @property
    def failed_count(self) -> int:
        """Count of failed downloads."""
        return sum(1 for item in self.items if item.status == DownloadStatus.FAILED)


class PlaylistManager:
    """
    Manages playlist detection and batch downloads.
    """

    # URL patterns that indicate playlists
    PLAYLIST_PATTERNS = [
        r"youtube\.com/playlist\?list=",
        r"youtube\.com/watch\?.*&list=",
        r"youtu\.be/.*\?list=",
    ]

    # YouTube Mix playlist prefixes - these are INFINITE and must be limited
    MIX_PREFIXES = ("RD", "RDAMVM", "RDCMUC", "RDEM", "RDMM", "RDQM", "RDVM")

    # Default limit for Mix playlists (prevent infinite download)
    MIX_PLAYLIST_LIMIT = 25

    def __init__(self, runtime_manager: RuntimeManager) -> None:
        """
        Initialize playlist manager.

        Args:
            runtime_manager: RuntimeManager for yt-dlp configuration
        """
        self.runtime_manager = runtime_manager

    def is_playlist_url(self, url: str) -> bool:
        """
        Check if URL points to a playlist.

        Args:
            url: URL to check

        Returns:
            True if URL is a playlist
        """
        return any(re.search(pattern, url) for pattern in self.PLAYLIST_PATTERNS)

    def is_mix_playlist(self, url: str) -> bool:
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

    def get_safe_download_options(self, url: str) -> dict[str, Any]:
        """
        Get yt-dlp options with safe defaults for URL type.

        Automatically detects Mix playlists and applies limits.

        Args:
            url: URL to download

        Returns:
            dict of yt-dlp options
        """
        opts = self.runtime_manager.get_ytdlp_options()

        if self.is_mix_playlist(url):
            # Mix playlists: default to single video only
            # User can override with explicit playlist download request
            opts["noplaylist"] = True
            logger.info(
                f"Detected Mix playlist - downloading single video only. "
                f"Use playlist mode to download up to {self.MIX_PLAYLIST_LIMIT} tracks."
            )

        return opts

    def get_mix_playlist_options(self, url: str, limit: int | None = None) -> dict[str, Any]:
        """
        Get options for intentionally downloading from a Mix playlist.

        Args:
            url: Mix playlist URL
            limit: Max videos to download (default: MIX_PLAYLIST_LIMIT)

        Returns:
            dict of yt-dlp options with playlist limit
        """
        opts = self.runtime_manager.get_ytdlp_options()
        opts["noplaylist"] = False
        opts["playlistend"] = limit or self.MIX_PLAYLIST_LIMIT
        opts["ignoreerrors"] = True  # Skip unavailable videos
        return opts

    def extract_playlist_info(self, url: str) -> PlaylistInfo | None:
        """
        Extract playlist metadata without downloading.

        Args:
            url: Playlist URL

        Returns:
            PlaylistInfo or None if not a playlist
        """
        ydl_opts = {
            **self.runtime_manager.get_ytdlp_options(),
            "extract_flat": True,  # Don't download, just get info
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info:
                    return None

                # Check if it's actually a playlist
                if "entries" not in info:
                    return None

                entries = list(info["entries"])

                items = []
                for i, entry in enumerate(entries):
                    if entry is None:  # Unavailable video
                        continue

                    items.append(
                        PlaylistItem(
                            index=i,
                            video_id=entry.get("id", ""),
                            title=entry.get("title", f"Video {i + 1}"),
                            url=entry.get("url") or entry.get("webpage_url", ""),
                            duration=entry.get("duration"),
                        )
                    )

                return PlaylistInfo(
                    playlist_id=info.get("id", ""),
                    title=info.get("title", "Unknown Playlist"),
                    uploader=info.get("uploader", "Unknown"),
                    url=url,
                    total_count=len(items),
                    items=items,
                )

        except Exception as e:
            logger.error(f"Failed to extract playlist info: {e}")
            return None

    def download_playlist(
        self,
        playlist: PlaylistInfo,
        output_dir: Path,
        downloader: "VideoDownloader",
        quality: str,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        audio_only: bool = False,
    ) -> dict[str, Any]:
        """
        Download all videos in a playlist.

        Args:
            playlist: PlaylistInfo with items to download
            output_dir: Directory for downloads
            downloader: VideoDownloader instance
            quality: Quality preset
            progress_callback: Callback for progress updates
            audio_only: Download audio only

        Returns:
            Results dictionary with counts and item statuses
        """
        results: dict[str, Any] = {
            "completed": 0,
            "failed": 0,
            "skipped": 0,
            "total": playlist.total_count,
        }

        # Create playlist subfolder
        playlist_dir = output_dir / self._sanitize_dirname(playlist.title)
        playlist_dir.mkdir(parents=True, exist_ok=True)

        for item in playlist.items:
            if downloader._cancelled:
                item.status = DownloadStatus.SKIPPED
                results["skipped"] += 1
                continue

            playlist.current_index = item.index
            item.status = DownloadStatus.DOWNLOADING

            # Notify progress
            if progress_callback:
                progress_callback(
                    {
                        "type": "playlist_item_start",
                        "index": item.index,
                        "total": playlist.total_count,
                        "title": item.title,
                        "playlist_title": playlist.title,
                    }
                )

            try:
                success = downloader.download(
                    item.url,
                    playlist_dir,
                    progress_callback,
                    quality,
                    audio_only,
                )

                if success:
                    item.status = DownloadStatus.COMPLETE
                    results["completed"] += 1
                else:
                    item.status = DownloadStatus.FAILED
                    results["failed"] += 1

            except Exception as e:
                item.status = DownloadStatus.FAILED
                item.error_message = str(e)
                results["failed"] += 1
                logger.error(f"Failed to download {item.title}: {e}")

            # Notify item complete
            if progress_callback:
                progress_callback(
                    {
                        "type": "playlist_item_complete",
                        "index": item.index,
                        "total": playlist.total_count,
                        "status": item.status.value,
                        "completed": results["completed"],
                        "failed": results["failed"],
                    }
                )

        return results

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize string for use as filename."""
        # Remove/replace illegal characters
        for char in ILLEGAL_FILENAME_CHARS:
            name = name.replace(char, "_")

        # Limit length
        return name[:100].strip(". ")

    def _sanitize_dirname(self, name: str) -> str:
        """Sanitize string for use as directory name."""
        return self._sanitize_filename(name)
