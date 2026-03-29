"""atlas-vox providers — list and manage TTS providers."""

from __future__ import annotations

import asyncio

import structlog
import typer
from rich.console import Console
from rich.table import Table

logger = structlog.get_logger("atlas_vox.cli.providers")

app = typer.Typer()
console = Console()


@app.command("list")
def list_providers() -> None:
    """List all TTS providers with health status."""
    logger.info("providers_list_start")

    async def _list():
        from app.services.provider_registry import provider_registry

        providers = provider_registry.list_all_known()
        logger.info("providers_list_fetched", provider_count=len(providers))

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
                    if health.healthy:
                        logger.debug(
                            "provider_health_check",
                            provider=p["name"],
                            healthy=True,
                            latency_ms=health.latency_ms,
                        )
                        health_str = f"[green]✓ {health.latency_ms}ms[/green]"
                    else:
                        logger.warning(
                            "provider_health_check",
                            provider=p["name"],
                            healthy=False,
                            error=health.error,
                        )
                        health_str = f"[red]✗ {health.error}[/red]"
                    caps = await provider_registry.get_capabilities(p["name"])
                    gpu = caps.gpu_mode
                except Exception as e:
                    logger.error("provider_health_check_error", provider=p["name"], error=str(e))
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
