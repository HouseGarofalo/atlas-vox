"""atlas-vox presets — manage persona presets."""

from __future__ import annotations

import asyncio

import structlog
import typer
from rich.console import Console
from rich.table import Table

logger = structlog.get_logger("atlas_vox.cli")

app = typer.Typer()
console = Console()


@app.command("list")
def list_presets() -> None:
    """List all persona presets."""
    async def _list():
        from sqlalchemy import select

        from app.core.database import async_session_factory
        from app.models.persona_preset import PersonaPreset

        logger.info("cli_presets_list")
        async with async_session_factory() as db:
            result = await db.execute(select(PersonaPreset).order_by(PersonaPreset.name))
            presets = result.scalars().all()

            table = Table(title="Persona Presets")
            table.add_column("Name", style="cyan")
            table.add_column("Speed", justify="right")
            table.add_column("Pitch", justify="right")
            table.add_column("Volume", justify="right")
            table.add_column("System")
            table.add_column("Description", style="dim")

            for p in presets:
                table.add_row(
                    p.name,
                    f"{p.speed:.2f}",
                    f"{p.pitch:+.0f}",
                    f"{p.volume:.2f}",
                    "✓" if p.is_system else "",
                    p.description or "",
                )

            console.print(table)

    asyncio.run(_list())


@app.command("create")
def create_preset(
    name: str = typer.Option(..., prompt=True),
    speed: float = typer.Option(1.0),
    pitch: float = typer.Option(0.0),
    volume: float = typer.Option(1.0),
    description: str = typer.Option(""),
) -> None:
    """Create a custom persona preset."""
    async def _create():
        from app.core.database import async_session_factory
        from app.models.persona_preset import PersonaPreset

        logger.info("cli_preset_create", name=name, speed=speed, pitch=pitch, volume=volume)
        async with async_session_factory() as db:
            preset = PersonaPreset(name=name, speed=speed, pitch=pitch, volume=volume, description=description or None)
            db.add(preset)
            await db.commit()
            logger.info("cli_preset_created", preset_id=preset.id, name=name)
            console.print(f"[green]✓[/green] Preset created: [bold]{name}[/bold]")

    asyncio.run(_create())
