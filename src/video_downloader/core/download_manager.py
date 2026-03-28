"""
Threaded download manager for GUI integration.

Manages downloads in background threads with queue-based communication.
"""

import logging
import queue
import threading
from collections.abc import Callable
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
        self.workers: list[threading.Thread] = []
        self.shutdown_event = threading.Event()
        self.current_downloader: VideoDownloader | None = None

    def download_in_thread(
        self,
        url: str,
        output_path: Path,
        quality: str = "best",
        audio_only: bool = False,
    ) -> None:
        """
        Start download in background thread.

        Args:
            url: Video URL to download
            output_path: Output file path
            quality: Video quality
            audio_only: Download audio only
        """
        worker = threading.Thread(
            target=self._download_worker,
            args=(url, output_path, quality, audio_only),
            daemon=True,
            name=f"DownloadWorker-{url[:30]}",
        )
        self.workers.append(worker)
        worker.start()

    def _download_worker(
        self,
        url: str,
        output_path: Path,
        quality: str,
        audio_only: bool,
    ) -> None:
        """
        Worker function running in background thread.

        Args:
            url: Video URL
            output_path: Output path
            quality: Video quality
            audio_only: Audio only flag
        """
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
            self.current_downloader = VideoDownloader(self.runtime_manager, self.config)

            # Progress callback
            def progress_cb(progress_info: dict[str, Any]) -> None:
                self._send_update("progress", progress_info)

            # Start download with automatic strategy escalation
            self._send_update("status", f"Starting download: {url}")

            success = self.current_downloader.download_with_retry(
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
            self.current_downloader = None

    def _send_update(self, event_type: str, data: Any) -> None:
        """
        Send update to GUI thread via queue.

        Args:
            event_type: Type of event (status, progress, complete, error)
            data: Event data
        """
        self.message_queue.put((event_type, data))

    def cancel_current(self) -> None:
        """Cancel current download."""
        if self.current_downloader:
            self.current_downloader.cancel()

    def shutdown(self) -> None:
        """
        Shutdown all worker threads.

        Cancels current download and waits for threads to finish.
        """
        self.shutdown_event.set()
        self.cancel_current()

        for worker in self.workers:
            worker.join(timeout=2.0)

        logger.info("Download manager shutdown complete")
