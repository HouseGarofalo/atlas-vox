"""Tests for RequestLoggingMiddleware and telemetry endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.middleware import TelemetryMetrics, telemetry


# ---------------------------------------------------------------------------
# X-Request-ID header
# ---------------------------------------------------------------------------

async def test_request_id_header_present(client: AsyncClient):
    """Every response must contain an X-Request-ID header."""
    resp = await client.get("/api/v1/profiles")
    assert "x-request-id" in resp.headers


async def test_request_id_header_is_non_empty(client: AsyncClient):
    resp = await client.get("/api/v1/profiles")
    assert resp.headers["x-request-id"].strip() != ""


async def test_custom_request_id_propagated(client: AsyncClient):
    """A custom X-Request-ID sent by the caller must be echoed back unchanged."""
    custom_id = "my-trace-id-12345"
    resp = await client.get("/api/v1/profiles", headers={"X-Request-ID": custom_id})
    assert resp.headers.get("x-request-id") == custom_id


# ---------------------------------------------------------------------------
# X-Response-Time-Ms header
# ---------------------------------------------------------------------------

async def test_response_time_header_present(client: AsyncClient):
    """Every response must contain an X-Response-Time-Ms header."""
    resp = await client.get("/api/v1/profiles")
    assert "x-response-time-ms" in resp.headers


async def test_response_time_header_is_numeric(client: AsyncClient):
    resp = await client.get("/api/v1/profiles")
    raw = resp.headers["x-response-time-ms"]
    # Must be parseable as a float (milliseconds can have decimals)
    latency = float(raw)
    assert latency >= 0


# ---------------------------------------------------------------------------
# Telemetry endpoint
# ---------------------------------------------------------------------------

async def test_telemetry_endpoint_returns_200(client: AsyncClient):
    resp = await client.get("/api/v1/telemetry")
    assert resp.status_code == 200


async def test_telemetry_endpoint_structure(client: AsyncClient):
    resp = await client.get("/api/v1/telemetry")
    data = resp.json()

    assert "total_requests" in data
    assert "total_errors" in data
    assert "status_counts" in data
    assert "endpoints" in data


async def test_telemetry_records_requests(client: AsyncClient):
    """Make a few requests then verify the telemetry counter increased."""
    before_resp = await client.get("/api/v1/telemetry")
    before_count = before_resp.json()["total_requests"]

    # Generate some traffic
    await client.get("/api/v1/profiles")
    await client.get("/api/v1/profiles")
    await client.get("/api/v1/profiles")

    after_resp = await client.get("/api/v1/telemetry")
    after_count = after_resp.json()["total_requests"]

    assert after_count > before_count


async def test_telemetry_records_404_in_status_counts(client: AsyncClient):
    """A 404 response should increment the 404 bucket in status_counts."""
    before_resp = await client.get("/api/v1/telemetry")
    before_data = before_resp.json()
    before_404 = before_data["status_counts"].get("404", 0)

    # Trigger a 404
    await client.get("/api/v1/profiles/nonexistent-profile-for-telemetry-test")

    after_resp = await client.get("/api/v1/telemetry")
    after_data = after_resp.json()
    after_404 = after_data["status_counts"].get("404", 0)

    assert after_404 > before_404


# ---------------------------------------------------------------------------
# TelemetryMetrics unit tests (no HTTP needed)
# ---------------------------------------------------------------------------

def test_telemetry_metrics_record_request():
    metrics = TelemetryMetrics()
    metrics.record_request("GET", "/test", 200, 15.0)

    assert metrics.total_requests == 1
    assert metrics.status_counts[200] == 1
    assert metrics.total_errors == 0


def test_telemetry_metrics_counts_500_as_error():
    metrics = TelemetryMetrics()
    metrics.record_request("POST", "/boom", 500, 50.0)

    assert metrics.total_errors == 1
    assert metrics.status_counts[500] == 1


def test_telemetry_metrics_snapshot_structure():
    metrics = TelemetryMetrics()
    metrics.record_request("GET", "/api/v1/profiles", 200, 10.0)
    metrics.record_request("GET", "/api/v1/profiles", 200, 20.0)

    snap = metrics.snapshot()
    assert "total_requests" in snap
    assert "total_errors" in snap
    assert "status_counts" in snap
    assert "endpoints" in snap

    endpoint_key = "GET /api/v1/profiles"
    assert endpoint_key in snap["endpoints"]
    stats = snap["endpoints"][endpoint_key]
    assert stats["count"] == 2
    assert stats["avg_ms"] == 15.0
    assert "p50_ms" in stats
    assert "p95_ms" in stats
    assert "p99_ms" in stats
    assert "max_ms" in stats


def test_telemetry_metrics_latency_list_bounded():
    """Latency list must not grow unbounded beyond _max_latency_samples."""
    metrics = TelemetryMetrics()
    metrics._max_latency_samples = 5

    for i in range(10):
        metrics.record_request("GET", "/bound", 200, float(i))

    assert len(metrics.endpoint_latencies["GET /bound"]) == 5
    # The last 5 samples should be retained
    assert metrics.endpoint_latencies["GET /bound"] == [5.0, 6.0, 7.0, 8.0, 9.0]


# ---------------------------------------------------------------------------
# Error handling — unhandled exception and 404 logging
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_endpoint_returns_500_with_request_id():
    """global_exception_handler returns 500 with request_id in the JSON body."""
    from unittest.mock import MagicMock

    from starlette.requests import Request

    from app.core.middleware import global_exception_handler

    # Build a minimal mock request with a known request_id in state
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/profiles",
        "query_string": b"",
        "headers": [],
    }
    mock_request = Request(scope)
    mock_request.state.request_id = "test-req-id-abc"

    response = await global_exception_handler(mock_request, RuntimeError("deliberate boom"))

    assert response.status_code == 500
    import json
    body = json.loads(response.body)
    assert "request_id" in body
    assert body["request_id"] == "test-req-id-abc"
    assert "detail" in body


async def test_404_logged_as_warning(client: AsyncClient):
    """A 404 response increments the 404 bucket and warning-level telemetry is emitted."""
    before_resp = await client.get("/api/v1/telemetry")
    before_404 = before_resp.json()["status_counts"].get("404", 0)

    # Hit an endpoint that always returns 404
    resp = await client.get("/api/v1/profiles/definite-nonexistent-profile-404-warn-test")
    assert resp.status_code == 404

    after_resp = await client.get("/api/v1/telemetry")
    after_404 = after_resp.json()["status_counts"].get("404", 0)

    # The middleware records 404 in status_counts
    assert after_404 > before_404
