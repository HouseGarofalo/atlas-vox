"""Usage analytics endpoints — character counts, cost tracking, provider breakdown."""

import csv
import io
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.core.dependencies import CurrentUser, DbSession
from app.models.synthesis_history import SynthesisHistory
from app.models.usage_event import UsageEvent
from app.services.cost_estimator import PROVIDER_COST_PER_1K_CHARS

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/usage", tags=["usage"])

# Estimated cost per 1000 characters by provider (USD).
# Single source of truth lives in ``cost_estimator``; this alias preserves the
# legacy name other code may rely on.
DEFAULT_COST_PER_1K: dict[str, float] = PROVIDER_COST_PER_1K_CHARS


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
        cost = (chars / 1000) * PROVIDER_COST_PER_1K_CHARS.get(p, 0.0)

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

    # VQ-39 — dashboard widget convenience: {provider: cost_usd} flat map.
    cost_by_provider: dict[str, float] = {
        p: stats["cost_usd"] for p, stats in by_provider.items()
    }

    return {
        "period_days": days,
        "total_characters": total_chars,
        "total_requests": total_requests,
        "total_estimated_cost_usd": round(total_cost, 4),
        "by_provider": by_provider,
        "cost_by_provider": cost_by_provider,
        "daily": dict(sorted(daily.items())),
    }


# ---------------------------------------------------------------------------
# VQ-39 — dedicated cost aggregation using ``synthesis_history`` stamps.
# ---------------------------------------------------------------------------


@router.get("/cost")
async def get_cost(
    db: DbSession,
    user: CurrentUser,
    provider: str | None = Query(None),
    profile_id: str | None = Query(None),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
) -> dict:
    """Aggregate synthesis cost using the per-row ``estimated_cost_usd`` stamp.

    Pulls from :class:`SynthesisHistory` rather than :class:`UsageEvent` so
    the numbers match what individual rows show on the history view. Rows
    missing a cost stamp (written before the migration) are treated as 0.0.
    """
    query = select(
        SynthesisHistory.provider_name,
        SynthesisHistory.profile_id,
        func.coalesce(func.sum(SynthesisHistory.estimated_cost_usd), 0.0).label("cost"),
        func.count().label("requests"),
        func.avg(SynthesisHistory.latency_ms).label("avg_latency_ms"),
    ).group_by(SynthesisHistory.provider_name, SynthesisHistory.profile_id)

    if provider:
        query = query.where(SynthesisHistory.provider_name == provider)
    if profile_id:
        query = query.where(SynthesisHistory.profile_id == profile_id)
    if since is not None:
        query = query.where(SynthesisHistory.created_at >= since)
    if until is not None:
        query = query.where(SynthesisHistory.created_at <= until)

    result = await db.execute(query)
    rows = result.fetchall()

    by_provider: dict[str, float] = {}
    by_profile: dict[str, float] = {}
    latency_accum: dict[str, list[tuple[int, float]]] = {}
    total_cost = 0.0
    total_requests = 0

    for row in rows:
        p = row.provider_name
        prof = row.profile_id
        cost = float(row.cost or 0.0)
        reqs = int(row.requests or 0)
        by_provider[p] = round(by_provider.get(p, 0.0) + cost, 6)
        by_profile[prof] = round(by_profile.get(prof, 0.0) + cost, 6)
        if row.avg_latency_ms is not None:
            latency_accum.setdefault(p, []).append((reqs, float(row.avg_latency_ms)))
        total_cost += cost
        total_requests += reqs

    # Reduce per-provider latency to a request-weighted average.
    avg_latency_by_provider: dict[str, int] = {}
    for p, pairs in latency_accum.items():
        total_reqs = sum(r for r, _ in pairs) or 1
        weighted = sum(r * lat for r, lat in pairs) / total_reqs
        avg_latency_by_provider[p] = int(weighted)

    return {
        "total_cost_usd": round(total_cost, 4),
        "total_requests": total_requests,
        "by_provider": by_provider,
        "by_profile": by_profile,
        "avg_latency_ms_by_provider": avg_latency_by_provider,
        "filters": {
            "provider": provider,
            "profile_id": profile_id,
            "since": since.isoformat() if since else None,
            "until": until.isoformat() if until else None,
        },
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
