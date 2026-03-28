"""
Command-line interface for video downloader.

Provides Typer-based CLI for downloading videos from the terminal.
"""

import logging
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)

from video_downloader.core.downloader import VideoDownloader
from video_downloader.core.runtime_manager import RuntimeManager
from video_downloader.utils.config import AppConfig, DownloadConfig
from video_downloader.utils.exceptions import (
    ConfigurationError,
    DownloadError,
    NetworkError,
    RuntimeNotFoundError,
    ValidationError,
)
from video_downloader.utils.ffmpeg_manager import FFmpegManager
from video_downloader.utils.validators import URLValidator

# Configure logging for CLI
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = typer.Typer(
    name="video-downloader",
    help="Download videos from YouTube, Vimeo, and other platforms",
    add_completion=False,
)
console = Console()


@app.command()
def download(
    url: str = typer.Argument(..., help="Video URL to download"),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output directory (default: configured downloads folder)"
    ),
    quality: str = typer.Option(
        "best", "--quality", "-q", help="Video quality: best, 2160p, 1080p, 720p, 480p, audio"
    ),
    audio_only: bool = typer.Option(False, "--audio-only", "-a", help="Download audio only"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Verbose output with debug information"
    ),
):
    """
    Download a video from URL.

    Examples:
        video-downloader download "https://www.youtube.com/watch?v=..."

        video-downloader download "https://..." -o "my_video.mp4" -q 1080p

        video-downloader download "https://..." --audio-only
    """
    # Set log level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration
    try:
        config_path = Path("config.toml")
        if config_path.exists():
            config = AppConfig.from_toml(config_path)
        else:
            # Use defaults
            config = AppConfig(
                title="Video Downloader",
                version="2.0.0",
                download=DownloadConfig(
                    output_dir=Path("downloads"),
                    max_concurrent=3,
                    timeout=300,
                    retry_attempts=3,
                    quality=quality,
                ),
            )
            console.print("[yellow]Using default configuration (no config.toml found)[/yellow]")
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1) from None

    # Validate URL
    try:
        validated_url = URLValidator.validate(url)
        console.print(f"[green]✓[/green] URL validated: {validated_url}")
    except ValidationError as e:
        console.print(f"[red]✗ Invalid URL: {e}[/red]")
        raise typer.Exit(1) from None

    # Initialize runtime manager
    try:
        runtime_manager = RuntimeManager()
        console.print(f"[green]✓[/green] Deno runtime: {runtime_manager.deno_path}")
    except RuntimeNotFoundError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1) from None

    # Check FFmpeg
    try:
        ffmpeg_manager = FFmpegManager()
        success, version_str, _ = ffmpeg_manager.check_version()
        if success:
            console.print(f"[green]✓[/green] FFmpeg: {version_str}")
        else:
            console.print("[yellow]⚠[/yellow] FFmpeg version check failed")
    except RuntimeNotFoundError:
        console.print("[yellow]⚠[/yellow] FFmpeg not found (may affect some downloads)")

    # Determine output path
    if output is None:
        output = config.download.output_dir
        output.mkdir(parents=True, exist_ok=True)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)

    # Create downloader
    downloader = VideoDownloader(runtime_manager, config)

    # Download with progress bar
    console.print(f"\n[cyan]Downloading to: {output}[/cyan]\n")

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TextColumn("[cyan]{task.fields[speed]}[/cyan]"),
        TextColumn("•"),
        TextColumn("ETA: {task.fields[eta]}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task: TaskID | None = None

        def progress_callback(info: dict) -> None:
            nonlocal task

            if info["status"] == "downloading":
                if task is None:
                    task = progress.add_task(
                        "Downloading...",
                        total=100,
                        speed=info.get("speed", "N/A"),
                        eta=info.get("eta", "N/A"),
                    )

                try:
                    pct = float(info["percentage"].strip("%"))
                    progress.update(
                        task,
                        completed=pct,
                        speed=info.get("speed", "N/A"),
                        eta=info.get("eta", "N/A"),
                    )
                except ValueError:
                    pass

            elif info["status"] == "complete":
                if task is not None:
                    progress.update(task, completed=100)

        try:
            success = downloader.download_with_retry(
                validated_url,
                output,
                progress_callback,
                quality,
                audio_only,
            )

            if success:
                console.print(f"\n[green]✓ Downloaded successfully: {output}[/green]")
            else:
                console.print("\n[red]✗ Download failed or was cancelled[/red]")
                raise typer.Exit(1)

        except NetworkError as e:
            console.print(f"\n[red]✗ Network error: {e}[/red]")
            raise typer.Exit(1) from None

        except DownloadError as e:
            console.print(f"\n[red]✗ Download error: {e}[/red]")
            raise typer.Exit(1) from None

        except KeyboardInterrupt:
            console.print("\n[yellow]⚠ Download cancelled by user[/yellow]")
            raise typer.Exit(130) from None

        except Exception as e:
            console.print(f"\n[red]✗ Unexpected error: {e}[/red]")
            if verbose:
                console.print_exception()
            raise typer.Exit(1) from None


@app.command()
def check_deps():
    """Check runtime dependencies (Deno, FFmpeg)."""
    console.print("\n[bold]Checking dependencies...[/bold]\n")

    # Check Deno
    try:
        runtime_manager = RuntimeManager()
        console.print(f"[green]✓ Deno[/green]: {runtime_manager.deno_path}")
    except RuntimeNotFoundError as e:
        console.print(f"[red]✗ Deno[/red]: {e}")

    # Check FFmpeg
    try:
        ffmpeg_manager = FFmpegManager()
        success, version_str, version = ffmpeg_manager.check_version()
        if success:
            console.print(f"[green]✓ FFmpeg[/green]: {version_str}")
        else:
            console.print(f"[yellow]⚠ FFmpeg[/yellow]: Version check failed - {version_str}")
    except RuntimeNotFoundError as e:
        console.print(f"[red]✗ FFmpeg[/red]: {e}")

    console.print()


@app.command()
def version():
    """Show version information."""
    from video_downloader import __version__

    console.print(f"Video Downloader v{__version__}")


def cli_main():
    """Entry point for CLI."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    cli_main()
