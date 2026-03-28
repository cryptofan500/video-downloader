# Execution Log - 2026-02-06

## Pre-flight

- **`uv sync`**: Resolved 67 packages, installed yt-dlp-ejs, brotli, certifi, pycryptodomex, requests, websockets, and other transitive deps from `yt-dlp[default]`.
- **CLI test** (`--quality best`, Rick Astley): Downloaded successfully (11.28 MiB, format 18). Noted android/ios PO Token warnings due to hardcoded `player_client: ["web", "android", "ios"]`.

## Changes Made

### 1. Removed hardcoded `player_client` from `download()` (downloader.py)

**Lines removed:** The `extractor_args` block in `ydl_opts` that forced `player_client: ["web", "android", "ios"]`.

**Why:** Hardcoding player clients caused PO Token warnings for android/ios and limited yt-dlp's ability to auto-select the best client. After removal, yt-dlp chose `android_vr` + `web_safari` on its own -- no warnings, and selected format `401+251` (high quality) instead of fallback format `18` (360p).

### 2. Deleted `PLAYER_STRATEGIES` class variable (downloader.py)

**Lines removed:** The entire `PLAYER_STRATEGIES: list[dict[str, Any]]` class variable (4 strategy dicts: web_authenticated, web_embedded, web_embedded_anon, aggressive).

**Why:** Dead code after simplifying retry logic. Strategy rotation added complexity without benefit since yt-dlp handles client selection internally.

### 3. Deleted `_build_strategy_options()` method (downloader.py)

**Lines removed:** The entire `_build_strategy_options()` method (~60 lines) that built yt-dlp options for a specific player strategy.

**Why:** No longer needed after removing strategy rotation. `download_with_retry()` now delegates to `download()` directly.

### 4. Simplified `download_with_retry()` (downloader.py)

**Before:** Iterated over `PLAYER_STRATEGIES`, built per-strategy options via `_build_strategy_options()`, rotated strategies on failure.

**After:** Simple retry loop with exponential backoff that calls `self.download()` directly. Uses `_classify_error()` to distinguish fatal vs recoverable errors. Parameter changed from `max_strategies` to `max_retries` (default 3).

**Callers checked:** `download_manager.py:115` calls with positional args `(url, output_path, progress_cb, quality, audio_only)` -- compatible with new signature.

### 5. Reordered `SUPPORTED_BROWSERS` (downloader.py)

**Before:** firefox, vivaldi, whale, opera, brave, edge, chrome, chromium, safari

**After:** chrome, edge, brave, opera, vivaldi, chromium, whale, firefox, safari

### 6. Removed `tomli` from `pyproject.toml`

**Before:** `"tomli>=2.0.0;python_version<'3.11'"`

**Why:** Dead dependency. Project requires Python >=3.12, which ships `tomllib` in stdlib. The version marker `python_version<'3.11'` meant it was never installed anyway.

### 7. Added "native" quality option

**downloader.py `_get_format_config()`:** Added early return for `quality_lower == "native"` that returns `format="bestvideo+bestaudio/best"`, `merge_output_format="mkv"`, `postprocessors=[]` (no re-encoding).

**constants.py `VIDEO_QUALITIES`:** Added `"native": "bestvideo+bestaudio/best"` entry.

**constants.py `GUI_QUALITY_OPTIONS`:** Added `"native"` after `"best"`.

**main_window.py:** Updated quality dropdown `values` to include `"native"`.

## Post-flight

- **`uv sync`**: Clean audit, 25 packages, no changes needed.
- **`ruff check`** on modified files: All checks passed.
- **`ruff format`** on modified files: 1 file reformatted (constants.py long line), 2 unchanged.
- **CLI test** (`--quality best`, Rick Astley): Download succeeded. yt-dlp auto-selected `android_vr` + `web_safari` clients. Format `401+251` selected (vs `18` before). No PO Token warnings. Exit code 0.

## Files Modified

| File | Changes |
|------|---------|
| `src/video_downloader/core/downloader.py` | Removed extractor_args, PLAYER_STRATEGIES, _build_strategy_options(); simplified download_with_retry(); reordered SUPPORTED_BROWSERS |
| `src/video_downloader/utils/constants.py` | Added "native" to VIDEO_QUALITIES and GUI_QUALITY_OPTIONS |
| `src/video_downloader/gui/main_window.py` | Added "native" to quality dropdown values |
| `pyproject.toml` | Removed tomli dependency |

## Not Committed

All changes are staged locally. No git commit per instructions -- awaiting review.
