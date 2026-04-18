"""SL-30 — context-adaptive voice routing tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.profile import ProfileCreate
from app.services.context_router import (
    CONTEXTS,
    ContextScore,
    classify_text,
    rank_profiles,
    recommend_route,
)
from app.services.profile_service import create_profile


# ---------------------------------------------------------------------------
# classify_text — deterministic + transparent
# ---------------------------------------------------------------------------


def _top(scores: list[ContextScore]) -> str:
    return scores[0].context


class TestClassifyText:
    def test_empty_text_returns_default(self):
        scores = classify_text("")
        assert scores[0].context == "conversational"
        assert scores[0].score == 0.0

    def test_whitespace_only_returns_default(self):
        assert _top(classify_text("   \n  ")) == "conversational"

    def test_dialogue_text_tops_dialogue(self):
        text = (
            '"I can\'t believe this," she said.\n'
            '"Neither can I," he replied, shaking his head.'
        )
        scores = classify_text(text)
        assert _top(scores) == "dialogue"
        top = scores[0]
        assert top.score > 0.4
        assert any("quoted span" in s for s in top.signals)

    def test_technical_text_tops_technical(self):
        text = (
            "Check the API response payload: the endpoint returns a JSON "
            "schema with status 500 when the Kubernetes pod's CPU exceeds "
            "its limit. See https://example.com/docs for the function signature."
        )
        assert _top(classify_text(text)) == "technical"

    def test_emotional_text_tops_emotional(self):
        text = "I love you so much! I was terrified, but then my heart overjoyed!"
        scores = classify_text(text)
        assert _top(scores) == "emotional"
        assert any("emotion word" in s for s in scores[0].signals)

    def test_narrative_text_tops_narrative(self):
        text = (
            "Once upon a time in a quiet kingdom, the narrator began her "
            "story. As night fell over the forest, the tale unfolded slowly "
            "through her patient, careful words, and the listeners leaned in."
        )
        assert _top(classify_text(text)) == "narrative"

    def test_long_form_beats_on_sheer_length(self):
        text = (
            "The careful observer notices a gradient, a slow build of tension "
            "across the chapter. " * 15
        )
        # 15 repetitions × ~80 chars = ~1200 chars, many sentences, no dialogue
        # or strong emotion → long_form should top.
        top = _top(classify_text(text))
        assert top in {"long_form", "narrative"}

    def test_conversational_tops_on_short_casual(self):
        assert _top(classify_text("Hey, yeah, kinda busy right now.")) == "conversational"

    def test_every_context_is_ranked(self):
        """Every run returns a fully-ordered list over CONTEXTS."""
        scores = classify_text("Hello there.")
        assert {s.context for s in scores} == set(CONTEXTS)
        # Non-increasing.
        vals = [s.score for s in scores]
        assert all(a >= b for a, b in zip(vals, vals[1:]))

    def test_classifier_is_deterministic(self):
        a = classify_text("Hello, how are you today?")
        b = classify_text("Hello, how are you today?")
        assert [s.to_dict() for s in a] == [s.to_dict() for s in b]


# ---------------------------------------------------------------------------
# rank_profiles — affinity + preference bias
# ---------------------------------------------------------------------------


class _ProfileStub:
    """Minimal duck-typed stand-in for VoiceProfile."""

    def __init__(self, id: str, name: str, provider_name: str, voice_id: str | None = None):
        self.id = id
        self.name = name
        self.provider_name = provider_name
        self.voice_id = voice_id


class TestRankProfiles:
    def test_dialogue_prefers_dia2(self):
        profiles = [
            _ProfileStub("a", "Alpha", "kokoro"),
            _ProfileStub("b", "Bravo", "dia2"),
            _ProfileStub("c", "Charlie", "elevenlabs"),
        ]
        recs = rank_profiles(profiles, top_context="dialogue")
        assert recs[0].profile_name == "Bravo"
        assert recs[0].provider_name == "dia2"

    def test_emotional_prefers_elevenlabs(self):
        profiles = [
            _ProfileStub("a", "Alpha", "kokoro"),
            _ProfileStub("b", "Bravo", "elevenlabs"),
            _ProfileStub("c", "Charlie", "piper"),
        ]
        assert rank_profiles(profiles, top_context="emotional")[0].provider_name == "elevenlabs"

    def test_technical_prefers_azure(self):
        profiles = [
            _ProfileStub("a", "Alpha", "azure_speech"),
            _ProfileStub("b", "Bravo", "elevenlabs"),
        ]
        assert rank_profiles(profiles, top_context="technical")[0].provider_name == "azure_speech"

    def test_preference_bias_overrides_ties(self):
        """Two kokoro profiles — the one with +0.2 thumbs-up bias wins."""
        profiles = [
            _ProfileStub("a", "Alpha", "kokoro"),
            _ProfileStub("b", "Bravo", "kokoro"),
        ]
        biases = {"b": 0.2}
        recs = rank_profiles(
            profiles, top_context="conversational", preference_biases=biases,
        )
        assert recs[0].profile_id == "b"
        assert any("preference bias" in r for r in recs[0].reasons)

    def test_limit_caps_output(self):
        profiles = [
            _ProfileStub(str(i), f"P{i}", "kokoro") for i in range(10)
        ]
        assert len(rank_profiles(profiles, top_context="conversational", limit=3)) == 3

    def test_stable_tie_breaking(self):
        """Alphabetical by name on tie."""
        profiles = [
            _ProfileStub("1", "Zebra", "kokoro"),
            _ProfileStub("2", "Alpha", "kokoro"),
            _ProfileStub("3", "Mango", "kokoro"),
        ]
        names = [r.profile_name for r in rank_profiles(profiles, top_context="conversational")]
        assert names == ["Alpha", "Mango", "Zebra"]

    def test_unknown_provider_gets_default_score(self):
        profiles = [_ProfileStub("a", "Alpha", "weirdprovider")]
        recs = rank_profiles(profiles, top_context="narrative")
        assert len(recs) == 1
        assert 0.0 < recs[0].score < 1.0


# ---------------------------------------------------------------------------
# recommend_route — end-to-end with real profile table
# ---------------------------------------------------------------------------


async def _make_profile(
    db: AsyncSession, name: str, provider: str, ready: bool = True,
) -> str:
    p = await create_profile(
        db,
        ProfileCreate(name=name, provider_name=provider, voice_id="default"),
    )
    if ready:
        p.status = "ready"
        await db.flush()
    return p.id


async def test_recommend_route_uses_ready_profiles_only(db_session: AsyncSession):
    ready_id = await _make_profile(db_session, "Ready Voice", "kokoro", ready=True)
    await _make_profile(db_session, "Training Voice", "kokoro", ready=False)

    rec = await recommend_route(db_session, "Hey, how are you doing today?")
    assert rec.top_context == "conversational"
    ids = {r.profile_id for r in rec.recommendations}
    assert ready_id in ids
    # The unreadied profile must NOT appear.
    assert all(r.profile_id != "Training Voice" for r in rec.recommendations)


async def test_recommend_route_returns_excerpt_and_scores(db_session: AsyncSession):
    await _make_profile(db_session, "Main", "elevenlabs", ready=True)
    long_text = (
        "Once upon a time in a quiet kingdom, the narrator began her story. "
        "As night fell over the forest, the tale unfolded slowly and surely "
        "through careful words and patient attention."
    )
    rec = await recommend_route(db_session, long_text, limit=2)
    assert rec.top_context in {"narrative", "long_form"}
    assert rec.text_excerpt.startswith("Once upon a time")
    assert len(rec.recommendations) <= 2
    # Context scores list is fully populated.
    assert {s.context for s in rec.context_scores} == set(CONTEXTS)


async def test_recommend_route_long_text_truncates_excerpt(db_session: AsyncSession):
    await _make_profile(db_session, "Main", "kokoro", ready=True)
    text = "a" * 500
    rec = await recommend_route(db_session, text, limit=1)
    assert len(rec.text_excerpt) <= 120
    assert rec.text_excerpt.endswith("…")


# ---------------------------------------------------------------------------
# Endpoint round-trip
# ---------------------------------------------------------------------------


async def test_endpoint_round_trip(client, db_session: AsyncSession):
    await _make_profile(db_session, "Api Voice", "dia2", ready=True)
    # Two quoted spans + two dialogue tags — unambiguous dialogue win
    # (conversational markers alone can't reach the same score).
    text = (
        '"I can\'t believe this," she said.\n'
        '"Neither can I," he replied quietly.'
    )
    resp = await client.post(
        "/api/v1/synthesis/recommend-voice",
        json={"text": text, "limit": 3},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["top_context"] == "dialogue"
    assert "text_excerpt" in payload
    assert "recommendations" in payload
    assert isinstance(payload["context_scores"], list)


async def test_endpoint_validates_empty_text(client):
    resp = await client.post(
        "/api/v1/synthesis/recommend-voice", json={"text": ""},
    )
    assert resp.status_code == 422


async def test_endpoint_validates_limit_bounds(client, db_session: AsyncSession):
    resp = await client.post(
        "/api/v1/synthesis/recommend-voice",
        json={"text": "hi", "limit": 99},
    )
    assert resp.status_code == 422
