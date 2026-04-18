"""Pronunciation dictionary endpoints — CRUD + import/export + synthesize preview.

Feature surface for VQ-38 (lexicon editor). Mirrors the ``/pronunciation``
(singular) prefix for backwards compatibility AND also exposes the
``/pronunciations`` (plural) prefix that newer clients target.
"""

from __future__ import annotations

import csv
import io
import re
import uuid
import xml.etree.ElementTree as ET

import structlog
from fastapi import APIRouter, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_, select

from app.core.dependencies import CurrentUser, DbSession
from app.models.pronunciation_entry import PronunciationEntry
from app.services.pronunciation_service import clear_cache, invalidate_cache

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PronunciationCreate(BaseModel):
    word: str = Field(..., min_length=1, max_length=255)
    ipa: str = Field(..., min_length=1, max_length=500)
    language: str = Field(default="en", max_length=10)
    stress: str | None = Field(default=None, max_length=20)
    profile_id: str | None = None


class PronunciationUpdate(BaseModel):
    word: str | None = None
    ipa: str | None = None
    language: str | None = None
    stress: str | None = None


class PronunciationResponse(BaseModel):
    id: str
    word: str
    ipa: str
    language: str
    stress: str | None = None
    profile_id: str | None
    created_at: str
    updated_at: str


class PronunciationListResponse(BaseModel):
    entries: list[PronunciationResponse]
    count: int


class PronunciationImportResponse(BaseModel):
    imported: int
    format: str


class PronunciationPreviewResponse(BaseModel):
    audio_url: str
    word: str
    ipa: str


def _to_response(e: PronunciationEntry) -> PronunciationResponse:
    """Serialise a DB row — ``stress`` is encoded in the IPA string when present."""
    stress = _extract_stress(e.ipa)
    return PronunciationResponse(
        id=e.id,
        word=e.word,
        ipa=e.ipa,
        language=e.language,
        stress=stress,
        profile_id=e.profile_id,
        created_at=e.created_at.isoformat(),
        updated_at=e.updated_at.isoformat(),
    )


def _extract_stress(ipa: str) -> str | None:
    """IPA primary stress marker is ``ˈ`` (U+02C8), secondary is ``ˌ`` (U+02CC).

    We return ``"primary"``, ``"secondary"``, or ``None`` so clients that
    can't render IPA still get something useful.
    """
    if not ipa:
        return None
    if "\u02c8" in ipa:
        return "primary"
    if "\u02cc" in ipa:
        return "secondary"
    return None


# ---------------------------------------------------------------------------
# Routers — expose both /pronunciation (legacy) and /pronunciations (VQ-38)
# ---------------------------------------------------------------------------

router = APIRouter(tags=["pronunciation"])


async def _list_entries(
    db,
    language: str | None,
    profile_id: str | None,
    search: str | None,
    limit: int,
    offset: int,
) -> PronunciationListResponse:
    query = select(PronunciationEntry)
    if language:
        query = query.where(PronunciationEntry.language == language)
    if profile_id == "__global__":
        query = query.where(PronunciationEntry.profile_id.is_(None))
    elif profile_id:
        query = query.where(
            or_(
                PronunciationEntry.profile_id == profile_id,
                PronunciationEntry.profile_id.is_(None),
            )
        )
    if search:
        escaped = search.replace("%", "\\%").replace("_", "\\_")
        query = query.where(PronunciationEntry.word.ilike(f"%{escaped}%", escape="\\"))
    query = query.order_by(PronunciationEntry.word).offset(offset).limit(limit)

    result = await db.execute(query)
    entries = result.scalars().all()
    return PronunciationListResponse(
        entries=[_to_response(e) for e in entries],
        count=len(entries),
    )


# ---------- LIST ----------


@router.get("/pronunciation", response_model=PronunciationListResponse)
async def list_entries_legacy(
    db: DbSession,
    user: CurrentUser,
    language: str | None = Query(None),
    profile_id: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
) -> PronunciationListResponse:
    """List pronunciation dictionary entries (legacy singular path)."""
    # Preserve the legacy default: no profile_id => global-only.
    effective_profile = profile_id if profile_id else "__global__"
    return await _list_entries(db, language, effective_profile, search, limit, offset)


