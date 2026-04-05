"""Usage analytics endpoints — character counts, cost tracking, provider breakdown."""

import csv
import io
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.core.dependencies import CurrentUser, DbSession
from app.models.usage_event import UsageEvent

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/usage", tags=["usage"])

# Estimated cost per 1000 characters by provider (USD)
DEFAULT_COST_PER_1K: dict[str, float] = {
    "elevenlabs": 0.30,
    "azure_speech": 0.016,
    "kokoro": 0.0,
    "piper": 0.0,
    "coqui_xtts": 0.0,
    "styletts2": 0.0,
    "cosyvoice": 0.0,
    "dia": 0.0,
    "dia2": 0.0,
}


@router.get("")
async def get_usage(
    db: DbSession,
    user: CurrentUser,
    days: int = Query(default=30, ge=1, le=365),
    provider: str | None = Query(None),
) -> dict:
    """Get usage analytics for the specified time period."""
    since = datetime.now(UTC) - timedelta(days=days)

    # Base query
    query = select(UsageEvent).where(UsageEvent.created_at >= since)
    if provider:
        query = query.where(UsageEvent.provider_name == provider)

    result = await db.execute(query)
    events = result.scalars().all()

    # Aggregate by provider
    by_provider: dict[str, dict] = {}
    total_chars = 0
    total_cost = 0.0
    total_requests = 0

    for e in events:
        p = e.provider_name
        if p not in by_provider:
            by_provider[p] = {"characters": 0, "requests": 0, "cost_usd": 0.0, "avg_latency_ms": 0, "latencies": []}
        by_provider[p]["characters"] += e.characters
        by_provider[p]["requests"] += 1
        cost = (e.characters / 1000) * DEFAULT_COST_PER_1K.get(p, 0.0)
        by_provider[p]["cost_usd"] += cost
        if e.duration_ms:
            by_provider[p]["latencies"].append(e.duration_ms)
        total_chars += e.characters
        total_cost += cost
        total_requests += 1

    # Calculate average latencies
    for p_data in by_provider.values():
        lats = p_data.pop("latencies")
        p_data["avg_latency_ms"] = int(sum(lats) / len(lats)) if lats else 0

    # Daily breakdown
    daily: dict[str, dict] = {}
    for e in events:
        day = e.created_at.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"characters": 0, "requests": 0, "cost_usd": 0.0}
        daily[day]["characters"] += e.characters
        daily[day]["requests"] += 1
        daily[day]["cost_usd"] += (e.characters / 1000) * DEFAULT_COST_PER_1K.get(e.provider_name, 0.0)

    return {
        "period_days": days,
        "total_characters": total_chars,
        "total_requests": total_requests,
        "total_estimated_cost_usd": round(total_cost, 4),
        "by_provider": by_provider,
        "daily": dict(sorted(daily.items())),
    }


@router.get("/export")
async def export_usage(
    db: DbSession,
    user: CurrentUser,
    days: int = Query(default=30, ge=1, le=365),
) -> StreamingResponse:
    """Export usage events as CSV."""
    since = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        select(UsageEvent)
        .where(UsageEvent.created_at >= since)
        .order_by(UsageEvent.created_at.desc())
    )
    events = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "provider", "profile_id", "voice_id", "characters", "duration_ms", "cost_usd", "event_type"])
    for e in events:
        cost = (e.characters / 1000) * DEFAULT_COST_PER_1K.get(e.provider_name, 0.0)
        writer.writerow([
            e.created_at.isoformat(),
            e.provider_name,
            e.profile_id or "",
            e.voice_id or "",
            e.characters,
            e.duration_ms or "",
            round(cost, 6),
            e.event_type,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=usage_export.csv"},
    )
