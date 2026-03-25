"""atlas-vox providers — list and manage TTS providers."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


@app.command("list")
def list_providers() -> None:
    """List all TTS providers with health status."""
    async def _list():
        from app.services.provider_registry import provider_registry

        providers = provider_registry.list_all_known()
        table = Table(title="TTS Providers")
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("Implemented")
        table.add_column("Health")
        table.add_column("GPU Mode", style="dim")

        for p in providers:
            impl = "[green]✓[/green]" if p["implemented"] else "[dim]—[/dim]"
            health_str = "[dim]—[/dim]"
            gpu = "—"

            if p["implemented"]:
                try:
                    health = await provider_registry.health_check(p["name"])
                    health_str = f"[green]✓ {health.latency_ms}ms[/green]" if health.healthy else f"[red]✗ {health.error}[/red]"
                    caps = await provider_registry.get_capabilities(p["name"])
                    gpu = caps.gpu_mode
                except Exception as e:
                    health_str = f"[red]✗ {e}[/red]"

            table.add_row(
                p["display_name"],
                p["provider_type"],
                impl,
                health_str,
                gpu,
            )

        console.print(table)

    asyncio.run(_list())


@app.command("health")
def check_health(
    name: str = typer.Argument(..., help="Provider name"),
) -> None:
    """Run health check on a specific provider."""
    async def _check():
        from app.services.provider_registry import provider_registry

        try:
            health = await provider_registry.health_check(name)
            if health.healthy:
                console.print(f"[green]✓[/green] {name}: healthy (latency: {health.latency_ms}ms)")
            else:
                console.print(f"[red]✗[/red] {name}: {health.error}")
        except ValueError:
            console.print(f"[red]✗[/red] Unknown provider: {name}")

    asyncio.run(_check())
