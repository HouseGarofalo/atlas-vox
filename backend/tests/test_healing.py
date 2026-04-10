"""Tests for the self-healing subsystem components."""

from __future__ import annotations

import time
from collections import deque
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.healing.detector import AnomalyDetector, AnomalyEvent
from app.healing.monitors import HealthWatchdog, LogStreamMonitor, TelemetryCollector
from app.healing.remediation import RemediationEngine


# --- Detector Tests ---


class TestAnomalyDetector:
    """Tests for AnomalyDetector detection rules."""

    def _make_detector(self, **kwargs):
        health = MagicMock(spec=HealthWatchdog)
        health.consecutive_failures = 0
        health.latest = None
        telemetry = MagicMock(spec=TelemetryCollector)
        telemetry.current_error_rate = 0.0
        telemetry.avg_error_rate = 0.0
        telemetry.history = []
        logs = MagicMock(spec=LogStreamMonitor)
        logs.errors_last_minute = 0
        logs.latest_errors = []
        return AnomalyDetector(health=health, telemetry=telemetry, logs=logs, **kwargs)

    def test_no_anomalies_when_healthy(self):
        detector = self._make_detector()
        events = detector.check_all()
        assert events == []

    def test_health_failure_rule(self):
        detector = self._make_detector(health_failure_threshold=3)
        detector.health.consecutive_failures = 5
        detector.health.latest = MagicMock(checks={"database": "ok", "redis": "fail"})
        events = detector.check_all()
        health_events = [e for e in events if e.rule == "health_failure"]
        assert len(health_events) == 1
        assert health_events[0].severity == "critical"

    def test_error_rate_spike_rule(self):
        detector = self._make_detector(error_rate_spike_multiplier=3.0)
        detector.telemetry.current_error_rate = 15.0
        detector.telemetry.avg_error_rate = 3.0  # 15/3 = 5x > 3x threshold
        events = detector.check_all()
        spike_events = [e for e in events if e.rule == "error_rate_spike"]
        assert len(spike_events) == 1
        assert spike_events[0].severity == "warning"

    def test_error_volume_rule(self):
        detector = self._make_detector(errors_per_minute_threshold=10)
        detector.logs.errors_last_minute = 15
        detector.logs.latest_errors = [MagicMock(event="test error")]
        events = detector.check_all()
        volume_events = [e for e in events if e.rule == "error_volume"]
        assert len(volume_events) == 1

    def test_cooldown_suppresses_repeat_fire(self):
        detector = self._make_detector(health_failure_threshold=1)
        detector.health.consecutive_failures = 5
        detector.health.latest = MagicMock(checks={})
        # First check fires
        events1 = detector.check_all()
        assert len([e for e in events1 if e.rule == "health_failure"]) == 1
        # Second check within cooldown should NOT fire
        events2 = detector.check_all()
        assert len([e for e in events2 if e.rule == "health_failure"]) == 0

    def test_reload_config(self):
        detector = self._make_detector()
        detector.reload_config({
            "health_failure_threshold": "10",
            "error_rate_spike_multiplier": "5.0",
            "memory_threshold_mb": "4096",
        })
        assert detector.health_failure_threshold == 10
        assert detector.error_rate_spike_multiplier == 5.0
        assert detector.memory_threshold_mb == 4096

    def test_provider_failure_rule(self):
        detector = self._make_detector()
        now = time.time()
        # Record 3 failures in last 5 minutes
        detector.record_provider_failure("elevenlabs")
        detector.record_provider_failure("elevenlabs")
        detector.record_provider_failure("elevenlabs")
        events = detector.check_all()
        provider_events = [e for e in events if e.rule == "provider_failure"]
        assert len(provider_events) == 1
        assert "elevenlabs" in provider_events[0].title


# --- LogStreamMonitor Tests ---


