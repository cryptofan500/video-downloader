"""
Transcription module using faster-whisper.

Optional feature - gracefully handles missing dependencies.
"""

import importlib.util

WHISPER_AVAILABLE = importlib.util.find_spec("faster_whisper") is not None


def is_transcription_available() -> bool:
    """Check if transcription dependencies are installed."""
    return WHISPER_AVAILABLE


def get_transcription_service():
    """
    Get transcription service class.

    Returns:
        TranscriptionService class

    Raises:
        ImportError: If faster-whisper is not installed
    """
    if not WHISPER_AVAILABLE:
        raise ImportError(
            "Transcription requires faster-whisper. Install with: pip install faster-whisper"
        )

    from video_downloader.transcription.whisper_backend import TranscriptionService

    return TranscriptionService


__all__ = [
    "is_transcription_available",
    "get_transcription_service",
    "WHISPER_AVAILABLE",
]
