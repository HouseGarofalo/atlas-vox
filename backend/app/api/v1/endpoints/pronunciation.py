"""Pronunciation dictionary endpoints — CRUD + import/export."""

import csv
import io
import uuid

import structlog
from fastapi import APIRouter, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession
from app.models.pronunciation_entry import PronunciationEntry
from app.services.synthesis_service import _pronunciation_cache

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/pronunciation", tags=["pronunciation"])


class PronunciationCreate(BaseModel):
    word: str = Field(..., min_length=1, max_length=255)
    ipa: str = Field(..., min_length=1, max_length=500)
    language: str = Field(default="en", max_length=10)
    profile_id: str | None = None


class PronunciationUpdate(BaseModel):
    word: str | None = None
    ipa: str | None = None
    language: str | None = None


class PronunciationResponse(BaseModel):
    id: str
    word: str
    ipa: str
    language: str
    profile_id: str | None
    created_at: str
    updated_at: str


@router.get("")
async def list_entries(
    db: DbSession,
    user: CurrentUser,
    language: str | None = Query(None),
    profile_id: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """List pronunciation dictionary entries with optional filters."""
    query = select(PronunciationEntry)
    if language:
        query = query.where(PronunciationEntry.language == language)
    if profile_id:
        query = query.where(PronunciationEntry.profile_id == profile_id)
    elif profile_id is None:
        # Global entries (no profile) by default
        query = query.where(PronunciationEntry.profile_id.is_(None))
    if search:
        query = query.where(PronunciationEntry.word.ilike(f"%{search}%"))
    query = query.order_by(PronunciationEntry.word).offset(offset).limit(limit)

    result = await db.execute(query)
    entries = result.scalars().all()
    return {
        "entries": [
            {
                "id": e.id,
                "word": e.word,
                "ipa": e.ipa,
                "language": e.language,
                "profile_id": e.profile_id,
                "created_at": e.created_at.isoformat(),
                "updated_at": e.updated_at.isoformat(),
            }
            for e in entries
        ],
        "count": len(entries),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_entry(data: PronunciationCreate, db: DbSession, user: CurrentUser) -> dict:
    """Create a pronunciation dictionary entry."""
    entry = PronunciationEntry(
        id=str(uuid.uuid4()),
        word=data.word,
        ipa=data.ipa,
        language=data.language,
        profile_id=data.profile_id,
    )
    db.add(entry)
    await db.flush()
    # Invalidate pronunciation cache for affected profile
    _pronunciation_cache.pop(data.profile_id or "__global__", None)
    logger.info("pronunciation_created", word=data.word, ipa=data.ipa)
    return {
        "id": entry.id,
        "word": entry.word,
        "ipa": entry.ipa,
        "language": entry.language,
        "profile_id": entry.profile_id,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
    }


@router.put("/{entry_id}")
async def update_entry(entry_id: str, data: PronunciationUpdate, db: DbSession, user: CurrentUser) -> dict:
    """Update a pronunciation dictionary entry."""
    result = await db.execute(select(PronunciationEntry).where(PronunciationEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    if data.word is not None:
        entry.word = data.word
    if data.ipa is not None:
        entry.ipa = data.ipa
    if data.language is not None:
        entry.language = data.language
    await db.flush()
    # Invalidate pronunciation cache for the affected profile
    _pronunciation_cache.pop(entry.profile_id or "__global__", None)
    logger.info("pronunciation_updated", entry_id=entry_id)
    return {
        "id": entry.id,
        "word": entry.word,
        "ipa": entry.ipa,
        "language": entry.language,
        "profile_id": entry.profile_id,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
    }


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(entry_id: str, db: DbSession, user: CurrentUser) -> None:
    """Delete a pronunciation dictionary entry."""
    result = await db.execute(select(PronunciationEntry).where(PronunciationEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    await db.delete(entry)
    # Invalidate pronunciation cache for the affected profile
    _pronunciation_cache.pop(entry.profile_id or "__global__", None)
    logger.info("pronunciation_deleted", entry_id=entry_id)


@router.post("/import")
async def import_csv(file: UploadFile, db: DbSession, user: CurrentUser) -> dict:
    """Import pronunciation entries from a CSV file (columns: word, ipa, language)."""
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    created = 0
    for row in reader:
        word = row.get("word", "").strip()
        ipa = row.get("ipa", "").strip()
        if not word or not ipa:
            continue
        entry = PronunciationEntry(
            id=str(uuid.uuid4()),
            word=word,
            ipa=ipa,
            language=row.get("language", "en").strip(),
        )
        db.add(entry)
        created += 1
    await db.flush()
    # Invalidate entire pronunciation cache after bulk import
    _pronunciation_cache.clear()
    logger.info("pronunciation_imported", count=created)
    return {"imported": created}


@router.get("/export")
async def export_csv(db: DbSession, user: CurrentUser) -> StreamingResponse:
    """Export all pronunciation entries as CSV."""
    result = await db.execute(select(PronunciationEntry).order_by(PronunciationEntry.word))
    entries = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["word", "ipa", "language"])
    for e in entries:
        writer.writerow([e.word, e.ipa, e.language])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pronunciation_dictionary.csv"},
    )
