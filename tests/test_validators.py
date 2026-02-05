"""
Sample tests for video downloader.

Demonstrates testing patterns for the application.
"""

import pytest
from pathlib import Path

from video_downloader.utils.validators import URLValidator, PathValidator
from video_downloader.utils.exceptions import ValidationError


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
        with pytest.raises(ValidationError, match="dangerous characters"):
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
        with pytest.raises(ValidationError, match="Reserved filename"):
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


# Add more tests as needed
