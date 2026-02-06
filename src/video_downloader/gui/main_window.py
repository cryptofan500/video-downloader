"""
Main application window.

Provides GUI for video downloading with progress tracking and diagnostics.
"""

import logging
import queue
from pathlib import Path
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from video_downloader.core.download_manager import ThreadedDownloadManager
from video_downloader.core.runtime_manager import RuntimeManager
from video_downloader.gui.diagnostics_pane import DiagnosticsPane
from video_downloader.gui.widgets import URLEntry
from video_downloader.utils.config import AppConfig
from video_downloader.utils.exceptions import RuntimeNotFoundError, ValidationError
from video_downloader.utils.ffmpeg_manager import FFmpegManager
from video_downloader.utils.validators import URLValidator

logger = logging.getLogger(__name__)


class MainWindow(ctk.CTk):
    """
    Main application window with download interface.

    Provides URL input, quality selection, progress tracking, and diagnostics.
    """

    def __init__(self, config: AppConfig):
        """
        Initialize main window.

        Args:
            config: Application configuration
        """
        super().__init__()

        self.config = config
        self.title(config.title)
        self.geometry("900x700")
        self.minsize(700, 500)

        # Initialize managers
        try:
            self.runtime_manager = RuntimeManager()
            self.ffmpeg_manager = FFmpegManager()
        except RuntimeNotFoundError as e:
            logger.error(f"Runtime initialization failed: {e}")
            # Will show error in diagnostics pane
            self.runtime_manager = None  # type: ignore
            self.ffmpeg_manager = None  # type: ignore

        # Configure grid
        self.grid_rowconfigure(6, weight=1)  # Diagnostics pane expands
        self.grid_columnconfigure(0, weight=1)

        # Create download manager
        if self.runtime_manager:
            self.download_manager = ThreadedDownloadManager(
                self.runtime_manager, self.config, self._handle_download_event
            )
        else:
            self.download_manager = None  # type: ignore

        # Create UI
        self._create_widgets()

        # Start queue monitor
        self.after(100, self._process_queue)

        # Log system info
        self._log_system_info()

    def _create_widgets(self) -> None:
        """Create all GUI widgets."""
        # Title
        title_label = ctk.CTkLabel(self, text=self.config.title, font=("Helvetica", 24, "bold"))
        title_label.grid(row=0, column=0, pady=(20, 10), sticky="ew")

        # URL input section
        url_frame = ctk.CTkFrame(self)
        url_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        url_frame.grid_columnconfigure(0, weight=1)

        url_label = ctk.CTkLabel(url_frame, text="Video URL:", font=("Helvetica", 12))
        url_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        self.url_entry = URLEntry(
            url_frame,
            placeholder_text="Enter YouTube, Vimeo, or other video URL",
            font=("Helvetica", 12),
        )
        self.url_entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        # Quality selection
        quality_frame = ctk.CTkFrame(self)
        quality_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        quality_label = ctk.CTkLabel(quality_frame, text="Quality:", font=("Helvetica", 12))
        quality_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.quality_var = ctk.StringVar(value="best")
        self.quality_dropdown = ctk.CTkOptionMenu(
            quality_frame,
            values=["best", "native", "2160p", "1080p", "720p", "480p", "mp3", "wav", "flac"],
            variable=self.quality_var,
        )
        self.quality_dropdown.grid(row=0, column=1, padx=10, pady=10)

        # Output path selection
        path_label = ctk.CTkLabel(quality_frame, text="Output:", font=("Helvetica", 12))
        path_label.grid(row=0, column=2, padx=(30, 5), pady=10, sticky="w")

        self.output_path = self.config.download.output_dir
        self.path_button = ctk.CTkButton(
            quality_frame, text=str(self.output_path), command=self._select_output_path, width=200
        )
        self.path_button.grid(row=0, column=3, padx=5, pady=10)

        # Download button
        self.download_btn = ctk.CTkButton(
            self,
            text="Download",
            command=self._start_download,
            font=("Helvetica", 14, "bold"),
            height=40,
        )
        self.download_btn.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        # Progress section
        progress_frame = ctk.CTkFrame(self)
        progress_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(progress_frame, text="Ready", font=("Helvetica", 11))
        self.progress_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.progress_bar.set(0)

        # Cancel button (initially disabled)
        self.cancel_btn = ctk.CTkButton(
            progress_frame,
            text="Cancel",
            command=self._cancel_download,
            state="disabled",
            width=100,
            fg_color="gray",
        )
        self.cancel_btn.grid(row=1, column=1, padx=10, pady=(0, 10))

        # Diagnostics pane
        self.diagnostics = DiagnosticsPane(self)
        self.diagnostics.grid(row=6, column=0, padx=20, pady=(10, 20), sticky="nsew")

    def _select_output_path(self) -> None:
        """Open folder selection dialog."""
        folder = filedialog.askdirectory(
            title="Select Output Folder", initialdir=str(self.output_path)
        )
        if folder:
            self.output_path = Path(folder)
            self.path_button.configure(text=str(self.output_path))
            self.diagnostics.log(f"Output path changed to: {self.output_path}")

    def _log_system_info(self) -> None:
        """Log system information to diagnostics pane."""
        self.diagnostics.log("=== System Information ===")
        self.diagnostics.log(f"Application: {self.config.title} v{self.config.version}")

        if self.runtime_manager and self.runtime_manager.is_available():
            self.diagnostics.log(f"Deno: {self.runtime_manager.deno_path}", "SUCCESS")
        else:
            self.diagnostics.log("Deno: NOT FOUND", "ERROR")

        if self.ffmpeg_manager and self.ffmpeg_manager.is_available():
            success, version_str, _ = self.ffmpeg_manager.check_version()
            if success:
                self.diagnostics.log(f"FFmpeg: {version_str}", "SUCCESS")
            else:
                self.diagnostics.log("FFmpeg: Version check failed", "WARNING")
        else:
            self.diagnostics.log("FFmpeg: NOT FOUND", "ERROR")

        self.diagnostics.log(f"Output directory: {self.config.download.output_dir}")
        self.diagnostics.log("=========================")

    def _start_download(self) -> None:
        """Start download in background thread."""
        if not self.download_manager:
            self.diagnostics.log("Cannot download: Runtime not initialized", "ERROR")
            return

        url = self.url_entry.get().strip()
        if not url:
            self.diagnostics.log("Please enter a URL", "WARNING")
            return

        # Validate URL
        try:
            URLValidator.validate(url)
        except ValidationError as e:
            self.diagnostics.log(str(e), "ERROR")
            return

        # Determine quality
        quality = self.quality_var.get()
        audio_only = quality in ["mp3", "wav", "flac", "audio"]

        # Let yt-dlp handle filename sanitization - just pass the directory
        output_path = self.output_path

        # Disable buttons and start download
        self.download_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal", fg_color=["#3B8ED0", "#1F6AA5"])
        self.progress_bar.set(0)
        self.diagnostics.log(f"Starting download: {url}")

        self.download_manager.download_in_thread(url, output_path, quality, audio_only)

    def _cancel_download(self) -> None:
        """Cancel current download."""
        if self.download_manager:
            self.download_manager.cancel_current()
            self.diagnostics.log("Cancelling download...", "WARNING")

    def _handle_download_event(self, event_type: str, data: Any) -> None:
        """
        Handle events from download threads (called via queue processing).

        Args:
            event_type: Event type (status, progress, complete, error)
            data: Event data
        """
        if event_type == "status":
            self.diagnostics.log(data)

        elif event_type == "progress":
            if "percentage" in data:
                # Parse percentage string (e.g., "45.3%")
                try:
                    pct_str = data["percentage"].strip("%")
                    pct = float(pct_str) / 100
                    self.progress_bar.set(pct)

                    speed = data.get("speed", "N/A")
                    eta = data.get("eta", "N/A")
                    self.progress_label.configure(
                        text=f"Downloading: {data['percentage']} | Speed: {speed} | ETA: {eta}"
                    )
                except ValueError:
                    pass

        elif event_type == "complete":
            self.progress_bar.set(1.0)
            self.diagnostics.log(f"Download complete: {data}", "SUCCESS")
            self.progress_label.configure(text="Complete!")
            self.download_btn.configure(state="normal")
            self.cancel_btn.configure(state="disabled", fg_color="gray")

        elif event_type == "error":
            self.diagnostics.log(f"Error: {data}", "ERROR")
            self.progress_label.configure(text="Error occurred")
            self.download_btn.configure(state="normal")
            self.cancel_btn.configure(state="disabled", fg_color="gray")

    def _process_queue(self) -> None:
        """Process messages from worker threads (called periodically)."""
        try:
            while True:
                event_type, data = self.download_manager.message_queue.get_nowait()
                self._handle_download_event(event_type, data)
        except queue.Empty:
            pass
        finally:
            # Schedule next check
            if not self.download_manager or not self.download_manager.shutdown_event.is_set():
                self.after(100, self._process_queue)

    def destroy(self) -> None:
        """Clean shutdown."""
        if self.download_manager:
            self.download_manager.shutdown()
        super().destroy()


def main() -> None:
    """Main entry point for GUI application."""
    # Configure logging so logger calls produce output
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Set appearance
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    # Setup environment paths for external tools
    from video_downloader.utils.path_utils import get_config_path, setup_environment_paths

    setup_environment_paths()

    # Load configuration
    config_path = get_config_path()

    try:
        if config_path.exists():
            config = AppConfig.from_toml(config_path)
        else:
            config = AppConfig.create_default(config_path)
            logger.info(f"Created default configuration: {config_path}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        # Use hardcoded defaults
        from video_downloader.utils.config import DownloadConfig

        config = AppConfig(
            title="Video Downloader",
            version="1.1.0",
            download=DownloadConfig(
                output_dir=Path("downloads"),
                max_concurrent=3,
                timeout=300,
                retry_attempts=3,
                quality="best",
            ),
        )

    # Create and run application
    app = MainWindow(config)
    app.mainloop()


if __name__ == "__main__":
    main()
