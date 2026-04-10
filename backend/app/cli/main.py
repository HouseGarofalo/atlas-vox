"""Atlas Vox CLI entry point."""

from __future__ import annotations

import structlog
import typer
from rich.console import Console

logger = structlog.get_logger("atlas_vox.cli")

app = typer.Typer(
    name="atlas-vox",
    help="Atlas Vox — Intelligent Voice Training & Customization Platform",
    no_args_is_help=True,
)
console = Console()


@app.command()
def version() -> None:
    """Show Atlas Vox version."""
    from app.core.config import settings
    logger.info("cli_version_command")
    console.print(f"[bold blue]Atlas Vox[/bold blue] v{settings.app_version}")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to listen on"),
    mcp: bool = typer.Option(False, help="Enable MCP server"),
) -> None:
    """Start the Atlas Vox API server."""
    import uvicorn

    from app.core.config import settings

    logger.info("cli_serve_started", host=host, port=port, mcp_enabled=mcp)
    console.print(f"[bold green]Starting Atlas Vox server[/bold green] on {host}:{port}")
    if mcp:
        console.print("[dim]MCP server enabled[/dim]")

    uvicorn.run("app.main:app", host=host, port=port, reload=settings.debug)


# Register subcommand modules
from app.cli.commands import (  # noqa: E402
    compare,
    init,
    presets,
    profiles,
    providers,
    synthesize,
    train,
)

app.command()(init.init)
app.add_typer(profiles.app, name="profiles", help="Manage voice profiles")
app.add_typer(train.app, name="train", help="Training operations")
app.add_typer(synthesize.app, name="synthesize", help="Text-to-speech synthesis")
app.add_typer(providers.app, name="providers", help="Manage TTS providers")
app.add_typer(compare.app, name="compare", help="Compare voices")
app.add_typer(presets.app, name="presets", help="Manage persona presets")


if __name__ == "__main__":
    app()
