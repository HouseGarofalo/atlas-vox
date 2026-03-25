"""atlas-vox profiles — list, create, delete voice profiles."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


def _run(coro):
    return asyncio.run(coro)


@app.command("list")
def list_profiles() -> None:
    """List all voice profiles."""
    async def _list():
        from app.core.database import async_session_factory
        from app.services.profile_service import list_profiles as _list_all
        from app.services.profile_service import profile_to_response

        async with async_session_factory() as db:
            profiles = await _list_all(db)
            table = Table(title="Voice Profiles")
            table.add_column("ID", style="dim", max_width=12)
            table.add_column("Name", style="cyan")
            table.add_column("Provider")
            table.add_column("Status")
            table.add_column("Samples", justify="right")
            table.add_column("Versions", justify="right")

            for p in profiles:
                r = await profile_to_response(db, p)
                color = {"ready": "green", "training": "blue", "error": "red"}.get(r.status, "white")
                table.add_row(
                    p.id[:12], p.name, p.provider_name,
                    f"[{color}]{r.status}[/{color}]",
                    str(r.sample_count), str(r.version_count),
                )
            console.print(table)

    _run(_list())


@app.command("create")
def create_profile(
    name: str = typer.Option(..., prompt=True, help="Profile name"),
    provider: str = typer.Option("kokoro", help="TTS provider name"),
    language: str = typer.Option("en", help="Language code"),
    description: str = typer.Option("", help="Description"),
) -> None:
    """Create a new voice profile."""
    async def _create():
        from app.core.database import async_session_factory
        from app.schemas.profile import ProfileCreate
        from app.services.profile_service import create_profile

        data = ProfileCreate(name=name, provider_name=provider, language=language, description=description or None)
        async with async_session_factory() as db:
            profile = await create_profile(db, data)
            await db.commit()
            console.print(f"[green]✓[/green] Profile created: [bold]{profile.name}[/bold] (ID: {profile.id})")

    _run(_create())


@app.command("delete")
def delete_profile(
    profile_id: str = typer.Argument(..., help="Profile ID to delete"),
) -> None:
    """Delete a voice profile."""
    async def _delete():
        from app.core.database import async_session_factory
        from app.services.profile_service import delete_profile

        async with async_session_factory() as db:
            deleted = await delete_profile(db, profile_id)
            await db.commit()
            if deleted:
                console.print(f"[green]✓[/green] Profile deleted: {profile_id}")
            else:
                console.print(f"[red]✗[/red] Profile not found: {profile_id}")

    _run(_delete())
