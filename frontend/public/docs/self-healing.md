# Self-Healing System

## Self-Healing Architecture

Atlas Vox includes a self-healing system that automatically detects and remediates common infrastructure issues. It monitors provider health, Redis connectivity, error rates, and resource usage, taking corrective action without manual intervention.

```
  +------------------+     +-------------------+     +------------------+
  |   Health Monitor |---->| Detection Engine  |---->| Remediation      |
  |                  |     |                   |     | Engine           |
  |  - Provider pings|     | - Rule matching   |     |                  |
  |  - Redis check   |     | - Threshold eval  |     | - Restart svc    |
  |  - Error rates   |     | - Severity assign |     | - Fallback mode  |
  |  - Resource usage|     |                   |     | - Purge cache    |
  +------------------+     +-------------------+     | - Alert user     |
                                    |                +--------+---------+
                                    v                         |
                           +-------------------+              v
                           | Incident Log      |     +------------------+
                           | (healing_incidents)|     | MCP Bridge       |
                           | - Severity         |     | (AI-assisted     |
                           | - Action taken     |     |  remediation)    |
                           | - Outcome          |     +------------------+
                           +-------------------+
```

---

## Detection Rules

| Rule | Threshold | Severity | Action |
|------|-----------|----------|--------|
| Redis connection failure | 3 consecutive failures | Critical | Restart Redis, switch to in-memory fallback |
| Provider health check failure | 5 consecutive failures | Warning | Mark provider unhealthy, remove from rotation |
| High error rate | >10% error rate over 5 min | Warning | Log alert, throttle requests |
| Celery worker unresponsive | 30 second heartbeat miss | Critical | Restart worker process |
| Disk space low | <500 MB free in storage/ | Warning | Purge old audio files, alert user |
| Database connection pool exhausted | 0 available connections | Critical | Close idle connections, increase pool size |
| Memory usage high | >90% system memory | Warning | Trigger garbage collection, unload idle models |
| GPU VRAM exhausted | CUDA OOM error | Critical | Unload least-used model, retry operation |

---

## Remediation Action Hierarchy

### Level 1: Automatic Recovery

Restart services, reconnect, retry operations. No human intervention needed.

### Level 2: Graceful Degradation

Switch to fallback mode (in-memory cache, alternative provider, reduced features).

### Level 3: Resource Cleanup

Purge old files, close idle connections, trigger garbage collection, unload unused models.

### Level 4: Alert & Escalate

Log incident, send webhook notification, mark as requiring human attention.

### Level 5: MCP-Assisted Fix

If MCP bridge is enabled, allow AI assistant to analyze the incident and suggest or apply a fix.

---

## MCP Bridge

The MCP bridge allows an AI assistant (e.g., Claude) to participate in incident remediation. When enabled, the self-healing system can expose incident details to the MCP server, allowing the AI to analyze root causes and suggest or apply fixes.

| Setting | Default | Description |
|---------|---------|-------------|
| MCP bridge enabled | true | Allow AI-assisted remediation |
| Max fixes per hour | 10 | Rate limit on automated fixes |
| Auto-apply fixes | false | Apply fixes without confirmation (dangerous) |

---

## How to Test Self-Healing

### 1. Simulate Redis failure

```bash
# Stop Redis
docker compose -f docker/docker-compose.yml stop redis

# Watch the Healing page for a critical incident
# The system should detect the failure within 30 seconds
# and switch to in-memory fallback mode

# Restart Redis
docker compose -f docker/docker-compose.yml start redis

# The system should auto-reconnect and log a "resolved" incident
```

### 2. Check incident log

```bash
# Via API
curl http://localhost:8100/api/v1/healing/incidents

# Via Web UI
# Navigate to the Self-Healing page and expand "Incident History"

# Each incident shows:
# - Severity (critical, warning, info)
# - Category (redis, provider, resource, etc.)
# - Action taken and outcome (resolved, failed, escalated)
```

### 3. Trigger provider failure

```bash
# Set an invalid API key for ElevenLabs
# The provider health check should fail
# After 5 consecutive failures, the system will:
# 1. Mark the provider as unhealthy
# 2. Remove it from the synthesis rotation
# 3. Log a warning-level incident
```

---

## Incident Log Format

```json
{
  "id": "inc_a1b2c3d4",
  "severity": "critical",
  "category": "redis",
  "title": "Redis connection failure",
  "description": "Connection refused after 3 consecutive attempts",
  "action_taken": "restart_service",
  "action_detail": "Attempted Redis reconnection with exponential backoff",
  "outcome": "resolved",
  "created_at": "2025-03-29T14:32:00Z",
  "resolved_at": "2025-03-29T14:32:45Z",
  "duration_seconds": 45
}
```
