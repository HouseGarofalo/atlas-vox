"""Comparison service — side-by-side synthesis across multiple voices."""

from __future__ import annotations

import asyncio

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
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
    """Synthesize the same text with multiple profiles concurrently.

    Each profile gets its own DB session to avoid async session conflicts
    when running in parallel via asyncio.gather.
    """
    if len(profile_ids) < 2:
        from app.core.exceptions import ValidationError
        raise ValidationError("At least 2 profiles required for comparison")

    logger.info(
        "comparison_started",
        profile_count=len(profile_ids),
        text_length=len(text),
        profile_ids=profile_ids,
    )

    async def _synth_one(pid: str) -> dict:
        """Synthesize for a single profile using its own session."""
        try:
            async with async_session_factory() as session:
                synth_result = await synthesize(
                    session, text=text, profile_id=pid, speed=speed, pitch=pitch,
                )

                # Fetch profile name for the response
                prof_result = await session.execute(
                    select(VoiceProfile).where(VoiceProfile.id == pid)
                )
                profile = prof_result.scalar_one_or_none()
                await session.commit()

            logger.debug(
                "comparison_profile_synthesized",
                profile_id=pid,
                provider=synth_result["provider_name"],
                latency_ms=synth_result["latency_ms"],
            )
            return {
                "profile_id": pid,
                "profile_name": profile.name if profile else pid,
                "provider_name": synth_result["provider_name"],
                "audio_url": synth_result["audio_url"],
                "duration_seconds": synth_result.get("duration_seconds"),
                "latency_ms": synth_result["latency_ms"],
            }
        except Exception as e:
            logger.error("comparison_failed", profile_id=pid, error=str(e))
            return {
                "profile_id": pid,
                "profile_name": pid,
                "provider_name": "error",
                "audio_url": "",
                "duration_seconds": None,
                "latency_ms": 0,
                "error": str(e),
            }

    results = await asyncio.gather(*[_synth_one(pid) for pid in profile_ids])

    logger.info(
        "comparison_completed",
        result_count=len(results),
        error_count=sum(1 for r in results if "error" in r),
    )
    return list(results)
