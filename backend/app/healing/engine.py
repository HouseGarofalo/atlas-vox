"""Self-healing engine — orchestrates monitoring, detection, and remediation."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque
from datetime import UTC, datetime
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
        self._started_at: float | None = None
        self._task: asyncio.Task[None] | None = None
        self._incident_log: deque[dict[str, Any]] = deque(maxlen=500)

    async def start(self) -> None:
        """Start all monitors and the detection loop."""
        # Try to load config from DB before starting
        await self._load_config_from_db()

        # Wire structlog processor chain to feed errors into LogStreamMonitor
        from app.core.logging import set_log_stream_monitor

        set_log_stream_monitor(self.logs)

        logger.info("self_healing_engine_starting")
        await self.health.start()
        await self.telemetry.start()
        self._running = True
        self._started_at = time.monotonic()
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

    async def reconfigure(self) -> dict[str, Any]:
        """Reload configuration from the database without full restart."""
        config = await self._load_config_from_db()
        return {"reconfigured": True, "config": config}

    async def _load_config_from_db(self) -> dict[str, Any]:
        """Load healing settings from the database and apply them."""
        config: dict[str, Any] = {}
        try:
            from app.core.database import async_session_factory
            from app.services.system_settings_service import SystemSettingsService

            async with async_session_factory() as session:
                settings = await SystemSettingsService.get_all(
                    session, category="healing", unmask=True
                )
                for s in settings:
                    config[s["key"]] = s["value"]

            # Apply to detector
            self.detector.reload_config(config)

            # Apply to remediation engine
            if "max_restarts_per_hour" in config:
                self.remediation.max_restarts_per_hour = int(
                    config["max_restarts_per_hour"]
                )
            if "max_fixes_per_hour" in config:
                self.remediation.max_fixes_per_hour = int(
                    config["max_fixes_per_hour"]
                )

            # Apply to MCP bridge
            if config.get("mcp_server_path"):
                from pathlib import Path
                self.mcp_bridge.server_path = Path(config["mcp_server_path"])
            if config.get("project_root"):
                from pathlib import Path
                self.mcp_bridge.project_root = Path(config["project_root"])

            # Apply intervals (only on fresh start, not during reconfigure)
            if not self._running:
                if "health_interval" in config:
                    self.health.interval = float(config["health_interval"])
                if "telemetry_interval" in config:
                    self.telemetry.interval = float(config["telemetry_interval"])
                if "detection_interval" in config:
                    self._detection_interval = float(config["detection_interval"])

            logger.info("healing_config_loaded_from_db", keys=list(config.keys()))
        except Exception as e:
            logger.warning("healing_config_load_error", error=str(e))
        return config

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

                    incident_data = {
                        "event": {
                            "rule": event.rule,
                            "severity": event.severity,
                            "category": event.category,
                            "title": event.title,
                        },
                        "action": result.get("action", "unknown"),
                        "detail": result.get("detail", ""),
                    }
                    self._incident_log.append(incident_data)

                    # Persist incident to database
                    await self._persist_incident(event, result)

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

    async def _persist_incident(
        self, event: AnomalyEvent, result: dict[str, str]
    ) -> None:
        """Write an incident record to the database."""
        try:
            from app.core.database import async_session_factory
            from app.healing.models import Incident

            action = result.get("action", "unknown")
            outcome = "resolved" if action in ("restart", "reconnect", "code_fix", "disable_provider", "clear_tasks", "flush_cache") else (
                "failed" if "failed" in action else "escalated" if action == "escalate" else "pending"
            )

            async with async_session_factory() as session:
                incident = Incident(
                    id=str(uuid.uuid4()),
                    severity=event.severity,
                    category=event.category,
                    title=event.title[:200],
                    description=event.description,
                    detection_rule=event.rule,
                    action_taken=action,
                    action_detail=result.get("detail", "")[:500],
                    outcome=outcome,
                    resolved_at=datetime.now(UTC) if outcome == "resolved" else None,
                )
                session.add(incident)
                await session.commit()
        except Exception as e:
            logger.error("incident_persist_error", error=str(e))

    def get_status(self) -> dict[str, Any]:
        """Return the current status of the self-healing system."""
        return {
            "enabled": self.enabled,
            "running": self._running,
            "uptime_seconds": round(time.monotonic() - self._started_at, 1) if self._started_at else 0,
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
            "detector": {
                "health_failure_threshold": self.detector.health_failure_threshold,
                "error_rate_spike_multiplier": self.detector.error_rate_spike_multiplier,
                "latency_p99_threshold_ms": self.detector.latency_p99_threshold_ms,
                "errors_per_minute_threshold": self.detector.errors_per_minute_threshold,
                "celery_backlog_threshold": self.detector.celery_backlog_threshold,
                "memory_threshold_mb": self.detector.memory_threshold_mb,
                "disk_usage_threshold_pct": self.detector.disk_usage_threshold_pct,
            },
            "mcp": self.mcp_bridge.status,
        }


# Singleton instance
healing_engine = SelfHealingEngine()
