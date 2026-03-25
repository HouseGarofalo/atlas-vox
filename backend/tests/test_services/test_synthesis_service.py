"""Tests for synthesis service — text chunking."""

from __future__ import annotations

from app.services.synthesis_service import _split_text


class TestTextChunking:
    def test_short_text_no_split(self):
        chunks = _split_text("Hello world.", max_chars=1000)
        assert chunks == ["Hello world."]

    def test_splits_at_sentence_boundary(self):
        text = "First sentence. Second sentence. Third sentence."
        chunks = _split_text(text, max_chars=30)
        assert len(chunks) >= 2
        # All original text should be present
        rejoined = " ".join(chunks)
        assert "First sentence." in rejoined
        assert "Third sentence." in rejoined

    def test_handles_long_sentence(self):
        text = "word " * 500  # Very long single sentence
        chunks = _split_text(text.strip(), max_chars=100)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 100

    def test_empty_text(self):
        chunks = _split_text("", max_chars=1000)
        assert chunks == [""]

    def test_exact_boundary(self):
        text = "A" * 1000
        chunks = _split_text(text, max_chars=1000)
        assert chunks == [text]
