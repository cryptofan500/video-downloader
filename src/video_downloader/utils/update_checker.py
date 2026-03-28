"""
Lightweight update checker using GitHub Releases API.

Checks for newer versions without blocking the UI.
"""

import json
import logging
import urllib.request

from packaging.version import parse

logger = logging.getLogger(__name__)


def check_for_update(current_version: str) -> tuple[bool, str | None]:
    """
    Check if a newer version is available on GitHub.

    Args:
        current_version: Current app version string (e.g. "2.0.0")

    Returns:
        Tuple of (update_available, latest_version_or_none)
    """
    try:
        url = "https://api.github.com/repos/cryptofan500/video-downloader/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": f"video-downloader/{current_version}",
            },
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        tag_name = data.get("tag_name", "")
        latest = tag_name.lstrip("v")

        if not latest:
            return False, None

        if parse(latest) > parse(current_version):
            return True, latest

        return False, None

    except Exception:
        # Never crash on update check failure
        return False, None
