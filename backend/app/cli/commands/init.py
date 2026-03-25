"""atlas-vox init — initialize config, database, check system dependencies."""

from __future__ import annotations

import shutil
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def init() -> None:
    """Initialize Atlas Vox: create config, database, check dependencies."""
    console.print("[bold blue]Atlas Vox Initialization[/bold blue]\n")

    # Check system deps
    table = Table(title="System Dependencies")
    table.add_column("Dependency", style="cyan")
    table.add_column("Status")
    table.add_column("Notes", style="dim")

    deps = [
        ("Python 3.11+", True, ""),
        ("espeak-ng", shutil.which("espeak-ng") is not None, "Required by Kokoro, StyleTTS2, Piper"),
        ("FFmpeg", shutil.which("ffmpeg") is not None, "Audio format conversion"),
        ("Redis", _check_redis(), "Celery broker/backend"),
    ]

    all_ok = True
    for name, ok, note in deps:
        status = "[green]✓ Found[/green]" if ok else "[red]✗ Missing[/red]"
        if not ok:
            all_ok = False
        table.add_row(name, status, note)

    console.print(table)

    # Create storage directories
    storage = Path("./storage")
    for subdir in ["samples", "preprocessed", "output", "models", "models/piper", "models/coqui_xtts"]:
        (storage / subdir).mkdir(parents=True, exist_ok=True)
    console.print("\n[green]✓[/green] Storage directories created")

    # Init database
    try:
        import asyncio

        from app.core.database import init_db
        asyncio.run(init_db())
        console.print("[green]✓[/green] Database initialized")
    except Exception as e:
        console.print(f"[red]✗[/red] Database error: {e}")

    if all_ok:
        console.print("\n[bold green]Atlas Vox is ready![/bold green] Run `atlas-vox serve` to start.")
    else:
        console.print("\n[yellow]Some dependencies are missing. Install them for full functionality.[/yellow]")


def _check_redis() -> bool:
    try:
        import redis
        r = redis.Redis()
        r.ping()
        return True
    except Exception:
        return False
