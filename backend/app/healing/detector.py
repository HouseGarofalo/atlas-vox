"""Anomaly detection rules for the self-healing system."""

from __future__ import annotations

import time
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
    ):
        self.health = health
        self.telemetry = telemetry
        self.logs = logs
        self.health_failure_threshold = health_failure_threshold
        self.error_rate_spike_multiplier = error_rate_spike_multiplier
        self.latency_p99_threshold_ms = latency_p99_threshold_ms
        self.errors_per_minute_threshold = errors_per_minute_threshold
        self._last_check = 0.0
        self._suppressed: dict[str, float] = {}  # rule -> last_fired timestamp

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

        # Rule 4: Latency degradation (check telemetry endpoint_latencies)
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

        for event in events:
            logger.warning(
                "anomaly_detected",
                rule=event.rule,
                severity=event.severity,
                title=event.title,
            )

        return events

    def _should_fire(self, rule: str, now: float, cooldown: float) -> bool:
        last = self._suppressed.get(rule, 0)
        if now - last < cooldown:
            return False
        self._suppressed[rule] = now
        return True
