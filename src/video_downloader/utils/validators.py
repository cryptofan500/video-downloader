"""
Input validation utilities.

Provides secure validation for URLs and file paths.
"""

import ipaddress
import re
import socket
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from video_downloader.utils.constants import MIX_PREFIXES
from video_downloader.utils.exceptions import ValidationError


def is_mix_playlist(url: str) -> bool:
    """
    Check if URL is a YouTube Mix (Radio) playlist.

    Mix playlists are dynamically generated and effectively infinite.
    They require special handling to prevent endless downloads.

    Args:
        url: URL to check

    Returns:
        True if URL is a Mix playlist
    """
    try:
        query = parse_qs(urlparse(url).query)
        if "list" not in query:
            return False
        playlist_id = query["list"][0]
        return any(playlist_id.startswith(prefix) for prefix in MIX_PREFIXES)
    except Exception:
        return False


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

            # SSRF Prevention: resolve hostname and check all IPs
            hostname = (parsed.hostname or "").lower()
            if not hostname:
                raise ValidationError("URL must have a valid hostname")

            # Block userinfo in URLs (user:pass@host)
            if "@" in (parsed.netloc or ""):
                raise ValidationError("URLs with credentials are not allowed")

            try:
                results = socket.getaddrinfo(
                    hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM
                )
                for _, _, _, _, addr in results:
                    ip_obj = ipaddress.ip_address(addr[0])
                    if not ip_obj.is_global:
                        raise ValidationError("Private/local addresses are not allowed")
            except socket.gaierror:
                pass  # Unresolvable hostnames are OK — they'll fail at download time

            # Check for shell injection patterns in the full URL
            for pattern in cls.SHELL_INJECTION_PATTERNS:
                if re.search(pattern, url):
                    raise ValidationError("URL contains potentially dangerous patterns")

            return url

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"URL validation failed: {e}") from e


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
            except ValueError as e:
                raise ValidationError(
                    f"Path traversal detected. Path must be within {self.base_dir}"
                ) from e

            # Check for Windows reserved names in all path components
            for part in full_path.relative_to(self.base_dir).parts:
                if part.split(".")[0].upper() in self.RESERVED_NAMES:
                    raise ValidationError(f"Windows reserved name in path: {part}")

            return full_path

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Path validation failed: {e}") from e
