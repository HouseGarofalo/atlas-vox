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
        elif event.category == "celery":
            return await self._handle_celery_backlog(event)
        elif event.category == "resource":
            return await self._handle_resource_pressure(event)
        elif event.category == "provider":
            return await self._handle_provider_failure(event)
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

    async def _handle_celery_backlog(self, event: AnomalyEvent) -> dict[str, str]:
        """Handle Celery task backlog by clearing stale tasks and optionally restarting workers."""
        try:
            r = redis.Redis.from_url(settings.redis_url, socket_timeout=5)

            # Step 1: Clear stale tasks from known queues
            cleared = 0
            for queue in ("default", "preprocessing", "training"):
                length = r.llen(queue) or 0
                if length > 0:
                    # Keep the most recent 10 tasks, clear the rest
                    if length > 10:
                        trim_count = length - 10
                        r.ltrim(queue, 0, 9)
                        cleared += trim_count

            if cleared > 0:
                logger.info("celery_stale_tasks_cleared", cleared=cleared)

            # Step 2: Try restarting Celery worker if backlog was severe
            if event.value and event.value > 200:
                restart_result = await self._try_celery_worker_restart()
                return {
                    "action": "clear_tasks",
                    "detail": (
                        f"Cleared {cleared} stale tasks. "
                        f"Worker restart: {restart_result.get('detail', 'skipped')}"
                    ),
                }

            return {
                "action": "clear_tasks",
                "detail": f"Cleared {cleared} stale tasks from Celery queues",
            }
        except Exception as e:
            logger.error("celery_backlog_remediation_error", error=str(e))
            return {
                "action": "escalate",
                "detail": f"Failed to clear Celery backlog: {e}",
            }

    async def _handle_resource_pressure(self, event: AnomalyEvent) -> dict[str, str]:
        """Handle resource pressure (memory, disk) by flushing caches."""
        rule = event.rule

        if rule == "memory_pressure":
            # Flush Redis cache to free memory
            return await self._try_flush_redis_cache()

        if rule == "disk_space":
            # Escalate disk space issues — can't safely auto-clean user data
            return {
                "action": "escalate",
                "detail": (
                    f"Disk usage at {event.value:.1f}% "
                    f"(threshold: {event.threshold:.0f}%). "
                    "Manual cleanup required."
                ),
            }

        return {
            "action": "monitor",
            "detail": f"Resource pressure ({rule}), monitoring",
        }

    async def _handle_provider_failure(self, event: AnomalyEvent) -> dict[str, str]:
        """Handle provider failures by auto-disabling the failing provider."""
        # Extract provider name from event title
        # Title format: "Provider 'provider_name' failing (N failures in 5min)"
        provider_name = ""
        title = event.title
        if "'" in title:
            provider_name = title.split("'")[1]

        if not provider_name:
            return {
                "action": "escalate",
                "detail": "Could not determine provider name from event",
            }

        try:
            return await self._try_disable_provider(provider_name)
        except Exception as e:
            logger.error(
                "provider_disable_error",
                provider=provider_name,
                error=str(e),
            )
            return {
                "action": "escalate",
                "detail": f"Failed to disable provider '{provider_name}': {e}",
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

    async def _try_flush_redis_cache(self) -> dict[str, str]:
        """Flush non-critical Redis cache keys to free memory."""
        try:
            r = redis.Redis.from_url(settings.redis_url, socket_timeout=5)

            # Only flush cache keys, not Celery queues or session data
            # Pattern: cache:* keys are safe to flush
            flushed = 0
            cursor = 0
            while True:
                cursor, keys = r.scan(cursor, match="cache:*", count=100)
                if keys:
                    r.delete(*keys)
                    flushed += len(keys)
                if cursor == 0:
                    break

            # Also flush celery result keys older than 1 hour
            cursor = 0
            while True:
                cursor, keys = r.scan(
                    cursor, match="celery-task-meta-*", count=100
                )
                if keys:
                    for key in keys:
                        ttl = r.ttl(key)
                        if ttl == -1:  # No expiry set
                            r.expire(key, 3600)  # Set 1hr expiry
                            flushed += 1
                if cursor == 0:
                    break

            logger.info("redis_cache_flushed", keys_flushed=flushed)
            return {
                "action": "flush_cache",
                "detail": f"Flushed {flushed} cache keys from Redis",
            }
        except Exception as e:
            logger.error("redis_flush_error", error=str(e))
            return {
                "action": "escalate",
                "detail": f"Redis cache flush failed: {e}",
            }

    async def _try_disable_provider(self, provider_name: str) -> dict[str, str]:
        """Disable a failing provider in the database."""
        try:
            from sqlalchemy import update

            from app.core.database import async_session_factory
            from app.models.provider import Provider

            async with async_session_factory() as session:
                result = await session.execute(
                    update(Provider)
                    .where(Provider.name == provider_name)
                    .values(enabled=False)
                )
                await session.commit()

                if result.rowcount > 0:
                    logger.warning(
                        "provider_auto_disabled",
                        provider=provider_name,
                    )
                    return {
                        "action": "disable_provider",
                        "detail": (
                            f"Auto-disabled provider '{provider_name}' "
                            "due to repeated failures"
                        ),
                    }
                return {
                    "action": "escalate",
                    "detail": (
                        f"Provider '{provider_name}' not found in DB"
                    ),
                }
        except Exception as e:
            logger.error(
                "provider_disable_db_error",
                provider=provider_name,
                error=str(e),
            )
            return {
                "action": "escalate",
                "detail": f"DB error disabling provider: {e}",
            }

    async def _try_celery_worker_restart(self) -> dict[str, str]:
        """Attempt to restart the Celery worker container."""
        return await self._try_service_restart("celery-worker")

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
