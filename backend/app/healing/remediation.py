"""Remediation actions for the self-healing system."""

from __future__ import annotations

import asyncio
import subprocess
import time
from collections import deque
from typing import Any

import redis
import structlog

from app.core.config import settings
from app.healing.detector import AnomalyEvent

logger = structlog.get_logger("atlas_vox.healing.remediation")


class RemediationEngine:
    """Executes remediation actions based on detected anomalies."""

    def __init__(
        self, max_restarts_per_hour: int = 5, max_fixes_per_hour: int = 3
    ):
        self.max_restarts_per_hour = max_restarts_per_hour
        self.max_fixes_per_hour = max_fixes_per_hour
        self._restart_timestamps: deque[float] = deque(maxlen=100)
        self._fix_timestamps: deque[float] = deque(maxlen=100)
        self.mcp_bridge: Any = None  # Set by engine when Phase 3 is active

    def _restarts_this_hour(self) -> int:
        cutoff = time.time() - 3600
        return sum(1 for t in self._restart_timestamps if t > cutoff)

    def _fixes_this_hour(self) -> int:
        cutoff = time.time() - 3600
        return sum(1 for t in self._fix_timestamps if t > cutoff)

    async def handle(self, event: AnomalyEvent) -> dict[str, str]:
        """Determine and execute the appropriate remediation action."""
        logger.info(
            "remediation_start",
            rule=event.rule,
            severity=event.severity,
            category=event.category,
        )

        if event.category == "health":
            return await self._handle_health_failure(event)
        elif event.category == "error_rate":
            return await self._handle_error_rate(event)
        elif event.category == "latency":
            return await self._handle_latency(event)
        else:
            return {
                "action": "none",
                "detail": f"No handler for category: {event.category}",
            }

    async def _handle_health_failure(self, event: AnomalyEvent) -> dict[str, str]:
        """Handle health check failures."""
        desc = event.description.lower()

        # Redis failure -> try reconnect
        if "redis" in desc:
            return await self._try_redis_reconnect()

        # DB failure -> log and escalate (can't self-fix)
        if "database" in desc:
            return {
                "action": "escalate",
                "detail": "Database failure requires manual intervention",
            }

        # Storage failure -> check disk space
        if "storage" in desc:
            return {
                "action": "escalate",
                "detail": "Storage failure — check disk space",
            }

        # General health failure -> try restart if under limit
        if self._restarts_this_hour() < self.max_restarts_per_hour:
            return await self._try_service_restart("backend")
        return {
            "action": "escalate",
            "detail": f"Restart limit reached ({self.max_restarts_per_hour}/hr)",
        }

    async def _handle_error_rate(self, event: AnomalyEvent) -> dict[str, str]:
        """Handle error rate spikes."""
        if event.severity == "critical" and self.mcp_bridge:
            if self._fixes_this_hour() < self.max_fixes_per_hour:
                self._fix_timestamps.append(time.time())
                return await self._request_code_fix(event)
        return {
            "action": "monitor",
            "detail": "Error rate elevated, monitoring for resolution",
        }

    async def _handle_latency(self, event: AnomalyEvent) -> dict[str, str]:
        """Handle latency degradation."""
        return {
            "action": "monitor",
            "detail": f"Latency on {event.title}, monitoring",
        }

    async def _try_redis_reconnect(self) -> dict[str, str]:
        """Attempt to reconnect to Redis."""
        try:
            r = redis.Redis.from_url(settings.redis_url, socket_timeout=5)
            r.ping()
            logger.info("redis_reconnect_success")
            return {"action": "reconnect", "detail": "Redis reconnected successfully"}
        except Exception as e:
            logger.error("redis_reconnect_failed", error=str(e))
            return {"action": "escalate", "detail": f"Redis reconnect failed: {e}"}

    async def _try_service_restart(self, service: str) -> dict[str, str]:
        """Attempt to restart a Docker service."""
        self._restart_timestamps.append(time.time())
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["docker", "restart", f"atlas-vox-{service}-1"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                logger.info("service_restart_success", service=service)
                return {
                    "action": "restart",
                    "detail": f"Restarted {service} container",
                }
            logger.warning(
                "service_restart_failed",
                service=service,
                stderr=result.stderr[:200],
            )
            return {"action": "restart_failed", "detail": result.stderr[:200]}
        except Exception as e:
            logger.error("service_restart_error", service=service, error=str(e))
            return {"action": "restart_failed", "detail": str(e)}

    async def _request_code_fix(self, event: AnomalyEvent) -> dict[str, str]:
        """Request a code fix via Claude Code MCP (Phase 3)."""
        if not self.mcp_bridge:
            return {
                "action": "escalate",
                "detail": "MCP bridge not configured",
            }
        try:
            result = await self.mcp_bridge.request_fix(event)
            return {"action": "code_fix", "detail": result}
        except Exception as e:
            logger.error("mcp_fix_error", error=str(e))
            return {"action": "code_fix_failed", "detail": str(e)}
