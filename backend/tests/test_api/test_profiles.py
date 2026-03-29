"""Tests for profile CRUD endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_profile(client: AsyncClient):
    response = await client.post("/api/v1/profiles", json={
        "name": "Test Voice",
        "provider_name": "kokoro",
        "language": "en",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Voice"
    assert data["provider_name"] == "kokoro"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_list_profiles(client: AsyncClient):
    # Create a profile first
    await client.post("/api/v1/profiles", json={"name": "P1", "provider_name": "kokoro"})

    response = await client.get("/api/v1/profiles")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert len(data["profiles"]) >= 1


@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient):
    create = await client.post("/api/v1/profiles", json={"name": "P2", "provider_name": "kokoro"})
    pid = create.json()["id"]

    response = await client.get(f"/api/v1/profiles/{pid}")
    assert response.status_code == 200
    assert response.json()["name"] == "P2"


@pytest.mark.asyncio
async def test_get_nonexistent_profile(client: AsyncClient):
    response = await client.get("/api/v1/profiles/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient):
    create = await client.post("/api/v1/profiles", json={"name": "P3", "provider_name": "kokoro"})
    pid = create.json()["id"]

    response = await client.put(f"/api/v1/profiles/{pid}", json={"name": "Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_profile(client: AsyncClient):
    create = await client.post("/api/v1/profiles", json={"name": "P4", "provider_name": "kokoro"})
    pid = create.json()["id"]

    response = await client.delete(f"/api/v1/profiles/{pid}")
    assert response.status_code == 204

    get_response = await client.get(f"/api/v1/profiles/{pid}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_create_profile_with_voice_id(client: AsyncClient):
    """Creating a profile with voice_id sets status to ready."""
    resp = await client.post("/api/v1/profiles", json={
        "name": "Test Library Voice",
        "provider_name": "kokoro",
        "voice_id": "af_heart",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "ready"
    assert data["voice_id"] == "af_heart"


@pytest.mark.asyncio
async def test_create_profile_without_voice_id_is_pending(client: AsyncClient):
    """Creating a profile without voice_id sets status to pending."""
    resp = await client.post("/api/v1/profiles", json={
        "name": "Custom Voice",
        "provider_name": "kokoro",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["voice_id"] is None


# ---------------------------------------------------------------------------
# Model versioning
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_versions_empty(client: AsyncClient):
    """GET /api/v1/profiles/{id}/versions returns empty list for a new profile."""
    create = await client.post("/api/v1/profiles", json={"name": "VersionsEmpty", "provider_name": "kokoro"})
    assert create.status_code == 201
    pid = create.json()["id"]

    resp = await client.get(f"/api/v1/profiles/{pid}/versions")
    assert resp.status_code == 200
    data = resp.json()
    assert "versions" in data
    assert "count" in data
    assert data["count"] == 0
    assert data["versions"] == []


@pytest.mark.asyncio
async def test_list_versions_with_versions(client: AsyncClient, db_session):
    """GET /api/v1/profiles/{id}/versions returns versions after inserting some."""
    from app.models.model_version import ModelVersion

    create = await client.post("/api/v1/profiles", json={"name": "WithVersions", "provider_name": "kokoro"})
    assert create.status_code == 201
    pid = create.json()["id"]

    # Insert a ModelVersion and commit so the HTTP handler's SELECT sees the row.
    # The `client` fixture overrides get_db with the same db_session, so we must
    # commit rather than just flush to make the data visible within the same
    # SQLite connection that the ASGI handler will query.
    version = ModelVersion(profile_id=pid, version_number=1)
    db_session.add(version)
    await db_session.commit()

    resp = await client.get(f"/api/v1/profiles/{pid}/versions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    ids = [v["id"] for v in data["versions"]]
    assert version.id in ids


@pytest.mark.asyncio
async def test_activate_version_success(client: AsyncClient, db_session):
    """POST /api/v1/profiles/{id}/activate-version/{ver_id} activates the version."""
    from app.models.model_version import ModelVersion

    create = await client.post("/api/v1/profiles", json={"name": "ActivateOK", "provider_name": "kokoro"})
    assert create.status_code == 201
    pid = create.json()["id"]

    version = ModelVersion(profile_id=pid, version_number=1)
    db_session.add(version)
    await db_session.commit()
    ver_id = version.id

    resp = await client.post(f"/api/v1/profiles/{pid}/activate-version/{ver_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == pid
    # Profile should now be ready after activation
    assert data["status"] == "ready"


@pytest.mark.asyncio
async def test_activate_version_not_found(client: AsyncClient):
    """POST /api/v1/profiles/{id}/activate-version/{ver_id} returns 400 when version doesn't exist."""
    create = await client.post("/api/v1/profiles", json={"name": "ActivateFail", "provider_name": "kokoro"})
    assert create.status_code == 201
    pid = create.json()["id"]

    resp = await client.post(f"/api/v1/profiles/{pid}/activate-version/nonexistent-version-id")
    assert resp.status_code == 400
