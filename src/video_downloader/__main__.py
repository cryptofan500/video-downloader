"""
Entry point for running video downloader as a module.

Usage:
    python -m video_downloader          # Start GUI
    python -m video_downloader cli      # Start CLI
"""

import sys

if __name__ == "__main__":
    # Check if CLI mode is requested
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        # Remove 'cli' argument and run CLI
        sys.argv.pop(1)
        from video_downloader.cli import cli_main

        cli_main()
    else:
        # Run GUI
        from video_downloader.gui import main

        main()