class TestLogStreamMonitor:
    def test_ingest_error(self):
        monitor = LogStreamMonitor()
        monitor.ingest(level="error", event="test error", logger_name="test")
        assert len(monitor.recent_errors) == 1
        assert monitor.errors_last_minute == 1

    def test_ingest_info_ignored(self):
        monitor = LogStreamMonitor()
        monitor.ingest(level="info", event="test info", logger_name="test")
        assert len(monitor.recent_errors) == 0

    def test_errors_last_minute(self):
        monitor = LogStreamMonitor()
        monitor.ingest(level="error", event="e1", logger_name="test")
        monitor.ingest(level="error", event="e2", logger_name="test")
        assert monitor.errors_last_minute == 2

    def test_latest_errors_limited(self):
        monitor = LogStreamMonitor()
        for i in range(20):
            monitor.ingest(level="error", event=f"error {i}", logger_name="test")
        # latest_errors returns last 10
        assert len(monitor.latest_errors) == 10


# --- RemediationEngine Tests ---


class TestRemediationEngine:
    @pytest.mark.asyncio
    async def test_handle_health_failure_redis(self):
        engine = RemediationEngine()
        event = AnomalyEvent(
            rule="health_failure",
            severity="critical",
            category="health",
            title="Health failing",
            description="Failed checks: redis",
        )
        with patch("app.healing.remediation.redis") as mock_redis:
            mock_r = MagicMock()
            mock_r.ping.return_value = True
            mock_redis.Redis.from_url.return_value = mock_r
            result = await engine.handle(event)
            assert result["action"] == "reconnect"

    @pytest.mark.asyncio
    async def test_handle_health_failure_database(self):
        engine = RemediationEngine()
        event = AnomalyEvent(
            rule="health_failure",
            severity="critical",
            category="health",
            title="Health failing",
            description="Failed checks: database",
        )
        result = await engine.handle(event)
        assert result["action"] == "escalate"

    @pytest.mark.asyncio
    async def test_handle_celery_backlog(self):
        engine = RemediationEngine()
        event = AnomalyEvent(
            rule="celery_backlog",
            severity="warning",
            category="celery",
            title="Celery backlog: 150 pending tasks",
            description="Threshold: 100",
            value=150.0,
            threshold=100.0,
        )
        with patch("app.healing.remediation.redis") as mock_redis:
            mock_r = MagicMock()
            mock_r.llen.return_value = 50
            mock_r.ltrim.return_value = True
            mock_redis.Redis.from_url.return_value = mock_r
            result = await engine.handle(event)
            assert result["action"] == "clear_tasks"

    @pytest.mark.asyncio
    async def test_handle_memory_pressure(self):
        engine = RemediationEngine()
        event = AnomalyEvent(
            rule="memory_pressure",
            severity="warning",
            category="resource",
            title="Memory pressure: 3000MB RSS",
            description="Threshold: 2048MB",
            value=3000.0,
            threshold=2048.0,
        )
        with patch("app.healing.remediation.redis") as mock_redis:
            mock_r = MagicMock()
            mock_r.scan.return_value = (0, [])
            mock_redis.Redis.from_url.return_value = mock_r
            result = await engine.handle(event)
            assert result["action"] == "flush_cache"

    @pytest.mark.asyncio
    async def test_handle_disk_space(self):
        engine = RemediationEngine()
        event = AnomalyEvent(
            rule="disk_space",
            severity="warning",
            category="resource",
            title="Disk usage: 95%",
            description="Threshold: 90%",
            value=95.0,
            threshold=90.0,
        )
        result = await engine.handle(event)
        assert result["action"] == "escalate"

    @pytest.mark.asyncio
    async def test_handle_provider_failure(self):
        engine = RemediationEngine()
        event = AnomalyEvent(
            rule="provider_failure",
            severity="warning",
            category="provider",
            title="Provider 'elevenlabs' failing (3 failures in 5min)",
            description="Auto-disable recommended",
            value=3.0,
            threshold=3.0,
        )
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_session
        mock_ctx.__aexit__.return_value = None

        with patch("app.core.database.async_session_factory", return_value=mock_ctx):
            result = await engine.handle(event)
            assert result["action"] == "disable_provider"

    @pytest.mark.asyncio
    async def test_handle_error_rate_with_mcp(self):
        engine = RemediationEngine()
        mock_bridge = AsyncMock()
        mock_bridge.request_fix.return_value = "Fixed the issue"
        engine.mcp_bridge = mock_bridge

        event = AnomalyEvent(
            rule="error_rate_spike",
            severity="critical",
            category="error_rate",
            title="Error rate spike",
            description="5x above baseline",
        )
        result = await engine.handle(event)
        assert result["action"] == "code_fix"

    @pytest.mark.asyncio
    async def test_restart_rate_limit(self):
        engine = RemediationEngine(max_restarts_per_hour=2)
        # Fill up restart timestamps
        now = time.time()
        engine._restart_timestamps.extend([now, now])

        event = AnomalyEvent(
            rule="health_failure",
            severity="critical",
            category="health",
            title="Health failing",
            description="Failed checks: general",
        )
        result = await engine.handle(event)
        assert result["action"] == "escalate"
        assert "Restart limit" in result["detail"]

    @pytest.mark.asyncio
    async def test_handle_unknown_category(self):
        engine = RemediationEngine()
        event = AnomalyEvent(
            rule="unknown",
            severity="info",
            category="unknown_category",
            title="Unknown",
            description="Unknown event",
        )
        result = await engine.handle(event)
        assert result["action"] == "none"


