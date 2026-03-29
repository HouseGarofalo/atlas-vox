"""Tests for the profile service layer."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio_sample import AudioSample
from app.models.model_version import ModelVersion
from app.models.voice_profile import VoiceProfile
from app.schemas.profile import ProfileCreate, ProfileResponse, ProfileUpdate
from app.services.profile_service import (
    create_profile,
    delete_profile,
    get_profile,
    list_profiles,
    profile_to_response,
    update_profile,
)


# ---------------------------------------------------------------------------
# create_profile
# ---------------------------------------------------------------------------

async def test_create_profile(db_session: AsyncSession):
    data = ProfileCreate(name="My Voice", provider_name="kokoro", language="en")
    profile = await create_profile(db_session, data)

    assert profile.id is not None
    assert profile.name == "My Voice"
    assert profile.provider_name == "kokoro"
    assert profile.language == "en"
    assert profile.status == "pending"
    assert profile.voice_id is None


async def test_create_profile_with_voice_id(db_session: AsyncSession):
    """A profile created with voice_id must have status 'ready' immediately."""
    data = ProfileCreate(
        name="Library Voice",
        provider_name="kokoro",
        voice_id="af_heart",
    )
    profile = await create_profile(db_session, data)

    assert profile.status == "ready"
    assert profile.voice_id == "af_heart"


async def test_create_profile_default_language(db_session: AsyncSession):
    data = ProfileCreate(name="Default Lang", provider_name="piper")
    profile = await create_profile(db_session, data)
    assert profile.language == "en"


async def test_create_profile_with_tags(db_session: AsyncSession):
    import json
    data = ProfileCreate(name="Tagged", provider_name="kokoro", tags=["deep", "narrator"])
    profile = await create_profile(db_session, data)
    assert json.loads(profile.tags) == ["deep", "narrator"]


# ---------------------------------------------------------------------------
# get_profile
# ---------------------------------------------------------------------------

async def test_get_profile(db_session: AsyncSession):
    data = ProfileCreate(name="Fetch Me", provider_name="kokoro")
    created = await create_profile(db_session, data)

    fetched = await get_profile(db_session, created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "Fetch Me"


async def test_get_profile_not_found(db_session: AsyncSession):
    result = await get_profile(db_session, "totally-nonexistent-id")
    assert result is None


# ---------------------------------------------------------------------------
# list_profiles
# ---------------------------------------------------------------------------

async def test_list_profiles(db_session: AsyncSession):
    before = await list_profiles(db_session, limit=1000)
    initial_count = len(before)

    await create_profile(db_session, ProfileCreate(name="List1", provider_name="kokoro"))
    await create_profile(db_session, ProfileCreate(name="List2", provider_name="piper"))

    after = await list_profiles(db_session, limit=1000)
    assert len(after) == initial_count + 2
    names = [p.name for p in after]
    assert "List1" in names
    assert "List2" in names


async def test_list_profiles_ordered_by_created_desc(db_session: AsyncSession):
    await create_profile(db_session, ProfileCreate(name="Old", provider_name="kokoro"))
    await create_profile(db_session, ProfileCreate(name="New", provider_name="kokoro"))

    profiles = await list_profiles(db_session)
    names = [p.name for p in profiles]
    assert names.index("New") < names.index("Old")


# ---------------------------------------------------------------------------
# update_profile
# ---------------------------------------------------------------------------

async def test_update_profile(db_session: AsyncSession):
    profile = await create_profile(db_session, ProfileCreate(name="Update Me", provider_name="kokoro"))

    updated = await update_profile(
        db_session, profile.id, ProfileUpdate(name="Updated Name", description="new desc")
    )
    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.description == "new desc"


async def test_update_profile_partial(db_session: AsyncSession):
    profile = await create_profile(
        db_session, ProfileCreate(name="Partial", provider_name="kokoro", language="fr")
    )
    updated = await update_profile(db_session, profile.id, ProfileUpdate(name="Partial Updated"))
    assert updated is not None
    assert updated.name == "Partial Updated"
    assert updated.language == "fr"


async def test_update_profile_not_found(db_session: AsyncSession):
    result = await update_profile(
        db_session, "no-such-profile", ProfileUpdate(name="Ghost")
    )
    assert result is None


# ---------------------------------------------------------------------------
# delete_profile
# ---------------------------------------------------------------------------

async def test_delete_profile(db_session: AsyncSession):
    profile = await create_profile(db_session, ProfileCreate(name="Delete Me", provider_name="kokoro"))
    pid = profile.id

    success = await delete_profile(db_session, pid)
    assert success is True

    gone = await get_profile(db_session, pid)
    assert gone is None


async def test_delete_profile_not_found(db_session: AsyncSession):
    result = await delete_profile(db_session, "does-not-exist")
    assert result is False


async def test_delete_profile_idempotency(db_session: AsyncSession):
    """Deleting an already-deleted profile returns False, not an exception."""
    profile = await create_profile(db_session, ProfileCreate(name="Delete Twice", provider_name="kokoro"))
    pid = profile.id

    first = await delete_profile(db_session, pid)
    second = await delete_profile(db_session, pid)

    assert first is True
    assert second is False


# ---------------------------------------------------------------------------
# profile_to_response
# ---------------------------------------------------------------------------

async def test_profile_to_response(db_session: AsyncSession):
    """profile_to_response returns ProfileResponse with correct aggregate counts."""
    import json as _json

    profile = await create_profile(
        db_session,
        ProfileCreate(name="Full Profile", provider_name="kokoro", tags=["calm", "deep"]),
    )

    # Add one AudioSample
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.mktemp(suffix=".wav"))
    db_session.add(AudioSample(
        profile_id=profile.id,
        filename=tmp.name,
        original_filename=tmp.name,
        file_path=str(tmp),
        format="wav",
        file_size_bytes=1024,
    ))

    # Add one ModelVersion
    db_session.add(ModelVersion(
        profile_id=profile.id,
        version_number=1,
        provider_model_id="voice-abc",
    ))
    await db_session.flush()

    response = await profile_to_response(db_session, profile)

    assert isinstance(response, ProfileResponse)
    assert response.id == profile.id
    assert response.name == "Full Profile"
    assert response.sample_count == 1
    assert response.version_count == 1
    assert response.tags == ["calm", "deep"]


async def test_profile_to_response_no_tags(db_session: AsyncSession):
    """Profile without tags must return tags=None in the response."""
    profile = await create_profile(
        db_session,
        ProfileCreate(name="No Tags Profile", provider_name="piper"),
    )

    response = await profile_to_response(db_session, profile)

    assert response.tags is None


async def test_profile_to_response_invalid_tags_json(db_session: AsyncSession):
    """Profile with malformed JSON in the tags column must return tags=None."""
    profile = await create_profile(
        db_session,
        ProfileCreate(name="Bad Tags Profile", provider_name="piper"),
    )
    # Manually corrupt the tags field after creation
    profile.tags = "not-valid-json-{"
    await db_session.flush()

    response = await profile_to_response(db_session, profile)

    assert response.tags is None
