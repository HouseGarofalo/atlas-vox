"""Training job endpoints — start, list, status, cancel, WebSocket progress."""

import asyncio

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status

from app.core.dependencies import CurrentUser, DbSession
from app.core.exceptions import NotFoundError, ValidationError
from app.core.rate_limit import limiter
from app.schemas.training import TrainingJobListResponse, TrainingJobResponse, TrainingStart
from app.services.training_service import (
    cancel_job,
    get_job_status,
    list_jobs,
    start_training,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["training"])


@router.post(
    "/profiles/{profile_id}/train",
    response_model=TrainingJobResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def start_training_job(
    request: Request,
    profile_id: str,
    data: TrainingStart,
    db: DbSession,
    user: CurrentUser,
) -> TrainingJobResponse:
    """Start a training job for a voice profile."""
    logger.info("start_training_job_called", profile_id=profile_id, provider_name=data.provider_name)
    try:
        job = await start_training(
            db,
            profile_id=profile_id,
            provider_name=data.provider_name,
            config=data.config,
        )
        logger.info("training_job_started", profile_id=profile_id, job_id=job.id, provider_name=data.provider_name)
        return TrainingJobResponse.model_validate(job)
    except (NotFoundError, ValidationError) as e:
        logger.error("start_training_job_failed", profile_id=profile_id, provider_name=data.provider_name, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/training/jobs", response_model=TrainingJobListResponse)
async def list_training_jobs(
    db: DbSession,
    user: CurrentUser,
    profile_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
) -> TrainingJobListResponse:
    """List all training jobs with optional filtering."""
    logger.info(
        "list_training_jobs_called",
        profile_id=profile_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    jobs = await list_jobs(db, profile_id=profile_id, status_filter=status_filter, limit=limit, offset=offset)
    logger.info("list_training_jobs_returned", count=len(jobs), profile_id=profile_id)
    return TrainingJobListResponse(
        jobs=[TrainingJobResponse.model_validate(j) for j in jobs],
        count=len(jobs),
    )


@router.get("/training/jobs/{job_id}")
async def get_training_job(
    job_id: str, db: DbSession, user: CurrentUser
) -> dict:
    """Get detailed training job status including Celery progress."""
    logger.info("get_training_job_called", job_id=job_id)
    try:
        return await get_job_status(db, job_id)
    except (NotFoundError, ValidationError) as e:
        logger.info("get_training_job_not_found", job_id=job_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/training/jobs/{job_id}/cancel", response_model=TrainingJobResponse)
async def cancel_training_job(
    job_id: str, db: DbSession, user: CurrentUser
) -> TrainingJobResponse:
    """Cancel a running or queued training job."""
    logger.info("cancel_training_job_called", job_id=job_id)
    try:
        job = await cancel_job(db, job_id)
        logger.info("training_job_cancelled", job_id=job_id)
        return TrainingJobResponse.model_validate(job)
    except (NotFoundError, ValidationError) as e:
        logger.error("cancel_training_job_failed", job_id=job_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.websocket("/training/jobs/{job_id}/progress")
async def training_progress_ws(websocket: WebSocket, job_id: str, token: str | None = None) -> None:
    """WebSocket endpoint streaming training progress for a specific job.

    Authentication via ?token= query parameter (skipped if AUTH_DISABLED).
    Polls Celery task state and pushes JSON frames to the client.
    """
    # Authenticate before accepting the connection
    from app.core.config import settings as app_settings
    if not app_settings.auth_disabled:
        if not token:
            await websocket.close(code=4001, reason="Authentication required: pass ?token=<api_key>")
            return
        # Validate token against stored API keys
        from sqlalchemy import select as _sel

        from app.core.database import async_session_factory as _sf
        from app.core.security import verify_api_key
        from app.models.api_key import ApiKey
        async with _sf() as _db:
            key_prefix = token[:12] if len(token) >= 12 else token
            result = await _db.execute(
                _sel(ApiKey).where(ApiKey.active == True, ApiKey.key_prefix == key_prefix)  # noqa: E712
            )
            keys = result.scalars().all()
            valid = any(verify_api_key(token, k.key_hash) for k in keys)
        if not valid:
            await websocket.close(code=4003, reason="Invalid API key")
            return

    await websocket.accept()

    try:
        from sqlalchemy import select

        from app.core.database import async_session_factory
        from app.models.training_job import TrainingJob
        from app.tasks.celery_app import celery_app

        # Look up the Celery task ID from the job
        async with async_session_factory() as db:
            result = await db.execute(select(TrainingJob).where(TrainingJob.id == job_id))
            job = result.scalar_one_or_none()

        if job is None:
            await websocket.send_json({"error": "Job not found"})
            await websocket.close()
            return

        celery_task_id = job.celery_task_id
        last_state = None

        while True:
            # Poll Celery state
            if celery_task_id:
                async_result = celery_app.AsyncResult(celery_task_id)
                state = async_result.state
                info = async_result.info if isinstance(async_result.info, dict) else {}
            else:
                state = job.status.upper()
                info = {}

            frame = {
                "job_id": job_id,
                "state": state,
                "percent": info.get("percent", 0),
                "status": info.get("status", state),
            }

            # Only send if changed
            if frame != last_state:
                await websocket.send_json(frame)
                last_state = frame

            # Terminal states — send final frame and close
            if state in ("SUCCESS", "FAILURE", "REVOKED"):
                # Refresh job from DB for final status
                async with async_session_factory() as db:
                    result = await db.execute(select(TrainingJob).where(TrainingJob.id == job_id))
                    job = result.scalar_one_or_none()
                if job:
                    await websocket.send_json({
                        "job_id": job_id,
                        "state": "DONE" if job.status == "completed" else job.status.upper(),
                        "percent": 100 if job.status == "completed" else frame["percent"],
                        "status": job.status,
                        "version_id": job.result_version_id,
                        "error": job.error_message,
                    })
                break

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        logger.debug("ws_disconnected", job_id=job_id)
    except Exception as e:
        logger.error("ws_error", job_id=job_id, error=str(e))
        try:
            await websocket.send_json({"error": "Internal error. Check server logs for details."})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
