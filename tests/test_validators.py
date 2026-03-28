"""
Tests for input validation utilities.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from video_downloader.utils.exceptions import ValidationError
from video_downloader.utils.validators import PathValidator, URLValidator


class TestURLValidator:
    """Tests for URL validation."""
    
    def test_valid_https_url(self):
        """Test valid HTTPS URL passes validation."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = URLValidator.validate(url)
        assert result == url
    
    def test_valid_http_url(self):
        """Test valid HTTP URL passes validation."""
        url = "http://example.com/video.mp4"
        result = URLValidator.validate(url)
        assert result == url
    
    def test_empty_url_raises_error(self):
        """Test empty URL raises ValidationError."""
        with pytest.raises(ValidationError, match="URL cannot be empty"):
            URLValidator.validate("")
    
    def test_invalid_scheme_raises_error(self):
        """Test invalid URL scheme raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid URL scheme"):
            URLValidator.validate("ftp://example.com/file.mp4")
    
    def test_dangerous_characters_raise_error(self):
        """Test URL with dangerous characters raises ValidationError."""
        with pytest.raises(ValidationError, match="dangerous patterns"):
            URLValidator.validate("https://example.com/video?cmd=`rm -rf /`")
    
    def test_private_ip_raises_error(self):
        """Test private IP addresses are blocked."""
        with pytest.raises(ValidationError, match="Private/local addresses"):
            URLValidator.validate("http://localhost/video.mp4")
        
        with pytest.raises(ValidationError):
            URLValidator.validate("http://192.168.1.1/video.mp4")


class TestPathValidator:
    """Tests for path validation."""
    
    def test_valid_path_within_base(self, tmp_path):
        """Test valid path within base directory passes."""
        validator = PathValidator(tmp_path)
        result = validator.validate("downloads/video.mp4")
        assert result.is_relative_to(tmp_path)
    
    def test_path_traversal_raises_error(self, tmp_path):
        """Test path traversal attempt raises ValidationError."""
        validator = PathValidator(tmp_path)
        with pytest.raises(ValidationError, match="Path traversal detected"):
            validator.validate("../../etc/passwd")
    
    def test_reserved_filename_raises_error(self, tmp_path):
        """Test Windows reserved filename raises ValidationError."""
        validator = PathValidator(tmp_path)
        with pytest.raises(ValidationError, match="reserved name"):
            validator.validate("CON")
    
    def test_empty_path_raises_error(self, tmp_path):
        """Test empty path raises ValidationError."""
        validator = PathValidator(tmp_path)
        with pytest.raises(ValidationError, match="Path cannot be empty"):
            validator.validate("")


class TestConfigLoading:
    """Tests for configuration loading."""
    
    def test_load_valid_config(self, tmp_path):
        """Test loading valid TOML configuration."""
        from video_downloader.utils.config import AppConfig
        
        config_content = """
[app]
title = "Test App"
version = "1.0.0"

[download]
output_dir = "downloads"
max_concurrent = 3
timeout = 300
retry_attempts = 3
quality = "best"
"""
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)
        
        config = AppConfig.from_toml(config_file)
        assert config.title == "Test App"
        assert config.version == "1.0.0"
        assert config.download.max_concurrent == 3


class TestSSRFPrevention:
    """Tests for SSRF prevention via DNS resolution."""

    def _mock_getaddrinfo(self, ip):
        """Helper to create a mock getaddrinfo that returns a specific IP."""
        return [(2, 1, 6, "", (ip, 0))]

    def test_blocks_localhost(self):
        """Localhost should be blocked."""
        with patch(
            "video_downloader.utils.validators.socket.getaddrinfo",
            return_value=self._mock_getaddrinfo("127.0.0.1"),
        ):
            with pytest.raises(ValidationError, match="Private/local addresses"):
                URLValidator.validate("http://localhost/path")

    def test_blocks_private_ip_192(self):
        """192.168.x.x should be blocked."""
        with patch(
            "video_downloader.utils.validators.socket.getaddrinfo",
            return_value=self._mock_getaddrinfo("192.168.1.1"),
        ):
            with pytest.raises(ValidationError, match="Private/local addresses"):
                URLValidator.validate("http://192.168.1.1/path")

    def test_blocks_private_ip_10(self):
        """10.x.x.x should be blocked."""
        with patch(
            "video_downloader.utils.validators.socket.getaddrinfo",
            return_value=self._mock_getaddrinfo("10.0.0.1"),
        ):
            with pytest.raises(ValidationError, match="Private/local addresses"):
                URLValidator.validate("http://10.0.0.1/path")

    def test_blocks_userinfo(self):
        """URLs with user@host should be blocked."""
        with pytest.raises(ValidationError, match="credentials"):
            URLValidator.validate("http://admin@127.0.0.1/")

    def test_allows_public_urls(self):
        """Public URLs should pass validation."""
        with patch(
            "video_downloader.utils.validators.socket.getaddrinfo",
            return_value=self._mock_getaddrinfo("142.250.80.46"),
        ):
            result = URLValidator.validate("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        with patch(
            "video_downloader.utils.validators.socket.getaddrinfo",
            return_value=self._mock_getaddrinfo("151.101.1.69"),
        ):
            result = URLValidator.validate("https://vimeo.com/123456")
            assert result == "https://vimeo.com/123456"

    def test_handles_unresolvable_hosts(self):
        """Unresolvable hosts should pass (they'll fail at download time)."""
        import socket

        with patch(
            "video_downloader.utils.validators.socket.getaddrinfo",
            side_effect=socket.gaierror("Name or service not known"),
        ):
            result = URLValidator.validate(
                "https://this-domain-does-not-exist-xyz123.com/video"
            )
            assert "this-domain-does-not-exist-xyz123.com" in result


class TestPathValidatorReservedNames:
    """Tests for reserved name validation across all path components."""

    def test_reserved_name_in_subdirectory(self, tmp_path):
        """Reserved names in subdirectories should be caught."""
        validator = PathValidator(tmp_path)
        with pytest.raises(ValidationError, match="reserved name"):
            validator.validate("CON/video.mp4")

    def test_reserved_name_with_extension(self, tmp_path):
        """Reserved names with extensions should be caught (e.g. NUL.txt)."""
        validator = PathValidator(tmp_path)
        with pytest.raises(ValidationError, match="reserved name"):
            validator.validate("NUL.txt")
