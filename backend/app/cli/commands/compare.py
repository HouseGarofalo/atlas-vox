"""atlas-vox compare — compare voices side-by-side."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def compare_voices(
    text: str = typer.Argument(..., help="Text to synthesize"),
    profile_ids: list[str] = typer.Option(..., "--voice", "-v", help="Profile IDs to compare (repeat for multiple)"),
) -> None:
    """Compare the same text across multiple voice profiles."""
    if len(profile_ids) < 2:
        console.print("[red]Need at least 2 voices for comparison.[/red]")
        raise typer.Exit(1)

    async def _compare():
        from app.core.database import async_session_factory
        from app.services.comparison_service import compare_voices

        async with async_session_factory() as db:
            try:
                results = await compare_voices(db, text=text, profile_ids=profile_ids)
                await db.commit()

                table = Table(title="Voice Comparison")
                table.add_column("Profile", style="cyan")
                table.add_column("Provider")
                table.add_column("Latency", justify="right")
                table.add_column("Duration", justify="right")
                table.add_column("Audio File", style="dim")

                for r in results:
                    table.add_row(
                        r.get("profile_name", "?"),
                        r.get("provider_name", "?"),
                        f"{r.get('latency_ms', 0)}ms",
                        f"{r.get('duration_seconds', 0):.1f}s" if r.get("duration_seconds") else "—",
                        r.get("audio_url", ""),
                    )

                console.print(table)
            except ValueError as e:
                console.print(f"[red]✗[/red] {e}")
                raise typer.Exit(1)

    asyncio.run(_compare())
