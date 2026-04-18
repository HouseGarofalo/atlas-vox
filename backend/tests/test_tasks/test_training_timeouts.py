"""P1-08 regression: subprocess + HTTP calls must honour timeouts."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.tasks.training import _ensure_wav


def test_ensure_wav_returns_original_on_ffmpeg_timeout(tmp_path: Path):
    """A stalled ffmpeg must surface as a timeout without stalling the worker."""
    src = tmp_path / "sample.m4a"
    src.write_bytes(b"fake m4a")

    with patch("app.tasks.training.subprocess.run") as run_mock:
        run_mock.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=120)
        result = _ensure_wav(src)

    # Fell back to the original file rather than hanging.
    assert result == src
    # We actually passed a timeout to subprocess.run.
    call_kwargs = run_mock.call_args.kwargs
    assert "timeout" in call_kwargs
    assert call_kwargs["timeout"] > 0


def test_ensure_wav_cleans_up_partial_output_on_timeout(tmp_path: Path):
    """Timed-out ffmpeg can leave a partial wav; we must not reuse it."""
    src = tmp_path / "sample.m4a"
    src.write_bytes(b"fake m4a")
    # Simulate a partial output existing after timeout.
    partial = src.with_suffix(".wav")

    def _fake_run(*a, **kw):
        partial.write_bytes(b"partial")
        raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=120)

    with patch("app.tasks.training.subprocess.run", side_effect=_fake_run):
        result = _ensure_wav(src)

    assert result == src  # returned original, not partial
    assert not partial.exists(), "Partial output should be cleaned up on timeout"


def test_ensure_wav_passes_through_when_already_wav(tmp_path: Path):
    src = tmp_path / "sample.wav"
    src.write_bytes(b"fake wav")
    # No subprocess call should happen; if the mock IS invoked the test fails
    # because no timeout param was provided to the mock.
    with patch("app.tasks.training.subprocess.run") as run_mock:
        result = _ensure_wav(src)
        run_mock.assert_not_called()
    assert result == src


def test_azure_token_fetch_timeout_is_bounded(monkeypatch):
    """credential.get_token() must be wrapped with a hard timeout."""
    # This is a structural test — we inspect the wrapper exists and yields a
    # bounded timeout rather than calling Azure from CI.
    from app.providers import azure_speech

    src = Path(azure_speech.__file__).read_text(encoding="utf-8")
    # The original credential.get_token() call MUST be guarded by a
    # ThreadPoolExecutor with a timeout.
    assert "concurrent.futures" in src, "azure_speech must import concurrent.futures for timeout"
    assert "TOKEN_FETCH_TIMEOUT_SECONDS" in src, "Timeout constant missing"
    assert "future.result(timeout=TOKEN_FETCH_TIMEOUT_SECONDS" in src

    from app.providers import azure_auth

    src2 = Path(azure_auth.__file__).read_text(encoding="utf-8")
    assert "TOKEN_FETCH_TIMEOUT_SECONDS" in src2
    assert "future.result(timeout=TOKEN_FETCH_TIMEOUT_SECONDS" in src2
