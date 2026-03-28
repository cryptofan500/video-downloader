# Contributing to Video Downloader

Thank you for considering contributing! Here's how to get started.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Git

## Development Setup

```bash
git clone https://github.com/cryptofan500/video-downloader.git
cd video-downloader
setup.bat
```

`setup.bat` will install dependencies, fetch FFmpeg/Deno binaries, and create the downloads folder.

To run the app:

```bash
run.bat
```

## Running Tests

```bash
pytest tests/ -v
```

## Linting

```bash
ruff check src/
```

To auto-fix issues:

```bash
ruff check src/ --fix
```

## Code Style

- Formatting and linting handled by [ruff](https://docs.astral.sh/ruff/)
- Type hints are required for all public functions
- Line length limit: 100 characters
- Target Python version: 3.12

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests and linting to confirm nothing is broken
5. Commit with a descriptive message
6. Push to your fork and open a Pull Request

## Reporting Issues

Use the [issue templates](https://github.com/cryptofan500/video-downloader/issues/new/choose) for bug reports and feature requests.
