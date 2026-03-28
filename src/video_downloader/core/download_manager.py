"""
Threaded download manager for GUI integration.

Manages downloads in background threads with queue-based communication.
"""

import logging
import queue
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from video_downloader.core.downloader import VideoDownloader
from video_downloader.core.runtime_manager import RuntimeManager
from video_downloader.utils.config import AppConfig
from video_downloader.utils.exceptions import DownloadError, NetworkError, ValidationError
from video_downloader.utils.validators import URLValidator

logger = logging.getLogger(__name__)


class ThreadedDownloadManager:
    """
    Manages downloads in background threads with GUI callbacks.

    Uses queue-based communication for thread-safe GUI updates.
    """

    def __init__(
        self,
        runtime_manager: RuntimeManager,
        config: AppConfig,
        update_callback: Callable[[str, Any], None],
    ):
        """
        Initialize download manager.

        Args:
            runtime_manager: RuntimeManager instance
            config: Application configuration
            update_callback: Callback for GUI updates (event_type, data)
        """
        self.runtime_manager = runtime_manager
        self.config = config
        self.update_callback = update_callback
        self.message_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.executor = ThreadPoolExecutor(
            max_workers=config.download.max_concurrent, thread_name_prefix="dl"
        )
        self._active: dict[str, VideoDownloader] = {}
        self._lock = threading.Lock()
        self._last_completed_file: Path | None = None
        self.shutdown_event = threading.Event()

    def download_in_thread(
        self,
        url: str,
        output_path: Path,
        quality: str = "best",
        audio_only: bool = False,
    ) -> str:
        """
        Start download in background thread.

        Args:
            url: Video URL to download
            output_path: Output file path
            quality: Video quality
            audio_only: Download audio only

        Returns:
            task_id: UUID string for tracking this download
        """
        task_id = uuid.uuid4().hex
        self.executor.submit(
            self._download_worker, task_id, url, output_path, quality, audio_only
        )
        return task_id

    def _download_worker(
        self,
        task_id: str,
        url: str,
        output_path: Path,
        quality: str,
        audio_only: bool,
    ) -> None:
        """
        Worker function running in background thread.

        Args:
            task_id: UUID for this download task
            url: Video URL
            output_path: Output path
            quality: Video quality
            audio_only: Audio only flag
        """
        downloader = None
        try:
            # Validate URL
            self._send_update("status", "Validating URL...")
            try:
                validated_url = URLValidator.validate(url)
            except ValidationError as e:
                self._send_update("error", str(e))
                return

            # Ensure output directory exists
            output_path.mkdir(parents=True, exist_ok=True)

            # Create downloader
            downloader = VideoDownloader(self.runtime_manager, self.config)
            with self._lock:
                self._active[task_id] = downloader

            # Progress callback
            def progress_cb(progress_info: dict[str, Any]) -> None:
                self._send_update("progress", progress_info)

            # Start download with automatic strategy escalation
            self._send_update("status", f"Starting download: {url}")

            success = downloader.download_with_retry(
                validated_url, output_path, progress_cb, quality, audio_only
            )

            if success:
                self._send_update("complete", str(output_path))
            else:
                self._send_update("error", "Download failed or was cancelled")

        except NetworkError as e:
            logger.error(f"Network error: {e}")
            self._send_update("error", f"Network error: {e}")

        except DownloadError as e:
            logger.error(f"Download error: {e}")
            self._send_update("error", f"Download error: {e}")

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            self._send_update("error", f"Unexpected error: {e}")

        finally:
            with self._lock:
                self._active.pop(task_id, None)
            if downloader and downloader.last_downloaded_file:
                with self._lock:
                    self._last_completed_file = downloader.last_downloaded_file

    def _send_update(self, event_type: str, data: Any) -> None:
        """
        Send update to GUI thread via queue.

        Args:
            event_type: Type of event (status, progress, complete, error)
            data: Event data
        """
        self.message_queue.put((event_type, data))

    def cancel_current(self) -> None:
        """Cancel all active downloads."""
        with self._lock:
            for downloader in self._active.values():
                downloader.cancel()

    def shutdown(self) -> None:
        """
        Shutdown all worker threads.

        Cancels current downloads and waits for threads to finish.
        """
        self.shutdown_event.set()
        self.cancel_current()
        self.executor.shutdown(wait=True, cancel_futures=True)

        logger.info("Download manager shutdown complete")
