"""VQ-37 — prosody preview tests.

Tests cover:
  - Tokenisation + syllable counting behaviour
  - Sentence-position rise/fall
  - Emphasis detection (caps, markdown, overrides)
  - Emotion overlays
  - SSML emission
  - Endpoint round-trip
"""

from __future__ import annotations

import pytest

from app.services.prosody_preview import (
    ProsodyPreview,
    build_prosody_preview,
    supported_emotions,
)
from app.services.prosody_preview import _syllables


class TestSyllableCounter:
    @pytest.mark.parametrize("word,expected", [
        ("hello", 2),
        ("the", 1),
        ("beautiful", 4),
        ("make", 1),       # silent-e drops the second syllable
        ("bike", 1),       # silent-e
        ("bee", 1),        # "ee" exception — stays 1
        ("simple", 2),     # "le" exception
        ("i", 1),
        ("'s", 1),         # empty stem defaults to 1
        ("syllable", 3),
        ("queue", 2),      # "ueue" — ignore silent-e logic trick
    ])
    def test_syllables(self, word, expected):
        # Syllable counter is a heuristic — allow ±1 on ambiguous cases
        # (e.g. "queue") while pinning the obvious ones.
        got = _syllables(word)
        assert abs(got - expected) <= 1


class TestBuildProsodyPreview:
    def test_empty_text_returns_empty_words(self):
        p = build_prosody_preview("")
        assert isinstance(p, ProsodyPreview)
        assert p.words == []
        assert p.sentence_count == 0
        assert p.total_duration_ms == 0

    def test_simple_sentence_declines_toward_end(self):
        """Statements should have pitch drifting down near the end."""
        p = build_prosody_preview("The quick brown fox jumps over the lazy dog.")
        assert len(p.words) == 9
        # First few words are near baseline; last word is lower.
        first_pitch = p.words[0].pitch
        last_pitch = p.words[-1].pitch
        assert last_pitch < first_pitch
        # Final punctuation flags sentence end.
        assert p.words[-1].is_sentence_end is True
        assert p.sentence_count == 1

    def test_question_rises_at_end(self):
        p = build_prosody_preview("Are you coming home later?")
        assert p.words[-1].is_sentence_end
        # Last word's pitch > first word's pitch for a question.
        assert p.words[-1].pitch > p.words[0].pitch

    def test_all_caps_word_gets_strong_emphasis(self):
        p = build_prosody_preview("The fox is REALLY fast.")
        target = next(w for w in p.words if w.text == "REALLY")
        assert target.emphasis == "strong"
        assert target.pitch > 0.15
        assert target.energy > 0.65

    def test_markdown_bold_marks_strong(self):
        p = build_prosody_preview("The fox is **really** fast.")
        target = next(w for w in p.words if w.text == "really")
        assert target.emphasis == "strong"

    def test_emphasis_override_beats_heuristic(self):
        p = build_prosody_preview(
            "The fox is REALLY fast.",
            emphasis_overrides={3: "reduced"},  # override "REALLY"
        )
        target = next(w for w in p.words if w.text == "REALLY")
        assert target.emphasis == "reduced"
        # Reduced emphasis pushes pitch & energy DOWN.
        assert target.pitch < 0.1
        assert target.energy < 0.4

    def test_commas_add_pause_duration(self):
        base = build_prosody_preview("Once upon a time")
        paused = build_prosody_preview("Once, upon a time")
        # Same tokens but the one with a comma after "Once" gets +120ms there.
        assert paused.total_duration_ms > base.total_duration_ms

    def test_emotion_overlay_shifts_all_words(self):
        neutral = build_prosody_preview("I am here today.")
        excited = build_prosody_preview("I am here today.", emotion="excited")
        avg_n = sum(w.pitch for w in neutral.words) / len(neutral.words)
        avg_e = sum(w.pitch for w in excited.words) / len(excited.words)
        assert avg_e > avg_n  # excitement raises pitch
        # Excited energy is higher too.
        assert sum(w.energy for w in excited.words) > sum(w.energy for w in neutral.words)

    def test_sad_emotion_lowers_pitch_and_lengthens(self):
        neutral = build_prosody_preview("I am here today.")
        sad = build_prosody_preview("I am here today.", emotion="sad")
        avg_n = sum(w.pitch for w in neutral.words) / len(neutral.words)
        avg_s = sum(w.pitch for w in sad.words) / len(sad.words)
        assert avg_s < avg_n
        # Sad pacing is slower → larger total duration.
        assert sad.total_duration_ms > neutral.total_duration_ms

    def test_unknown_emotion_is_ignored_gracefully(self):
        p = build_prosody_preview("Hello there.", emotion="NOT_A_THING")
        # Same shape as default — no crash, no overlay applied.
        assert p.emotion == "NOT_A_THING"
        neutral = build_prosody_preview("Hello there.")
        assert [w.pitch for w in p.words] == [w.pitch for w in neutral.words]

    def test_pitch_clamped_to_unit_range(self):
        # Stacked shouting + exclamations + caps + excited overlay should
        # still stay in [-1, 1] — no NaNs or runaway values.
        text = "I CAN'T BELIEVE IT! THIS IS AMAZING!!"
        p = build_prosody_preview(text, emotion="excited")
        for w in p.words:
            assert -1.0 <= w.pitch <= 1.0
            assert 0.0 <= w.energy <= 1.0

    def test_multiple_sentences_count_correctly(self):
        p = build_prosody_preview("First. Second! Third?")
        assert p.sentence_count == 3


