"""Self-healing engine — orchestrates monitoring, detection, and remediation."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.healing.detector import AnomalyDetector, AnomalyEvent
from app.healing.mcp_bridge import MCPBridge
from app.healing.monitors import HealthWatchdog, LogStreamMonitor, TelemetryCollector
from app.healing.remediation import RemediationEngine

logger = structlog.get_logger("atlas_vox.healing.engine")


class SelfHealingEngine:
    """Top-level orchestrator for the self-healing subsystem.

    Wires together monitors, the anomaly detector, the remediation engine,
    and the MCP bridge for code-level fixes.
    """

    def __init__(
        self,
        base_url: str | None = None,
        health_interval: float = 30.0,
        telemetry_interval: float = 15.0,
        detection_interval: float = 30.0,
    ):
        if base_url is None:
            from app.core.config import settings
            base_url = f"http://127.0.0.1:{settings.port}"
        # Monitors
        self.health = HealthWatchdog(base_url=base_url, interval=health_interval)
        self.telemetry = TelemetryCollector(
            base_url=base_url, interval=telemetry_interval
        )
        self.logs = LogStreamMonitor()

        # Detection
        self.detector = AnomalyDetector(
            health=self.health,
            telemetry=self.telemetry,
            logs=self.logs,
        )

        # Remediation
        self.remediation = RemediationEngine()
        self.mcp_bridge = MCPBridge()
        self.remediation.mcp_bridge = self.mcp_bridge

        # Control
        self._remediating = False
        self.enabled = True
        self._detection_interval = detection_interval
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._incident_log: list[dict[str, Any]] = []

    async def start(self) -> None:
        """Start all monitors and the detection loop."""
        logger.info("self_healing_engine_starting")
        await self.health.start()
        await self.telemetry.start()
        self._running = True
        self._task = asyncio.create_task(self._detection_loop())
        logger.info("self_healing_engine_started")

    async def stop(self) -> None:
        """Stop all monitors and the detection loop."""
        self._running = False
        if self._task:
            self._task.cancel()
        await self.health.stop()
        await self.telemetry.stop()
        logger.info("self_healing_engine_stopped")

    async def _detection_loop(self) -> None:
        """Periodically check for anomalies and trigger remediation."""
        while self._running:
            try:
                events = self.detector.check_all()
                for event in events:
                    self._remediating = True
                    try:
                        result = await self.remediation.handle(event)
                    finally:
                        self._remediating = False
                    self._incident_log.append(
                        {
                            "event": {
                                "rule": event.rule,
                                "severity": event.severity,
                                "category": event.category,
                                "title": event.title,
                            },
                            "action": result.get("action", "unknown"),
                            "detail": result.get("detail", ""),
                        }
                    )
                    logger.info(
                        "remediation_complete",
                        rule=event.rule,
                        action=result.get("action"),
                    )
                    # Cool down after remediation to avoid feedback loop
                    await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("detection_loop_error", error=str(e))
            await asyncio.sleep(self._detection_interval)

    def get_status(self) -> dict[str, Any]:
        """Return the current status of the self-healing system."""
        return {
            "enabled": self.enabled,
            "running": self._running,
            "uptime_seconds": 0,
            "incidents_handled": len(self._incident_log),
            "health": {
                "healthy": self.health.is_healthy,
                "consecutive_failures": self.health.consecutive_failures,
                "checks_count": len(self.health.history),
            },
            "telemetry": {
                "current_error_rate": round(self.telemetry.current_error_rate, 2),
                "avg_error_rate": round(self.telemetry.avg_error_rate, 2),
                "snapshots_count": len(self.telemetry.history),
            },
            "logs": {
                "errors_last_minute": self.logs.errors_last_minute,
                "errors_last_5_minutes": self.logs.errors_last_5_minutes,
                "total_tracked": len(self.logs.recent_errors),
            },
            "mcp": self.mcp_bridge.status,
        }


# Singleton instance
healing_engine = SelfHealingEngine()
