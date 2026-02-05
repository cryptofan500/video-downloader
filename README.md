# Video Downloader

![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Platform: Windows](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey.svg)

A modern video downloader with GUI and CLI, built with Python 3.12+.

## Features

- Download videos from YouTube, Vimeo, and 1000+ sites
- Multiple quality options (4K, 1080p, 720p, 480p, audio-only)
- Progress tracking with real-time speed and ETA
- System diagnostics and logging with export
- Right-click context menus for easy copy/paste
- Downloads to user's Downloads folder by default
- Both GUI and CLI interfaces

## Installation

### Option 1: Download Release (Recommended)

Download the latest release from [Releases](https://github.com/cryptofan500/video-downloader/releases).

1. Extract the ZIP file
2. Run `VideoDownloader.exe`

### Option 2: From Source

#### Requirements

- **Python** 3.12+
- **Deno** 2.0+ (for YouTube JavaScript execution)
- **FFmpeg** 4.0+ (for video processing)
- **Windows** 10/11

#### Setup

```powershell
git clone https://github.com/cryptofan500/video-downloader.git
cd video-downloader

# Run setup script
.\setup.bat
```

Or manually:
```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install with uv (faster) or pip
pip install uv
uv pip install -e ".[dev]"

# Fetch binaries (FFmpeg, Deno)
python scripts/fetch_binaries.py
```

### Running the Application

```powershell
# Method 1: Python module
.venv\Scripts\Activate.ps1
python -m video_downloader

# Method 2: Batch file
.\run.bat

# Method 3: Windowless (no console)
cscript run_windowless.vbs
```

## CLI Usage

```powershell
# Activate environment
.venv\Scripts\Activate.ps1

# Download video
python -m video_downloader cli download "https://www.youtube.com/watch?v=..."

# Download with quality
python -m video_downloader cli download "URL" --quality 1080p

# Download audio only
python -m video_downloader cli download "URL" --quality mp3

# Check dependencies
python -m video_downloader cli check-deps
```

## Configuration

Edit `config.toml` to customize:

```toml
[download]
# "downloads" = user's Downloads folder (default)
# Or use absolute path: "C:/Videos"
output_dir = "downloads"
quality = "best"
```

## Building EXE

```powershell
.venv\Scripts\Activate.ps1
pyinstaller app.spec --clean --noconfirm
# Output: dist/VideoDownloader/VideoDownloader.exe
```

## Troubleshooting

**Windows Defender Warning**: Since this EXE is not signed with a paid certificate, Windows may flag it as "Unknown Publisher". This is normal for open-source tools. Click "More info" then "Run anyway", or build from source.

**403 Forbidden errors**: YouTube may temporarily block downloads. Try:
- Wait a few minutes and retry
- Use a different video
- Update yt-dlp: `uv pip install --upgrade yt-dlp`

**Deno/FFmpeg not found**:
- Run `python scripts/fetch_binaries.py` to download automatically
- Or manually place executables in `bin/` folder
- Or install system-wide and add to PATH

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video downloading
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - GUI
- [FFmpeg](https://ffmpeg.org/) - Video processing
- [Deno](https://deno.com/) - JavaScript runtime
