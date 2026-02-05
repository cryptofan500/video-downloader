"""
Input validation utilities.

Provides secure validation for URLs and file paths.
"""

import re
from pathlib import Path
from urllib.parse import urlparse

from video_downloader.utils.exceptions import ValidationError


class URLValidator:
    """Validates URLs with security checks."""

    ALLOWED_SCHEMES = ["http", "https"]

    # Only block actual shell injection patterns, not URL-safe characters
    # Parentheses () are common in URLs and video titles
    SHELL_INJECTION_PATTERNS = [
        r"\$\(",  # $(command)
        r"\$\{",  # ${variable}
        r"`[^`]+`",  # `command`
        r";\s*\w",  # ; command
        r"\|\s*\w",  # | command
        r">\s*/",  # > /path (redirect)
        r"<\s*/",  # < /path (redirect)
    ]

    # Private IP patterns for SSRF prevention
    PRIVATE_IP_PATTERNS = [
        r"^localhost",
        r"^127\.",
        r"^10\.",
        r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",
        r"^192\.168\.",
        r"^\[::1\]",  # IPv6 localhost
        r"^0\.0\.0\.0",
    ]

    @classmethod
    def validate(cls, url: str) -> str:
        """
        Validate URL against security rules.

        Args:
            url: URL string to validate

        Returns:
            Validated URL string (stripped)

        Raises:
            ValidationError: If URL is invalid or contains dangerous patterns
        """
        if not url or not url.strip():
            raise ValidationError("URL cannot be empty")

        url = url.strip()

        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in cls.ALLOWED_SCHEMES:
                raise ValidationError(
                    f"Invalid URL scheme: {parsed.scheme}. "
                    f"Only {', '.join(cls.ALLOWED_SCHEMES)} are allowed."
                )

            # Check for valid netloc (domain)
            if not parsed.netloc:
                raise ValidationError("URL must have a valid domain")

            # Block private/local addresses (SSRF prevention)
            netloc = parsed.netloc.lower()
            for pattern in cls.PRIVATE_IP_PATTERNS:
                if re.match(pattern, netloc):
                    raise ValidationError("Private/local addresses are not allowed")

            # Check for shell injection patterns in the full URL
            for pattern in cls.SHELL_INJECTION_PATTERNS:
                if re.search(pattern, url):
                    raise ValidationError("URL contains potentially dangerous patterns")

            return url

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"URL validation failed: {e}")


class PathValidator:
    """Validates file paths with security checks."""

    # Windows reserved filenames
    RESERVED_NAMES = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }

    def __init__(self, base_dir: Path) -> None:
        """
        Initialize path validator.

        Args:
            base_dir: Base directory for path validation
        """
        self.base_dir = base_dir.resolve()

    def validate(self, user_path: str) -> Path:
        """
        Validate user-provided path against base directory.

        Prevents path traversal attacks.

        Args:
            user_path: User-provided path string

        Returns:
            Validated Path object

        Raises:
            ValidationError: If path is invalid or attempts traversal
        """
        if not user_path or not user_path.strip():
            raise ValidationError("Path cannot be empty")

        try:
            # Convert to Path and resolve
            full_path = (self.base_dir / user_path.strip()).resolve()

            # Verify path is within base directory
            try:
                full_path.relative_to(self.base_dir)
            except ValueError:
                raise ValidationError(
                    f"Path traversal detected. Path must be within {self.base_dir}"
                )

            # Check for Windows reserved names
            if full_path.name.upper().split(".")[0] in self.RESERVED_NAMES:
                raise ValidationError(f"Reserved filename: {full_path.name}")

            return full_path

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Path validation failed: {e}")
