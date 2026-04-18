"""Voice clone consent ledger endpoints (SC-44).

All three endpoints require admin scope.  The ledger is append-only —
there are deliberately no PUT / PATCH / DELETE routes.
"""

from __future__ import annotations

import base64

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.dependencies import CurrentUser, DbSession, require_scope
from app.core.exceptions import NotFoundError, ValidationError
from app.models.clone_consent import CloneConsent
from app.services.consent_service import (
    PrehashedSample,
    get_consent,
    list_consent,
    record_consent,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/consent", tags=["consent"])


class ConsentCreate(BaseModel):
    profile_id: str = Field(..., description="Target voice profile id")
    # Exactly one of source_audio_hash / source_audio_bytes_b64 must be set.
    source_audio_hash: str | None = Field(
        None,
        min_length=64,
        max_length=64,
        description="Pre-computed sha256 hex digest of the first sample",
    )
    source_audio_bytes_b64: str | None = Field(
        None,
        description="Base64-encoded first-sample bytes (alternative to source_audio_hash)",
    )
    target_provider: str | None = Field(
        None,
        description="Provider the clone is being created with; defaults to the profile's provider",
    )
    consent_text: str = Field(..., min_length=1)
    operator_user_id: str | None = Field(
        None,
        description="Operator identifier; defaults to the authenticated user's sub",
    )
    consent_proof_blob: str | None = None


class ConsentResponse(BaseModel):
    id: str
    source_audio_hash: str
    target_profile_id: str
    target_provider: str
    consent_text: str
    consent_granted_at: str
    operator_user_id: str
    consent_proof_blob: str | None

    @classmethod
    def from_model(cls, row: CloneConsent) -> "ConsentResponse":
        return cls(
            id=row.id,
            source_audio_hash=row.source_audio_hash,
            target_profile_id=row.target_profile_id,
            target_provider=row.target_provider,
            consent_text=row.consent_text,
            consent_granted_at=row.consent_granted_at.isoformat(),
            operator_user_id=row.operator_user_id,
            consent_proof_blob=row.consent_proof_blob,
        )


class ConsentListResponse(BaseModel):
    entries: list[ConsentResponse]
    count: int


@router.post(
    "",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_consent(
    data: ConsentCreate,
    db: DbSession,
    user: CurrentUser,
    _admin=require_scope("admin"),
) -> ConsentResponse:
    """Record a new consent entry. Requires admin scope."""
    if not data.source_audio_hash and not data.source_audio_bytes_b64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either source_audio_hash or source_audio_bytes_b64 is required",
        )

    if data.source_audio_hash:
        sample_for_hash = PrehashedSample(data.source_audio_hash)
    else:
        try:
            sample_for_hash = base64.b64decode(
                data.source_audio_bytes_b64 or "", validate=True
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source_audio_bytes_b64 must be valid base64",
            )

    operator = data.operator_user_id or (user or {}).get("sub", "unknown")
    try:
        record = await record_consent(
            db,
            profile_id=data.profile_id,
            samples=[sample_for_hash],
            operator_user_id=operator,
            consent_text=data.consent_text,
            target_provider=data.target_provider,
            consent_proof_blob=data.consent_proof_blob,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail)

    await db.flush()
    logger.info(
        "consent_endpoint_created",
        consent_id=record.id,
        profile_id=data.profile_id,
    )
    return ConsentResponse.from_model(record)


@router.get("", response_model=ConsentListResponse)
async def list_consent_entries(
    db: DbSession,
    user: CurrentUser,
    _admin=require_scope("admin"),
    profile_id: str | None = Query(None),
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
) -> ConsentListResponse:
    """List consent entries, most recent first."""
    rows = await list_consent(db, profile_id=profile_id, limit=limit, offset=offset)
    return ConsentListResponse(
        entries=[ConsentResponse.from_model(r) for r in rows],
        count=len(rows),
    )


@router.get("/{consent_id}", response_model=ConsentResponse)
async def get_consent_entry(
    consent_id: str,
    db: DbSession,
    user: CurrentUser,
    _admin=require_scope("admin"),
) -> ConsentResponse:
    """Return a single consent entry by id."""
    try:
        row = await get_consent(db, consent_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail)
    return ConsentResponse.from_model(row)
