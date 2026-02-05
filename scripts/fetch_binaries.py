"""
Helper script to download required binaries (FFmpeg, Deno) for Windows.

Usage: python scripts/fetch_binaries.py

This script downloads the exact versions of FFmpeg and Deno needed for the
video downloader to function properly. It extracts only the required executables
and places them in the bin/ directory.
"""

import io
import sys
import zipfile
import urllib.request
from pathlib import Path

# Configuration
BIN_DIR = Path(__file__).parent.parent / "bin"

# FFmpeg from BtbN's builds (GPL licensed, includes all codecs)
FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

# Deno runtime for YouTube JS execution
DENO_URL = "https://github.com/denoland/deno/releases/download/v2.1.9/deno-x86_64-pc-windows-msvc.zip"


def download_and_extract(url: str, target_files: list[str]) -> None:
    """Download ZIP and extract specific files to bin directory."""
    print(f"Downloading {url}...")

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            data = response.read()
            print(f"  Downloaded {len(data) / (1024*1024):.1f} MB")

            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for file_info in z.infolist():
                    # Extract only the files we need (flatten directory structure)
                    if file_info.filename.endswith(tuple(target_files)):
                        filename = Path(file_info.filename).name
                        print(f"  Extracting {filename}...")
                        target_path = BIN_DIR / filename
                        with z.open(file_info) as source:
                            with open(target_path, "wb") as target:
                                target.write(source.read())
    except Exception as e:
        print(f"  Error: {e}")
        raise


def main() -> int:
    """Download all required binaries."""
    print(f"Binary directory: {BIN_DIR.resolve()}")
    BIN_DIR.mkdir(exist_ok=True)

    try:
        # Download FFmpeg (includes ffmpeg.exe and ffprobe.exe)
        download_and_extract(FFMPEG_URL, ["ffmpeg.exe", "ffprobe.exe"])

        # Download Deno
        download_and_extract(DENO_URL, ["deno.exe"])

        print(f"\nBinaries ready in {BIN_DIR}")
        print("\nInstalled files:")
        for f in BIN_DIR.glob("*.exe"):
            print(f"  - {f.name}")

        return 0

    except Exception as e:
        print(f"\nFailed to download binaries: {e}")
        print("Please download manually:")
        print(f"  FFmpeg: {FFMPEG_URL}")
        print(f"  Deno: {DENO_URL}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
