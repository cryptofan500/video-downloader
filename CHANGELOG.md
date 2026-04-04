# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2026-04-04

### Fixed
- Open Folder button now highlights the actual downloaded file in Explorer
- Queue processing guarded against missing download manager
- Fallback config uses "native" quality consistently

### Improved
- User-Agent strings updated to April 2026 browser versions (Chrome 135, Firefox 138, Edge 135, Safari 18.4)
- Cookie extraction now cycles through fallback browsers on auth failures
- AAC and Opus audio formats added to GUI quality dropdown

## [2.1.0] - 2026-03-28

### Security
- Fixed SSRF vulnerability with DNS-resolution-based validation (blocks integer/octal/hex IP bypasses)
- Blocked userinfo in URLs to prevent authentication-based SSRF

### Fixed
- Thread memory leak in download manager (replaced raw threads with ThreadPoolExecutor)
- Race condition when cancelling concurrent downloads (UUID-based task tracking)
- CLI audio format override (--audio-only now respects user's quality choice like flac/wav)
- Console window flash during FFmpeg/Deno subprocess calls on Windows
- DPI awareness conflict between runtime hook and CustomTkinter
- Reserved filename validation now checks all path components

### Added
- MKV as default merge container (universal codec compatibility)
- Firefox prioritized for cookie extraction (immune to Chrome encryption changes)
- Download archive to prevent re-downloading
- Actual downloaded file path tracking
- Artifact attestation for release builds
- Comprehensive test suite for security and core logic

### Changed
- Default quality changed to "native" (highest quality, MKV container, no re-encoding)

## [2.0.0] - 2026-03-28

### Changed
- Consolidated version to 2.0.0 across all files
- setup.bat now automatically fetches FFmpeg and Deno binaries
- Updated Deno runtime to v2.7.9
- Added test and lint CI job that runs before build
- Fixed all ruff lint warnings across the codebase
- Exception chaining with `raise ... from` for proper error tracebacks

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
