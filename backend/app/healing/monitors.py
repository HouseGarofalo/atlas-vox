"""Monitoring components for the self-healing system."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field

import httpx
import structlog

logger = structlog.get_logger("atlas_vox.healing")


@dataclass
class HealthSnapshot:
    timestamp: float
    healthy: bool
    checks: dict[str, str] = field(default_factory=dict)
    error: str | None = None


@dataclass
class TelemetrySnapshot:
    timestamp: float
    total_requests: int = 0
    total_errors: int = 0
    error_rate: float = 0.0
    status_counts: dict[str, int] = field(default_factory=dict)
    endpoint_latencies: dict[str, dict] = field(default_factory=dict)


@dataclass
class LogEvent:
    timestamp: float
    level: str
    event: str
    logger_name: str
    error: str | None = None
    extra: dict = field(default_factory=dict)


class HealthWatchdog:
    """Polls the health endpoint and tracks consecutive failures."""

    def __init__(
        self, base_url: str = "http://127.0.0.1:8100", interval: float = 30.0
    ):
        self.base_url = base_url
        self.interval = interval
        self.history: deque[HealthSnapshot] = deque(maxlen=100)
        self.consecutive_failures = 0
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("health_watchdog_started", interval=self.interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def check_now(self) -> HealthSnapshot:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/api/v1/health")
                data = resp.json()
                snap = HealthSnapshot(
                    timestamp=time.time(),
                    healthy=data.get("status") == "healthy",
                    checks=data.get("checks", {}),
                )
                if snap.healthy:
                    self.consecutive_failures = 0
                else:
                    self.consecutive_failures += 1
                self.history.append(snap)
                return snap
        except Exception as e:
            self.consecutive_failures += 1
            snap = HealthSnapshot(timestamp=time.time(), healthy=False, error=str(e))
            self.history.append(snap)
            return snap

    async def _loop(self) -> None:
        while self._running:
            try:
                snap = await self.check_now()
                if not snap.healthy:
                    logger.warning(
                        "health_check_failed",
                        consecutive=self.consecutive_failures,
                        error=snap.error,
                        checks=snap.checks,
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("health_watchdog_error", error=str(e))
            # Exponential backoff when failing to avoid self-DDoS
            if self.consecutive_failures > 0:
                backoff = min(self.interval * (2 ** min(self.consecutive_failures, 5)), 300)
                await asyncio.sleep(backoff)
            else:
                await asyncio.sleep(self.interval)

    @property
    def is_healthy(self) -> bool:
        if not self.history:
            return True
        return self.history[-1].healthy

    @property
    def latest(self) -> HealthSnapshot | None:
        return self.history[-1] if self.history else None


class TelemetryCollector:
    """Polls the telemetry endpoint and computes error rate trends."""

    def __init__(
        self, base_url: str = "http://127.0.0.1:8100", interval: float = 15.0
    ):
        self.base_url = base_url
        self.interval = interval
        self.history: deque[TelemetrySnapshot] = deque(maxlen=200)
        self._running = False
        self._task: asyncio.Task | None = None
        self._prev_errors = 0
        self._prev_requests = 0

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("telemetry_collector_started", interval=self.interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def collect_now(self) -> TelemetrySnapshot:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/api/v1/telemetry")
                data = resp.json()
                total_req = data.get("total_requests", 0)
                total_err = data.get("total_errors", 0)
                delta_req = max(total_req - self._prev_requests, 0)
                delta_err = max(total_err - self._prev_errors, 0)
                error_rate = (delta_err / delta_req * 100) if delta_req > 0 else 0.0
                self._prev_requests = total_req
                self._prev_errors = total_err
                snap = TelemetrySnapshot(
                    timestamp=time.time(),
                    total_requests=total_req,
                    total_errors=total_err,
                    error_rate=error_rate,
                    status_counts=data.get("status_counts", {}),
                    endpoint_latencies=data.get("endpoint_latencies", {}),
                )
                self.history.append(snap)
                return snap
        except Exception as e:
            logger.error("telemetry_collect_error", error=str(e))
            snap = TelemetrySnapshot(timestamp=time.time())
            self.history.append(snap)
            return snap

    async def _loop(self) -> None:
        while self._running:
            try:
                await self.collect_now()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("telemetry_collector_error", error=str(e))
            await asyncio.sleep(self.interval)

    @property
    def current_error_rate(self) -> float:
        if not self.history:
            return 0.0
        return self.history[-1].error_rate

    @property
    def avg_error_rate(self) -> float:
        if len(self.history) < 2:
            return 0.0
        recent = list(self.history)[-20:]
        rates = [s.error_rate for s in recent]
        return sum(rates) / len(rates) if rates else 0.0


class LogStreamMonitor:
    """Watches for error patterns in structured log output."""

    def __init__(self, max_errors: int = 500):
        self.recent_errors: deque[LogEvent] = deque(maxlen=max_errors)
        self.error_count_window: deque[float] = deque(maxlen=1000)
        self._running = False

    def ingest(
        self,
        level: str,
        event: str,
        logger_name: str = "",
        error: str | None = None,
        **extra: object,
    ) -> None:
        """Call this from the structlog processor chain to feed log events."""
        if level in ("error", "critical", "exception"):
            log_event = LogEvent(
                timestamp=time.time(),
                level=level,
                event=event,
                logger_name=logger_name,
                error=error,
                extra=extra,
            )
            self.recent_errors.append(log_event)
            self.error_count_window.append(time.time())

    @property
    def errors_last_minute(self) -> int:
        cutoff = time.time() - 60
        return sum(1 for t in self.error_count_window if t > cutoff)

    @property
    def errors_last_5_minutes(self) -> int:
        cutoff = time.time() - 300
        return sum(1 for t in self.error_count_window if t > cutoff)

    @property
    def latest_errors(self) -> list[LogEvent]:
        return list(self.recent_errors)[-10:]
