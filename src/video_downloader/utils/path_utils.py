"""
Path utilities for frozen and development environments.

Handles sys._MEIPASS for PyInstaller bundles and provides safe path resolution.
"""

import os
import sys
from pathlib import Path


def get_application_path() -> Path:
    """
    Get the application's base path.

    Works correctly whether running as:
    - Python script (development)
    - PyInstaller frozen executable
    - Installed package

    Returns:
        Path to application base directory
    """
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        # sys._MEIPASS is the temp folder where PyInstaller extracts files
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        # Running as script - go up from utils to package root
        return Path(__file__).parent.parent.parent.parent


def get_bin_path() -> Path:
    """
    Get path to bin/ directory containing external executables.

    Returns:
        Path to bin directory
    """
    if getattr(sys, "frozen", False):
        # In frozen app, bin/ is bundled at _MEIPASS/bin/
        return Path(sys._MEIPASS) / "bin"  # type: ignore[attr-defined]
    else:
        # In development, bin/ is at project root
        return get_application_path() / "bin"


def get_resource_path(relative_path: str) -> Path:
    """
    Get absolute path to a resource, works for dev and PyInstaller.

    Args:
        relative_path: Path relative to application root

    Returns:
        Absolute path to resource
    """
    base = get_application_path()
    return base / relative_path


def get_config_path() -> Path:
    """
    Get path to config.toml.

    For frozen apps, config is next to the .exe (user-modifiable).
    For development, config is in project root.

    Returns:
        Path to config.toml
    """
    if getattr(sys, "frozen", False):
        # Frozen: config.toml next to .exe (not inside bundle)
        return Path(sys.executable).parent / "config.toml"
    else:
        return get_application_path() / "config.toml"


def get_default_output_dir() -> Path:
    """
    Get default output directory for downloads.

    Returns:
        Path to downloads directory (created if needed)
    """
    if getattr(sys, "frozen", False):
        # Frozen: downloads folder next to .exe
        output_dir = Path(sys.executable).parent / "downloads"
    else:
        # Development: downloads in project root
        output_dir = get_application_path() / "downloads"

    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def setup_environment_paths() -> None:
    """
    Configure PATH and environment for external tools.

    Must be called early in application startup.
    """
    bin_path = get_bin_path()

    if bin_path.exists():
        # Prepend bin/ to PATH so ffmpeg/deno are found
        current_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(bin_path) + os.pathsep + current_path

        # Set explicit ffmpeg location for yt-dlp
        ffmpeg_exe = bin_path / "ffmpeg.exe"
        if ffmpeg_exe.exists():
            os.environ["FFMPEG_BINARY"] = str(ffmpeg_exe)


def is_frozen() -> bool:
    """Check if running as frozen PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def safe_path_str(path: Path) -> str:
    """
    Convert path to string safe for subprocess calls.

    Handles spaces and special characters in paths.

    Args:
        path: Path to convert

    Returns:
        String path, quoted if necessary
    """
    path_str = str(path.resolve())

    # On Windows, paths with spaces need quoting for some subprocess calls
    if " " in path_str and not path_str.startswith('"'):
        return f'"{path_str}"'

    return path_str
