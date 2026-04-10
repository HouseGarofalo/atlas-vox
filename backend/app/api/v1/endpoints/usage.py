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

    # Base aggregation query by provider
    provider_query = select(
        UsageEvent.provider_name,
        func.sum(UsageEvent.characters).label("total_characters"),
        func.count().label("total_requests"),
        func.avg(UsageEvent.duration_ms).label("avg_duration_ms"),
    ).where(UsageEvent.created_at >= since)

    if provider:
        provider_query = provider_query.where(UsageEvent.provider_name == provider)

    provider_query = provider_query.group_by(UsageEvent.provider_name)
    provider_result = await db.execute(provider_query)
    provider_rows = provider_result.fetchall()

    # Build provider breakdown
    by_provider: dict[str, dict] = {}
    total_chars = 0
    total_cost = 0.0
    total_requests = 0

    for row in provider_rows:
        p = row.provider_name
        chars = row.total_characters or 0
        requests = row.total_requests or 0
        avg_latency = int(row.avg_duration_ms or 0)
        cost = (chars / 1000) * DEFAULT_COST_PER_1K.get(p, 0.0)

        by_provider[p] = {
            "characters": chars,
            "requests": requests,
            "cost_usd": round(cost, 6),
            "avg_latency_ms": avg_latency,
        }

        total_chars += chars
        total_cost += cost
        total_requests += requests

    # Daily breakdown aggregation
    daily_query = select(
        func.strftime('%Y-%m-%d', UsageEvent.created_at).label("day"),
        func.sum(UsageEvent.characters).label("total_characters"),
        func.count().label("total_requests"),
    ).where(UsageEvent.created_at >= since)

    if provider:
        daily_query = daily_query.where(UsageEvent.provider_name == provider)

    daily_query = daily_query.group_by(func.strftime('%Y-%m-%d', UsageEvent.created_at))
    daily_result = await db.execute(daily_query)
    daily_rows = daily_result.fetchall()

    daily: dict[str, dict] = {}
    for row in daily_rows:
        day = row.day
        chars = row.total_characters or 0
        requests = row.total_requests or 0

        # Calculate cost for the day - need provider breakdown for accurate cost
        day_cost_query = select(
            UsageEvent.provider_name,
            func.sum(UsageEvent.characters).label("chars"),
        ).where(
            UsageEvent.created_at >= since,
            func.strftime('%Y-%m-%d', UsageEvent.created_at) == day,
        )
        if provider:
            day_cost_query = day_cost_query.where(UsageEvent.provider_name == provider)
        day_cost_query = day_cost_query.group_by(UsageEvent.provider_name)

        day_cost_result = await db.execute(day_cost_query)
        day_cost_rows = day_cost_result.fetchall()

        day_cost = sum((r.chars / 1000) * DEFAULT_COST_PER_1K.get(r.provider_name, 0.0) for r in day_cost_rows)

        daily[day] = {
            "characters": chars,
            "requests": requests,
            "cost_usd": round(day_cost, 6),
        }

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
