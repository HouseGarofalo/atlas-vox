"""Anomaly detection rules for the self-healing system."""

from __future__ import annotations

import os
import shutil
import time
from collections import deque
from dataclasses import dataclass

import structlog

from app.healing.monitors import HealthWatchdog, LogStreamMonitor, TelemetryCollector

logger = structlog.get_logger("atlas_vox.healing.detector")


@dataclass
class AnomalyEvent:
    rule: str
    severity: str  # info, warning, critical
    category: str
    title: str
    description: str
    value: float | None = None
    threshold: float | None = None


class AnomalyDetector:
    """Evaluates monitoring data against configurable detection rules."""

    def __init__(
        self,
        health: HealthWatchdog,
        telemetry: TelemetryCollector,
        logs: LogStreamMonitor,
        *,
        health_failure_threshold: int = 3,
        error_rate_spike_multiplier: float = 3.0,
        latency_p99_threshold_ms: float = 5000.0,
        errors_per_minute_threshold: int = 10,
        celery_backlog_threshold: int = 100,
        memory_threshold_mb: int = 2048,
        disk_usage_threshold_pct: int = 90,
    ):
        self.health = health
        self.telemetry = telemetry
        self.logs = logs
        self.health_failure_threshold = health_failure_threshold
        self.error_rate_spike_multiplier = error_rate_spike_multiplier
        self.latency_p99_threshold_ms = latency_p99_threshold_ms
        self.errors_per_minute_threshold = errors_per_minute_threshold
        self.celery_backlog_threshold = celery_backlog_threshold
        self.memory_threshold_mb = memory_threshold_mb
        self.disk_usage_threshold_pct = disk_usage_threshold_pct
        self._last_check = 0.0
        self._suppressed: dict[str, float] = {}  # rule -> last_fired timestamp
        # Track provider health failures: provider_name -> deque of failure timestamps
        self._provider_failures: dict[str, deque[float]] = {}

    def reload_config(self, config: dict) -> None:
        """Reload detection thresholds from a config dict (e.g., from DB)."""
        if "health_failure_threshold" in config:
            self.health_failure_threshold = int(config["health_failure_threshold"])
        if "error_rate_spike_multiplier" in config:
            self.error_rate_spike_multiplier = float(config["error_rate_spike_multiplier"])
        if "latency_p99_threshold_ms" in config:
            self.latency_p99_threshold_ms = float(config["latency_p99_threshold_ms"])
        if "errors_per_minute_threshold" in config:
            self.errors_per_minute_threshold = int(config["errors_per_minute_threshold"])
        if "celery_backlog_threshold" in config:
            self.celery_backlog_threshold = int(config["celery_backlog_threshold"])
        if "memory_threshold_mb" in config:
            self.memory_threshold_mb = int(config["memory_threshold_mb"])
        if "disk_usage_threshold_pct" in config:
            self.disk_usage_threshold_pct = int(config["disk_usage_threshold_pct"])
        logger.info("detector_config_reloaded", config=config)

    def record_provider_failure(self, provider_name: str) -> None:
        """Record a provider health check failure for the provider-failure rule."""
        if provider_name not in self._provider_failures:
            self._provider_failures[provider_name] = deque(maxlen=50)
        self._provider_failures[provider_name].append(time.time())

    def check_all(self) -> list[AnomalyEvent]:
        """Run all detection rules and return any triggered anomalies."""
        now = time.time()
        self._last_check = now
        events: list[AnomalyEvent] = []

        # Rule 1: Consecutive health failures
        if self.health.consecutive_failures >= self.health_failure_threshold:
            if self._should_fire("health_failure", now, cooldown=120):
                checks = self.health.latest.checks if self.health.latest else {}
                failed = [k for k, v in checks.items() if v != "ok"]
                events.append(
                    AnomalyEvent(
                        rule="health_failure",
                        severity="critical",
                        category="health",
                        title=f"Health check failing ({self.health.consecutive_failures} consecutive)",
                        description=f"Failed checks: {', '.join(failed) or 'all'}",
                        value=float(self.health.consecutive_failures),
                        threshold=float(self.health_failure_threshold),
                    )
                )

        # Rule 2: Error rate spike
        current = self.telemetry.current_error_rate
        baseline = self.telemetry.avg_error_rate
        if baseline > 0 and current > baseline * self.error_rate_spike_multiplier:
            if self._should_fire("error_rate_spike", now, cooldown=120):
                events.append(
                    AnomalyEvent(
                        rule="error_rate_spike",
                        severity="warning",
                        category="error_rate",
                        title=f"Error rate spike: {current:.1f}% (baseline: {baseline:.1f}%)",
                        description=f"Current error rate is {current / baseline:.1f}x above baseline",
                        value=current,
                        threshold=baseline * self.error_rate_spike_multiplier,
                    )
                )

        # Rule 3: High error volume
        errors_1m = self.logs.errors_last_minute
        if errors_1m >= self.errors_per_minute_threshold:
            if self._should_fire("error_volume", now, cooldown=120):
                recent = self.logs.latest_errors
                sample = recent[0].event if recent else "unknown"
                events.append(
                    AnomalyEvent(
                        rule="error_volume",
                        severity="warning",
                        category="error_rate",
                        title=f"{errors_1m} errors in the last minute",
                        description=f"Latest: {sample}",
                        value=float(errors_1m),
                        threshold=float(self.errors_per_minute_threshold),
                    )
                )

        # Rule 4: Latency degradation
        if self.telemetry.history:
            latest = self.telemetry.history[-1]
            for endpoint, stats in latest.endpoint_latencies.items():
                p99 = stats.get("p99", 0)
                if p99 > self.latency_p99_threshold_ms:
                    if self._should_fire(f"latency_{endpoint}", now, cooldown=300):
                        events.append(
                            AnomalyEvent(
                                rule="latency_degradation",
                                severity="warning",
                                category="latency",
                                title=f"High latency on {endpoint}: p99={p99:.0f}ms",
                                description=f"Threshold: {self.latency_p99_threshold_ms}ms",
                                value=p99,
                                threshold=self.latency_p99_threshold_ms,
                            )
                        )

        # Rule 5: Celery backlog
        events.extend(self._check_celery_backlog(now))

        # Rule 6: Memory pressure
        events.extend(self._check_memory_pressure(now))

        # Rule 7: Disk space
        events.extend(self._check_disk_space(now))

        # Rule 8: Provider failure (3x in 5 minutes -> auto-disable)
        events.extend(self._check_provider_failures(now))

        for event in events:
            logger.warning(
                "anomaly_detected",
                rule=event.rule,
                severity=event.severity,
                title=event.title,
            )

        return events

    def _check_celery_backlog(self, now: float) -> list[AnomalyEvent]:
        """Rule 5: Check for Celery task backlog."""
        events: list[AnomalyEvent] = []
        try:
            import redis as redis_lib

            from app.core.config import settings

            r = redis_lib.Redis.from_url(settings.redis_url, socket_timeout=2)
            # Check all known queues
            total_pending = 0
            for queue in ("default", "preprocessing", "training"):
                length = r.llen(queue) or 0
                total_pending += length

            if total_pending >= self.celery_backlog_threshold:
                if self._should_fire("celery_backlog", now, cooldown=120):
                    events.append(
                        AnomalyEvent(
                            rule="celery_backlog",
                            severity="warning",
                            category="celery",
                            title=f"Celery backlog: {total_pending} pending tasks",
                            description=f"Threshold: {self.celery_backlog_threshold}",
                            value=float(total_pending),
                            threshold=float(self.celery_backlog_threshold),
                        )
                    )
        except Exception as e:
            logger.debug("celery_backlog_check_error", error=str(e))
        return events

    def _check_memory_pressure(self, now: float) -> list[AnomalyEvent]:
        """Rule 6: Check Python process RSS memory usage."""
        events: list[AnomalyEvent] = []
        try:
            import psutil

            process = psutil.Process(os.getpid())
            rss_mb = process.memory_info().rss / (1024 * 1024)
            if rss_mb > self.memory_threshold_mb:
                if self._should_fire("memory_pressure", now, cooldown=300):
                    events.append(
                        AnomalyEvent(
                            rule="memory_pressure",
                            severity="warning",
                            category="resource",
                            title=f"Memory pressure: {rss_mb:.0f}MB RSS",
                            description=f"Threshold: {self.memory_threshold_mb}MB",
                            value=rss_mb,
                            threshold=float(self.memory_threshold_mb),
                        )
                    )
        except ImportError:
            pass  # psutil not installed
        except Exception as e:
            logger.debug("memory_check_error", error=str(e))
        return events

    def _check_disk_space(self, now: float) -> list[AnomalyEvent]:
        """Rule 7: Check storage directory disk usage."""
        events: list[AnomalyEvent] = []
        try:
            from app.core.config import settings

            storage_path = str(settings.storage_path)
            if os.path.exists(storage_path):
                usage = shutil.disk_usage(storage_path)
                pct_used = (usage.used / usage.total) * 100
                if pct_used > self.disk_usage_threshold_pct:
                    if self._should_fire("disk_space", now, cooldown=600):
                        events.append(
                            AnomalyEvent(
                                rule="disk_space",
                                severity="warning",
                                category="resource",
                                title=f"Disk usage: {pct_used:.1f}% ({usage.free // (1024**3)}GB free)",
                                description=f"Threshold: {self.disk_usage_threshold_pct}%",
                                value=pct_used,
                                threshold=float(self.disk_usage_threshold_pct),
                            )
                        )
        except Exception as e:
            logger.debug("disk_check_error", error=str(e))
        return events

    def _check_provider_failures(self, now: float) -> list[AnomalyEvent]:
        """Rule 8: Provider health fails 3x in 5 minutes -> auto-disable."""
        events: list[AnomalyEvent] = []
        cutoff = now - 300  # 5 minutes
        for provider_name, timestamps in self._provider_failures.items():
            recent = sum(1 for t in timestamps if t > cutoff)
            if recent >= 3:
                if self._should_fire(f"provider_failure_{provider_name}", now, cooldown=600):
                    events.append(
                        AnomalyEvent(
                            rule="provider_failure",
                            severity="warning",
                            category="provider",
                            title=f"Provider '{provider_name}' failing ({recent} failures in 5min)",
                            description="Auto-disable recommended",
                            value=float(recent),
                            threshold=3.0,
                        )
                    )
        return events

    def _should_fire(self, rule: str, now: float, cooldown: float) -> bool:
        last = self._suppressed.get(rule, 0)
        if now - last < cooldown:
            return False
        self._suppressed[rule] = now
        return True
