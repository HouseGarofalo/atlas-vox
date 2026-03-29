"""atlas-vox synthesize — text-to-speech synthesis."""

from __future__ import annotations

import asyncio

import structlog
import typer
from rich.console import Console

logger = structlog.get_logger("atlas_vox.cli")

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def synthesize_text(
    text: str = typer.Argument(..., help="Text to synthesize"),
    profile_id: str = typer.Option(..., "--voice", "-v", help="Voice profile ID"),
    output: str = typer.Option("output.wav", "--output", "-o", help="Output file path"),
    speed: float = typer.Option(1.0, help="Speech speed (0.5–2.0)"),
    play: bool = typer.Option(False, "--play", "-p", help="Play audio after synthesis"),
    format: str = typer.Option("wav", "--format", "-f", help="Output format: wav, mp3, ogg"),
) -> None:
    """Synthesize text to speech."""
    async def _synth():
        import shutil

        from app.core.database import async_session_factory
        from app.services.synthesis_service import synthesize

        logger.info(
            "cli_synthesize_started",
            profile_id=profile_id,
            text_length=len(text),
            output=output,
            format=format,
        )
        async with async_session_factory() as db:
            try:
                result = await synthesize(
                    db, text=text, profile_id=profile_id,
                    speed=speed, output_format=format,
                )
                await db.commit()

                # Copy to requested output path
                from pathlib import Path
                src = Path(result["audio_url"].split("/")[-1])
                from app.core.config import settings
                src_path = Path(settings.storage_path) / "output" / src
                shutil.copy2(src_path, output)

                logger.info(
                    "cli_synthesize_completed",
                    profile_id=profile_id,
                    latency_ms=result["latency_ms"],
                    output=output,
                )
                console.print(f"[green]✓[/green] Synthesized to: [bold]{output}[/bold]")
                console.print(f"  Provider: {result['provider_name']}")
                console.print(f"  Latency: {result['latency_ms']}ms")
                if result.get("duration_seconds"):
                    console.print(f"  Duration: {result['duration_seconds']:.1f}s")

                if play:
                    _play_audio(output)

            except ValueError as e:
                logger.error("cli_synthesize_failed", profile_id=profile_id, error=str(e))
                console.print(f"[red]✗[/red] {e}")
                raise typer.Exit(1)

    asyncio.run(_synth())


def _play_audio(path: str) -> None:
    """Attempt to play audio using system default player."""
    import subprocess
    import sys

    try:
        if sys.platform == "win32":
            subprocess.Popen(["start", "", path], shell=True)
        elif sys.platform == "darwin":
            subprocess.Popen(["afplay", path])
        else:
            subprocess.Popen(["aplay", path])
        console.print("[dim]Playing audio...[/dim]")
    except Exception:
        console.print(f"[dim]Open {path} to play the audio[/dim]")
