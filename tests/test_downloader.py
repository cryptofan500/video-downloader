"""
Unit tests for core downloader logic.

All tests are offline — no network access required.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from video_downloader.core.downloader import VideoDownloader
from video_downloader.utils.config import AppConfig, DownloadConfig
from video_downloader.utils.validators import is_mix_playlist


@pytest.fixture
def mock_runtime_manager():
    """Create a mock RuntimeManager."""
    rm = MagicMock()
    rm.deno_path = Path("bin/deno.exe")
    rm.get_ytdlp_options.return_value = {}
    return rm


@pytest.fixture
def mock_config():
    """Create a mock AppConfig."""
    return AppConfig(
        title="Video Downloader",
        version="2.1.0",
        download=DownloadConfig(
            output_dir=Path("test_downloads"),
            max_concurrent=3,
            timeout=300,
            retry_attempts=3,
            quality="best",
        ),
    )


@pytest.fixture
def downloader(mock_runtime_manager, mock_config):
    """Create a VideoDownloader instance with mocked dependencies."""
    return VideoDownloader(mock_runtime_manager, mock_config)


class TestClassifyError:
    """Tests for VideoDownloader._classify_error()."""

    def test_video_unavailable(self, downloader):
        is_recoverable, category = downloader._classify_error("video unavailable")
        assert is_recoverable is False
        assert category == "video_unavailable"

    def test_forbidden(self, downloader):
        is_recoverable, category = downloader._classify_error("403 Forbidden")
        assert is_recoverable is True
        assert category == "forbidden"

    def test_rate_limited(self, downloader):
        is_recoverable, category = downloader._classify_error("rate limit exceeded")
        assert is_recoverable is True
        assert category == "rate_limited"

    def test_timeout(self, downloader):
        is_recoverable, category = downloader._classify_error("connection timeout")
        assert is_recoverable is True
        assert category == "network"

    def test_drm_protected(self, downloader):
        is_recoverable, category = downloader._classify_error("drm protected content")
        assert is_recoverable is False
        assert category == "drm_protected"

    def test_unknown_error(self, downloader):
        is_recoverable, category = downloader._classify_error("some random error")
        assert is_recoverable is True
        assert category == "unknown"

    def test_geo_blocked(self, downloader):
        is_recoverable, category = downloader._classify_error(
            "not available in your country"
        )
        assert is_recoverable is False
        assert category == "geo_blocked"

    def test_bot_detection(self, downloader):
        is_recoverable, category = downloader._classify_error(
            "sign in to confirm you're not a bot"
        )
        assert is_recoverable is True
        assert category == "bot_detection"


class TestCalculateBackoff:
    """Tests for VideoDownloader._calculate_backoff()."""

    def test_attempt_zero_within_range(self, downloader):
        delay = downloader._calculate_backoff(0, base_delay=2.0, max_delay=30.0)
        assert 2.0 <= delay <= 2.0 * 1.5

    def test_attempt_two_within_max(self, downloader):
        delay = downloader._calculate_backoff(2, base_delay=2.0, max_delay=30.0)
        # base * 2^2 = 8, max jitter = 8 * 0.5 = 4, so max = 12
        assert delay <= 30.0 * 1.5

    def test_never_exceeds_max_with_jitter(self, downloader):
        for attempt in range(10):
            delay = downloader._calculate_backoff(
                attempt, base_delay=2.0, max_delay=30.0
            )
            assert delay <= 30.0 * 1.5

    def test_increases_with_attempts(self, downloader):
        # On average, higher attempts should produce longer delays
        low_delays = [downloader._calculate_backoff(0) for _ in range(50)]
        high_delays = [downloader._calculate_backoff(4) for _ in range(50)]
        assert sum(low_delays) / len(low_delays) < sum(high_delays) / len(high_delays)


class TestGetFormatConfig:
    """Tests for VideoDownloader._get_format_config()."""

    def test_best_quality(self, downloader):
        config = downloader._get_format_config("best")
        assert config["format"] == "bestvideo+bestaudio/best"

    def test_1080p_quality(self, downloader):
        config = downloader._get_format_config("1080p")
        assert "height<=1080" in config["format"]

    def test_mp3_audio(self, downloader):
        config = downloader._get_format_config("mp3")
        assert config["format"] == "bestaudio/best"
        pp_keys = [pp["key"] for pp in config["postprocessors"]]
        assert "FFmpegExtractAudio" in pp_keys
        audio_pp = next(
            pp for pp in config["postprocessors"] if pp["key"] == "FFmpegExtractAudio"
        )
        assert audio_pp["preferredcodec"] == "mp3"

    def test_native_quality(self, downloader):
        config = downloader._get_format_config("native")
        assert config["merge_output_format"] == "mkv"
        assert config["postprocessors"] == []

    def test_wav_no_embed_thumbnail(self, downloader):
        config = downloader._get_format_config("wav")
        pp_keys = [pp["key"] for pp in config["postprocessors"]]
        assert "EmbedThumbnail" not in pp_keys

    def test_mp3_has_embed_thumbnail(self, downloader):
        config = downloader._get_format_config("mp3")
        pp_keys = [pp["key"] for pp in config["postprocessors"]]
        assert "EmbedThumbnail" in pp_keys

    def test_flac_has_embed_thumbnail(self, downloader):
        config = downloader._get_format_config("flac")
        pp_keys = [pp["key"] for pp in config["postprocessors"]]
        assert "EmbedThumbnail" in pp_keys

    def test_audio_only_flag(self, downloader):
        config = downloader._get_format_config("best", audio_only=True)
        assert config["format"] == "bestaudio/best"


class TestIsMixPlaylist:
    """Tests for the shared is_mix_playlist() utility."""

    def test_mix_playlist_rd_prefix(self):
        assert is_mix_playlist("https://youtube.com/watch?v=abc&list=RDabc") is True

    def test_regular_playlist(self):
        assert is_mix_playlist("https://youtube.com/watch?v=abc&list=PLabc") is False

    def test_no_list_param(self):
        assert is_mix_playlist("https://youtube.com/watch?v=abc") is False

    def test_non_youtube_url(self):
        assert is_mix_playlist("https://example.com") is False

    def test_mix_playlist_rdamvm_prefix(self):
        assert (
            is_mix_playlist("https://youtube.com/watch?v=abc&list=RDAMVMxyz") is True
        )

    def test_empty_string(self):
        assert is_mix_playlist("") is False

    def test_malformed_url(self):
        assert is_mix_playlist("not a url at all") is False