@router.get("/pronunciations", response_model=PronunciationListResponse)
async def list_entries(
    db: DbSession,
    user: CurrentUser,
    profile_id: str | None = Query(None),
    q: str | None = Query(None, description="Word substring search"),
    language: str | None = Query(None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
) -> PronunciationListResponse:
    """Search pronunciation entries — VQ-38 primary surface.

    When ``profile_id`` is supplied, the response includes global entries
    too (so the UI can show them as inherited); leave it blank to browse
    only global entries.
    """
    return await _list_entries(db, language, profile_id, q, limit, offset)


# ---------- CREATE ----------


async def _create_entry(db, data: PronunciationCreate) -> PronunciationEntry:
    entry = PronunciationEntry(
        id=str(uuid.uuid4()),
        word=data.word,
        ipa=data.ipa,
        language=data.language,
        profile_id=data.profile_id,
    )
    db.add(entry)
    await db.flush()
    invalidate_cache(data.profile_id)
    logger.info("pronunciation_created", word=data.word, ipa=data.ipa)
    return entry


@router.post("/pronunciation", response_model=PronunciationResponse, status_code=status.HTTP_201_CREATED)
async def create_entry_legacy(data: PronunciationCreate, db: DbSession, user: CurrentUser) -> PronunciationResponse:
    """Create a pronunciation entry (legacy singular path)."""
    entry = await _create_entry(db, data)
    return _to_response(entry)


@router.post("/pronunciations", response_model=PronunciationResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(data: PronunciationCreate, db: DbSession, user: CurrentUser) -> PronunciationResponse:
    """Create a pronunciation entry — VQ-38 primary surface."""
    entry = await _create_entry(db, data)
    return _to_response(entry)


# ---------- UPDATE ----------


async def _update_entry(db, entry_id: str, data: PronunciationUpdate) -> PronunciationEntry:
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
    invalidate_cache(entry.profile_id)
    logger.info("pronunciation_updated", entry_id=entry_id)
    return entry


@router.put("/pronunciation/{entry_id}", response_model=PronunciationResponse)
async def update_entry_legacy(entry_id: str, data: PronunciationUpdate, db: DbSession, user: CurrentUser) -> PronunciationResponse:
    entry = await _update_entry(db, entry_id, data)
    return _to_response(entry)


@router.put("/pronunciations/{entry_id}", response_model=PronunciationResponse)
async def update_entry(entry_id: str, data: PronunciationUpdate, db: DbSession, user: CurrentUser) -> PronunciationResponse:
    entry = await _update_entry(db, entry_id, data)
    return _to_response(entry)


# ---------- DELETE ----------


async def _delete_entry(db, entry_id: str) -> None:
    result = await db.execute(select(PronunciationEntry).where(PronunciationEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    profile_id = entry.profile_id
    await db.delete(entry)
    invalidate_cache(profile_id)
    logger.info("pronunciation_deleted", entry_id=entry_id)


@router.delete("/pronunciation/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry_legacy(entry_id: str, db: DbSession, user: CurrentUser):
    await _delete_entry(db, entry_id)


@router.delete("/pronunciations/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(entry_id: str, db: DbSession, user: CurrentUser):
    await _delete_entry(db, entry_id)


# ---------- IMPORT (CSV + PLS) ----------


# W3C PLS namespace — every <lexeme> must live here per the spec.
_PLS_NS = "http://www.w3.org/2005/01/pronunciation-lexicon"
_PLS_LANG_ATTR = "{http://www.w3.org/XML/1998/namespace}lang"


def _parse_pls(body: bytes) -> list[tuple[str, str, str]]:
    """Parse a W3C Pronunciation Lexicon (PLS) document.

    Returns ``(word, ipa, language)`` tuples. Both namespaced and
    non-namespaced ``<lexeme>`` / ``<grapheme>`` / ``<phoneme>`` elements are
    accepted since in the wild authors sometimes skip the namespace.
    """
    root = ET.fromstring(body)
    lang_default = root.attrib.get(_PLS_LANG_ATTR, "en")

    out: list[tuple[str, str, str]] = []
    for lex in root.iter():
        tag = lex.tag.split("}")[-1]
        if tag != "lexeme":
            continue
        grapheme = ipa = None
        for child in lex:
            ctag = child.tag.split("}")[-1]
            if ctag == "grapheme" and child.text:
                grapheme = child.text.strip()
            elif ctag == "phoneme" and child.text:
                ipa = child.text.strip()
        if grapheme and ipa:
            out.append((grapheme, ipa, lang_default))
    return out


async def _import_entries(
    db, file: UploadFile, profile_id: str | None,
) -> PronunciationImportResponse:
    content = await file.read()
    filename = (file.filename or "").lower()
    is_pls = filename.endswith((".pls", ".xml")) or content.lstrip().startswith(b"<")

    created = 0
    fmt: str
    if is_pls:
        fmt = "pls"
        try:
            rows = _parse_pls(content)
        except ET.ParseError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid PLS XML: {exc}",
            ) from exc
        for word, ipa, language in rows:
            db.add(PronunciationEntry(
                id=str(uuid.uuid4()), word=word, ipa=ipa,
                language=language, profile_id=profile_id,
            ))
            created += 1
    else:
        fmt = "csv"
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV must be UTF-8",
            ) from exc
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            word = (row.get("word") or "").strip()
            ipa = (row.get("ipa") or "").strip()
            if not word or not ipa:
                continue
            db.add(PronunciationEntry(
                id=str(uuid.uuid4()), word=word, ipa=ipa,
                language=(row.get("language") or "en").strip(),
                profile_id=profile_id,
            ))
            created += 1

    await db.flush()
    clear_cache()  # large bulk change — cheapest to nuke everything.
    logger.info("pronunciation_imported", count=created, format=fmt)
    return PronunciationImportResponse(imported=created, format=fmt)


@router.post("/pronunciation/import", response_model=PronunciationImportResponse)
async def import_entries_legacy(
    file: UploadFile, db: DbSession, user: CurrentUser,
    profile_id: str | None = Query(None),
) -> PronunciationImportResponse:
    return await _import_entries(db, file, profile_id)


@router.post("/pronunciations/import", response_model=PronunciationImportResponse)
async def import_entries(
    file: UploadFile, db: DbSession, user: CurrentUser,
    profile_id: str | None = Query(None),
) -> PronunciationImportResponse:
    """Bulk import pronunciation entries from CSV or PLS."""
    return await _import_entries(db, file, profile_id)


# ---------- EXPORT (CSV + PLS) ----------


def _build_csv(entries: list[PronunciationEntry]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["word", "ipa", "language"])
    for e in entries:
        writer.writerow([e.word, e.ipa, e.language])
    return buf.getvalue()


def _build_pls(entries: list[PronunciationEntry]) -> str:
    # Build a minimal but spec-compliant lexicon. Assumes a single-language
    # export — we group by language to keep it well-formed.
    languages = sorted({e.language or "en" for e in entries})
    primary = languages[0] if languages else "en"
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<lexicon version="1.0" xmlns="{_PLS_NS}" '
            f'xml:lang="{primary}" alphabet="ipa">'
        ),
    ]
    for e in entries:
        # Escape angle brackets / ampersands defensively.
        word = (e.word or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ipa = (e.ipa or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        out.append(
            f"  <lexeme><grapheme>{word}</grapheme><phoneme>{ipa}</phoneme></lexeme>"
        )
    out.append("</lexicon>")
    return "\n".join(out)


async def _export_entries(
    db, fmt: str, profile_id: str | None,
) -> StreamingResponse:
    query = select(PronunciationEntry).order_by(PronunciationEntry.word)
    if profile_id == "__global__":
        query = query.where(PronunciationEntry.profile_id.is_(None))
    elif profile_id:
        query = query.where(PronunciationEntry.profile_id == profile_id)
    result = await db.execute(query)
    entries = list(result.scalars().all())

    if fmt == "pls":
        body = _build_pls(entries)
        return StreamingResponse(
            iter([body]),
            media_type="application/pls+xml",
            headers={"Content-Disposition": "attachment; filename=pronunciation_dictionary.pls"},
        )
    body = _build_csv(entries)
    return StreamingResponse(
        iter([body]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pronunciation_dictionary.csv"},
    )


@router.get("/pronunciation/export")
async def export_entries_legacy(db: DbSession, user: CurrentUser) -> StreamingResponse:
    """Export all entries as CSV (legacy surface — no format parameter)."""
    return await _export_entries(db, "csv", None)


@router.get("/pronunciations/export")
async def export_entries(
    db: DbSession, user: CurrentUser,
    format: str = Query("csv", pattern="^(csv|pls)$"),
    profile_id: str | None = Query(None),
) -> StreamingResponse:
    """Export pronunciation entries as CSV or PLS (VQ-38)."""
    return await _export_entries(db, format, profile_id)


# ---------- PREVIEW ----------


_IPA_ALLOWED = re.compile(r"[^A-Za-z\u00C0-\u024F\u0250-\u02AF\u0300-\u036F\u0370-\u03FF .ˈˌː'_-]")


class PronunciationPreviewRequest(BaseModel):
    profile_id: str | None = None


@router.post("/pronunciations/{entry_id}/preview", response_model=PronunciationPreviewResponse)
async def preview_entry(
    entry_id: str,
    db: DbSession,
    user: CurrentUser,
    payload: PronunciationPreviewRequest | None = None,
) -> PronunciationPreviewResponse:
    """Synthesize a preview of the entry's word using the current lexicon.

    The preview uses a small SSML fragment with a ``<phoneme>`` tag so the
    user hears exactly how their IPA renders. If no ``profile_id`` is
    supplied we pick the first available profile — keeps the UX simple for
    single-user installs.
    """
    from app.models.voice_profile import VoiceProfile
    from app.services import synthesis_service

    result = await db.execute(
        select(PronunciationEntry).where(PronunciationEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    # Pick a profile: explicit > entry's profile > any profile.
    profile_id: str | None = None
    if payload is not None and payload.profile_id:
        profile_id = payload.profile_id
    if profile_id is None:
        profile_id = entry.profile_id
    if profile_id is None:
        default_row = (
            await db.execute(select(VoiceProfile).limit(1))
        ).scalar_one_or_none()
        if default_row is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No voice profile available for preview",
            )
        profile_id = default_row.id

    # Defensive escape — deny anything outside a whitelisted IPA / letter set.
    safe_ipa = _IPA_ALLOWED.sub("", entry.ipa)
    ssml = (
        '<speak version="1.0" xml:lang="en-US">'
        f'<phoneme alphabet="ipa" ph="{safe_ipa}">{entry.word}</phoneme>'
        "</speak>"
    )

    synth = await synthesis_service.synthesize(
        db, text=ssml, profile_id=profile_id, ssml=True,
    )
    return PronunciationPreviewResponse(
        audio_url=synth["audio_url"], word=entry.word, ipa=entry.ipa,
    )