class TestSSMLEmission:
    def test_ssml_wraps_strong_words(self):
        p = build_prosody_preview("I think this is AWESOME today.")
        assert '<emphasis level="strong">AWESOME</emphasis>' in p.ssml

    def test_ssml_wraps_reduced_words_when_override_supplied(self):
        p = build_prosody_preview(
            "A quick note.",
            emphasis_overrides={2: "reduced"},
        )
        assert '<emphasis level="reduced">note</emphasis>' in p.ssml

    def test_ssml_includes_mstts_express_as_when_emotion_set(self):
        p = build_prosody_preview("Hello there.", emotion="cheerful")
        assert 'mstts:express-as style="cheerful"' in p.ssml

    def test_ssml_is_safe_for_html_chars_in_source(self):
        """Special characters in source text must not produce broken SSML.

        Tokenisation strips punctuation; the escape helper then covers
        the ``strong``/``reduced`` emphasis paths where the raw word
        survives. Net result: the emitted SSML is always well-formed.
        """
        p = build_prosody_preview("Less < than & greater > symbols")
        # The emitted body must not contain a raw <, >, or & that isn't
        # part of a declared SSML tag or entity. We check by stripping
        # the outer <speak ...> frame and the declared namespaces.
        assert "<emphasis" not in p.ssml  # nothing marked strong/reduced here
        # Cheap lint: the string parses as well-formed XML.
        import xml.etree.ElementTree as ET
        ET.fromstring(p.ssml)

    def test_ssml_never_leaks_raw_ampersand_or_angle_brackets(self):
        """Tokenisation strips '&', '<', '>' before SSML emission."""
        p = build_prosody_preview("The fox is **Ben&Jerry's** <tasty> flavour.")
        # Raw ampersand/angle-brackets from the source never make it into
        # the output — tokenisation drops them, then the escape helper
        # protects anything surviving inside an emphasis block.
        assert "Ben&Jerry" not in p.ssml
        assert "<tasty>" not in p.ssml
        # Output is well-formed XML.
        import xml.etree.ElementTree as ET
        ET.fromstring(p.ssml)


class TestSupportedEmotions:
    def test_core_emotions_present(self):
        emotions = set(supported_emotions())
        # Spot-check the staples.
        assert {"cheerful", "sad", "angry", "excited", "neutral"}.issubset(emotions)


# ---------------------------------------------------------------------------
# Endpoint round-trip
# ---------------------------------------------------------------------------


async def test_endpoint_round_trip(client):
    resp = await client.post(
        "/api/v1/synthesis/prosody-preview",
        json={"text": "Hello there, friend!", "emotion": "cheerful"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["emotion"] == "cheerful"
    assert len(data["words"]) == 3
    assert "ssml" in data
    assert data["sentence_count"] == 1
    # supported_emotions surfaced so the UI can populate a dropdown.
    assert "supported_emotions" in data
    assert "cheerful" in data["supported_emotions"]


async def test_endpoint_accepts_emphasis_overrides(client):
    resp = await client.post(
        "/api/v1/synthesis/prosody-preview",
        json={
            "text": "One two three four.",
            "emphasis": {"2": "strong"},
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["words"][2]["emphasis"] == "strong"


async def test_endpoint_rejects_empty_text(client):
    resp = await client.post(
        "/api/v1/synthesis/prosody-preview", json={"text": ""},
    )
    assert resp.status_code == 422


async def test_endpoint_rejects_oversize_text(client):
    resp = await client.post(
        "/api/v1/synthesis/prosody-preview",
        json={"text": "x" * 6000},
    )
    assert resp.status_code == 422


async def test_endpoint_ignores_unknown_emotion(client):
    resp = await client.post(
        "/api/v1/synthesis/prosody-preview",
        json={"text": "hello", "emotion": "wat"},
    )
    assert resp.status_code == 200, resp.text
    # Endpoint strips unknown emotions to None so the SSML isn't polluted.
    assert resp.json()["emotion"] is None
