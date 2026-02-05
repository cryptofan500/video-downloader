# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-02-05

### Added
- Multi-browser cookie extraction (Firefox, Edge, Chrome, Brave, Opera, Vivaldi, Whale, Chromium)
- Browser process detection to avoid locked Chromium databases
- Player client fallback strategies (web, web_embedded, android_sdkless, tv)
- Rate limiting with exponential backoff for YouTube anti-bot measures
- User-Agent rotation matching the cookie source browser
- Pre-flight checks (internet connectivity, YouTube accessibility, disk space)
- Download retry functionality with automatic strategy escalation
- GitHub Actions workflow for automated builds
- Binary fetcher script for FFmpeg and Deno setup

### Changed
- Updated User-Agent pool for 2026 browser versions
- Improved error classification (recoverable vs fatal errors)
- Pinned dependency versions for stability

### Fixed
- js_runtimes format for yt-dlp November 2025+ compatibility
- YouTube mix playlist infinite download loop prevention

## [1.0.0] - 2026-01-15

### Added
- Initial release
- GUI with CustomTkinter dark theme
- CLI with Typer and Rich formatting
- YouTube, Vimeo, and 1000+ site support via yt-dlp
- Quality selection (4K, 1080p, 720p, 480p, audio-only)
- Progress tracking with real-time speed and ETA
- System diagnostics pane with export
- Transcription support via faster-whisper (optional)
- Windows 10/11 DPI-aware manifest
- Portable EXE distribution via PyInstaller