# --- MCP Bridge Tests ---


class TestMCPBridge:
    def test_status_property(self):
        from app.healing.mcp_bridge import MCPBridge
        bridge = MCPBridge()
        status = bridge.status
        assert "enabled" in status
        assert "server_path" in status
        assert "project_root" in status
        assert "fixes_this_hour" in status
        assert "total_fixes" in status
        assert "recent_fixes" in status

    def test_rate_limiting(self):
        from app.healing.mcp_bridge import MCPBridge
        bridge = MCPBridge(max_fixes_per_hour=3)
        now = time.time()
        bridge._fix_timestamps.extend([now, now, now])
        assert bridge._fixes_this_hour() == 3

    @pytest.mark.asyncio
    async def test_request_fix_disabled(self):
        from app.healing.mcp_bridge import MCPBridge
        bridge = MCPBridge()
        bridge.enabled = False
        event = AnomalyEvent(
            rule="test", severity="warning", category="test",
            title="Test", description="Test",
        )
        result = await bridge.request_fix(event)
        assert result == "MCP bridge disabled"

    @pytest.mark.asyncio
    async def test_request_fix_rate_limited(self):
        from app.healing.mcp_bridge import MCPBridge
        bridge = MCPBridge(max_fixes_per_hour=1)
        bridge._fix_timestamps.append(time.time())
        event = AnomalyEvent(
            rule="test", severity="warning", category="test",
            title="Test", description="Test",
        )
        result = await bridge.request_fix(event)
        assert "Rate limited" in result

    @pytest.mark.asyncio
    async def test_test_connection(self):
        from app.healing.mcp_bridge import MCPBridge
        bridge = MCPBridge()
        result = await bridge.test_connection()
        assert "claude_cli_found" in result
        assert "server_path_valid" in result
        assert "project_root_valid" in result
        assert "ready" in result
        assert isinstance(result["ready"], bool)


# --- Healing API Endpoint Tests ---


@pytest.mark.asyncio
async def test_healing_status_endpoint(client):
    """GET /api/v1/healing/status returns status."""
    response = await client.get("/api/v1/healing/status")
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "running" in data
    assert "health" in data
    assert "telemetry" in data
    assert "logs" in data
    assert "detector" in data


@pytest.mark.asyncio
async def test_healing_incidents_endpoint(client):
    """GET /api/v1/healing/incidents returns incidents."""
    response = await client.get("/api/v1/healing/incidents")
    assert response.status_code == 200
    data = response.json()
    assert "incidents" in data
    assert "count" in data


@pytest.mark.asyncio
async def test_healing_mcp_status_endpoint(client):
    """GET /api/v1/healing/mcp/status returns MCP status."""
    response = await client.get("/api/v1/healing/mcp/status")
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "fixes_this_hour" in data


@pytest.mark.asyncio
async def test_healing_reconfigure_endpoint(client):
    """POST /api/v1/healing/reconfigure works."""
    response = await client.post("/api/v1/healing/reconfigure")
    assert response.status_code == 200
    data = response.json()
    assert data["reconfigured"] is True


@pytest.mark.asyncio
async def test_healing_mcp_test_endpoint(client):
    """POST /api/v1/healing/mcp/test returns test results."""
    response = await client.post("/api/v1/healing/mcp/test")
    assert response.status_code == 200
    data = response.json()
    assert "claude_cli_found" in data
    assert "ready" in data
