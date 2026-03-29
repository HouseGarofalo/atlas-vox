"""atlas-vox profiles — list, create, delete voice profiles."""

from __future__ import annotations

import asyncio

import structlog
import typer
from rich.console import Console
from rich.table import Table

logger = structlog.get_logger("atlas_vox.cli")

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

        logger.info("cli_profiles_list")
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

        logger.info("cli_profile_create", name=name, provider=provider, language=language)
        data = ProfileCreate(name=name, provider_name=provider, language=language, description=description or None)
        async with async_session_factory() as db:
            profile = await create_profile(db, data)
            await db.commit()
            logger.info("cli_profile_created", profile_id=profile.id, name=profile.name)
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

        logger.info("cli_profile_delete", profile_id=profile_id)
        async with async_session_factory() as db:
            deleted = await delete_profile(db, profile_id)
            await db.commit()
            if deleted:
                logger.info("cli_profile_deleted", profile_id=profile_id)
                console.print(f"[green]✓[/green] Profile deleted: {profile_id}")
            else:
                logger.warning("cli_profile_not_found", profile_id=profile_id)
                console.print(f"[red]✗[/red] Profile not found: {profile_id}")

    _run(_delete())


@app.command("export")
def export_profiles(
    output: str = typer.Option("profiles_export.json", "--output", "-o", help="Output JSON file path"),
    profile_id: str = typer.Option(None, "--id", help="Export a single profile by ID (exports all if omitted)"),
) -> None:
    """Export voice profiles to JSON file."""
    import json

    async def _export():
        from app.core.database import async_session_factory
        from app.services.profile_service import list_profiles as _list_all, get_profile, profile_to_response

        logger.info("cli_profiles_export", output=output, profile_id=profile_id)
        async with async_session_factory() as db:
            if profile_id:
                profile = await get_profile(db, profile_id)
                if not profile:
                    console.print(f"[red]✗[/red] Profile not found: {profile_id}")
                    raise typer.Exit(1)
                profiles = [profile]
            else:
                profiles = await _list_all(db)

            export_data = []
            for p in profiles:
                r = await profile_to_response(db, p)
                export_data.append({
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "language": p.language,
                    "provider_name": p.provider_name,
                    "voice_id": p.voice_id,
                    "status": r.status,
                    "tags": p.tags,
                    "sample_count": r.sample_count,
                    "version_count": r.version_count,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                })

        with open(output, "w") as f:
            json.dump({"profiles": export_data, "count": len(export_data)}, f, indent=2)

        console.print(f"[green]✓[/green] Exported {len(export_data)} profile(s) to [bold]{output}[/bold]")

    _run(_export())


@app.command("import")
def import_profiles(
    input_file: str = typer.Argument(..., help="JSON file to import profiles from"),
    skip_existing: bool = typer.Option(True, help="Skip profiles that already exist (by name)"),
) -> None:
    """Import voice profiles from a JSON file."""
    import json
    from pathlib import Path

    if not Path(input_file).exists():
        console.print(f"[red]✗[/red] File not found: {input_file}")
        raise typer.Exit(1)

    with open(input_file) as f:
        data = json.load(f)

    profile_list = data.get("profiles", data if isinstance(data, list) else [])
    if not profile_list:
        console.print("[yellow]No profiles found in file.[/yellow]")
        return

    async def _import():
        from app.core.database import async_session_factory
        from app.schemas.profile import ProfileCreate
        from app.services.profile_service import create_profile, list_profiles as _list_all

        logger.info("cli_profiles_import", input_file=input_file, count=len(profile_list))
        async with async_session_factory() as db:
            existing = await _list_all(db)
            existing_names = {p.name for p in existing}
            imported = 0
            skipped = 0

            for item in profile_list:
                name = item.get("name", "")
                if not name:
                    continue
                if skip_existing and name in existing_names:
                    logger.info("cli_profile_import_skip", name=name)
                    skipped += 1
                    continue

                profile_data = ProfileCreate(
                    name=name,
                    provider_name=item.get("provider_name", "kokoro"),
                    language=item.get("language", "en"),
                    description=item.get("description"),
                    voice_id=item.get("voice_id"),
                    tags=item.get("tags"),
                )
                await create_profile(db, profile_data)
                imported += 1

            await db.commit()

        table = Table(title="Import Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right")
        table.add_row("Imported", f"[green]{imported}[/green]")
        table.add_row("Skipped (existing)", f"[yellow]{skipped}[/yellow]")
        table.add_row("Total in file", str(len(profile_list)))
        console.print(table)

    _run(_import())
