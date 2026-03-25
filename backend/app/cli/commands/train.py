"""atlas-vox train — upload samples and start training."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

app = typer.Typer()
console = Console()


@app.command("upload")
def upload_samples(
    profile_id: str = typer.Argument(..., help="Profile ID"),
    directory: str = typer.Argument(..., help="Directory containing audio files"),
) -> None:
    """Upload audio samples from a directory."""
    async def _upload():
        from app.core.config import settings
        from app.core.database import async_session_factory
        from app.models.audio_sample import AudioSample

        sample_dir = Path(directory)
        if not sample_dir.is_dir():
            console.print(f"[red]✗[/red] Not a directory: {directory}")
            raise typer.Exit(1)

        audio_exts = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
        files = [f for f in sample_dir.iterdir() if f.suffix.lower() in audio_exts]

        if not files:
            console.print(f"[yellow]No audio files found in {directory}[/yellow]")
            raise typer.Exit(1)

        storage_dir = Path(settings.storage_path) / "samples" / profile_id
        storage_dir.mkdir(parents=True, exist_ok=True)

        async with async_session_factory() as db:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), console=console) as progress:
                task = progress.add_task("Uploading...", total=len(files))
                for f in files:
                    import shutil
                    import uuid
                    stored_name = f"{uuid.uuid4().hex[:12]}{f.suffix}"
                    dest = storage_dir / stored_name
                    shutil.copy2(f, dest)

                    sample = AudioSample(
                        profile_id=profile_id,
                        filename=stored_name,
                        original_filename=f.name,
                        file_path=str(dest),
                        format=f.suffix.lstrip("."),
                        file_size_bytes=f.stat().st_size,
                    )
                    db.add(sample)
                    progress.advance(task)
            await db.commit()

        console.print(f"[green]✓[/green] Uploaded {len(files)} samples for profile {profile_id}")

    asyncio.run(_upload())


@app.command("start")
def start_training(
    profile_id: str = typer.Argument(..., help="Profile ID to train"),
    provider: str = typer.Option(None, help="Override provider"),
) -> None:
    """Start a training job."""
    async def _train():
        from app.core.database import async_session_factory
        from app.services.training_service import start_training

        async with async_session_factory() as db:
            try:
                job = await start_training(db, profile_id, provider_name=provider)
                await db.commit()
                console.print("[green]✓[/green] Training started!")
                console.print(f"  Job ID: {job.id}")
                console.print(f"  Provider: {job.provider_name}")
                console.print(f"  Celery Task: {job.celery_task_id}")
                console.print(f"\nMonitor: atlas-vox train status {job.id}")
            except ValueError as e:
                console.print(f"[red]✗[/red] {e}")
                raise typer.Exit(1)

    asyncio.run(_train())


@app.command("status")
def training_status(
    job_id: str = typer.Argument(..., help="Training job ID"),
) -> None:
    """Check training job status."""
    async def _status():
        from app.core.database import async_session_factory
        from app.services.training_service import get_job_status

        async with async_session_factory() as db:
            try:
                status = await get_job_status(db, job_id)
                color = {"completed": "green", "failed": "red", "cancelled": "yellow"}.get(status["status"], "blue")
                console.print(f"Job: {status['id']}")
                console.print(f"Status: [{color}]{status['status']}[/{color}]")
                console.print(f"Progress: {status['progress'] * 100:.0f}%")
                if status.get("error_message"):
                    console.print(f"Error: [red]{status['error_message']}[/red]")
                if status.get("result_version_id"):
                    console.print(f"Version: {status['result_version_id']}")
            except ValueError as e:
                console.print(f"[red]✗[/red] {e}")

    asyncio.run(_status())
