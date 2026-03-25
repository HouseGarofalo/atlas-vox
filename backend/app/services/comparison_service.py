"""Comparison service — side-by-side synthesis across multiple voices."""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voice_profile import VoiceProfile
from app.services.synthesis_service import synthesize

logger = structlog.get_logger(__name__)


async def compare_voices(
    db: AsyncSession,
    text: str,
    profile_ids: list[str],
    speed: float = 1.0,
    pitch: float = 0.0,
) -> list[dict]:
    """Synthesize the same text with multiple profiles sequentially.

    Sequential due to shared DB session; each synthesis is internally async.
    """
    if len(profile_ids) < 2:
        raise ValueError("At least 2 profiles required for comparison")

    # Validate all profiles exist
    for pid in profile_ids:
        result = await db.execute(
            select(VoiceProfile).where(VoiceProfile.id == pid)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            raise ValueError(f"Profile '{pid}' not found")

    # Synthesize in parallel using asyncio.gather
    # We need separate DB sessions for parallel work, so we serialize here
    # but each individual synthesis is still async internally
    results = []
    for pid in profile_ids:
        try:
            synth_result = await synthesize(
                db, text=text, profile_id=pid, speed=speed, pitch=pitch,
            )

            # Enrich with profile info
            prof_result = await db.execute(
                select(VoiceProfile).where(VoiceProfile.id == pid)
            )
            profile = prof_result.scalar_one_or_none()

            results.append({
                "profile_id": pid,
                "profile_name": profile.name if profile else pid,
                "provider_name": synth_result["provider_name"],
                "audio_url": synth_result["audio_url"],
                "duration_seconds": synth_result.get("duration_seconds"),
                "latency_ms": synth_result["latency_ms"],
            })
        except Exception as e:
            logger.error("comparison_failed", profile_id=pid, error=str(e))
            results.append({
                "profile_id": pid,
                "profile_name": pid,
                "provider_name": "error",
                "audio_url": "",
                "duration_seconds": None,
                "latency_ms": 0,
                "error": str(e),
            })

    return results
