"""
PyInstaller runtime hook for Video Downloader.

Configures paths and environment for frozen application.
"""

import os
import sys


def configure_paths() -> None:
    """Configure paths for frozen application."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = sys._MEIPASS
        bin_path = os.path.join(base_path, 'bin')

        # Prepend bin/ to PATH for FFmpeg and Deno
        current_path = os.environ.get('PATH', '')
        os.environ['PATH'] = bin_path + os.pathsep + current_path

        # Set explicit FFmpeg location for yt-dlp
        ffmpeg_exe = os.path.join(bin_path, 'ffmpeg.exe')
        if os.path.exists(ffmpeg_exe):
            os.environ['FFMPEG_BINARY'] = ffmpeg_exe


# Run configuration on import
configure_paths()
