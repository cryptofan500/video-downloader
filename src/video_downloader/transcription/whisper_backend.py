"""
Whisper-based transcription backend.

Uses faster-whisper for CPU-optimized local transcription.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from faster_whisper import WhisperModel

from video_downloader.utils.constants import TRANSCRIPTION_PRESETS

logger = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    """Single segment of transcription."""

    start: float
    end: float
    text: str


@dataclass
class TranscriptResult:
    """Complete transcription result."""

    language: str
    language_probability: float
    duration: float
    segments: list[TranscriptSegment] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        """Get concatenated text from all segments."""
        return " ".join(seg.text for seg in self.segments)


class TranscriptionService:
    """
    CPU-optimized transcription using faster-whisper.

    Presets:
    - fast: tiny.en model, ~1 min per 10 min audio
    - balanced: small.en model, ~4 min per 10 min audio (RECOMMENDED)
    - accurate: medium.en model, ~15 min per 10 min audio
    """

    def __init__(
        self,
        preset: str = "balanced",
        cpu_threads: int = 8,
    ) -> None:
        """
        Initialize transcription service.

        Args:
            preset: Quality preset (fast, balanced, accurate)
            cpu_threads: Number of CPU threads to use
        """
        model_name, compute_type, beam_size = TRANSCRIPTION_PRESETS.get(
            preset, TRANSCRIPTION_PRESETS["balanced"]
        )

        logger.info(f"Loading Whisper model: {model_name} ({compute_type})")

        self.model = WhisperModel(
            model_name,
            device="cpu",
            compute_type=compute_type,
            cpu_threads=cpu_threads,
        )
        self.beam_size = beam_size
        self.preset = preset

    def transcribe(
        self,
        audio_path: Path,
        progress_callback: Callable[[float], None] | None = None,
    ) -> TranscriptResult:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file (any format FFmpeg supports)
            progress_callback: Optional callback with progress 0.0-1.0

        Returns:
            TranscriptResult with segments and metadata
        """
        logger.info(f"Transcribing: {audio_path}")

        segments_iter, info = self.model.transcribe(
            str(audio_path),
            beam_size=self.beam_size,
            vad_filter=True,  # Skip silence for speed
            vad_parameters=dict(
                min_silence_duration_ms=500,
            ),
        )

        # Collect segments with progress
        segments = []
        for segment in segments_iter:
            segments.append(
                TranscriptSegment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip(),
                )
            )

            if progress_callback and info.duration > 0:
                progress = min(segment.end / info.duration, 1.0)
                progress_callback(progress)

        logger.info(f"Transcription complete: {len(segments)} segments")

        return TranscriptResult(
            language=info.language,
            language_probability=info.language_probability,
            duration=info.duration,
            segments=segments,
        )

    def save_transcript(
        self,
        result: TranscriptResult,
        output_path: Path,
        format: str = "txt",
    ) -> Path:
        """
        Save transcript to file.

        Args:
            result: TranscriptResult to save
            output_path: Base output path (extension will be replaced)
            format: Output format (txt, srt, vtt)

        Returns:
            Path to saved file
        """
        output_path = output_path.with_suffix(f".{format}")

        if format == "txt":
            content = result.full_text

        elif format == "srt":
            lines = []
            for i, seg in enumerate(result.segments, 1):
                start = self._format_timestamp_srt(seg.start)
                end = self._format_timestamp_srt(seg.end)
                lines.append(f"{i}\n{start} --> {end}\n{seg.text}\n")
            content = "\n".join(lines)

        elif format == "vtt":
            lines = ["WEBVTT\n"]
            for seg in result.segments:
                start = self._format_timestamp_vtt(seg.start)
                end = self._format_timestamp_vtt(seg.end)
                lines.append(f"\n{start} --> {end}\n{seg.text}")
            content = "\n".join(lines)

        else:
            raise ValueError(f"Unknown format: {format}")

        output_path.write_text(content, encoding="utf-8")
        logger.info(f"Saved transcript: {output_path}")

        return output_path

    def _format_timestamp_srt(self, seconds: float) -> str:
        """Format timestamp for SRT (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _format_timestamp_vtt(self, seconds: float) -> str:
        """Format timestamp for VTT (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
