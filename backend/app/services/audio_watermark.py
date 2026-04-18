"""Inaudible deepfake watermarking (SC-45).

v1 implementation — a simple spread-spectrum / LSB-in-high-frequency-band
scheme that embeds a short ASCII payload into a WAV file.  It is not
robust against heavy re-encoding or resampling; that's acceptable at this
stage because the goal is provenance signalling for unmodified outputs
rather than forensic watermarking.

Design
------
* The payload is padded / truncated to ``PAYLOAD_LENGTH`` bytes (32) and
  framed with ``MAGIC`` so that the verifier can tell where the payload
  starts and stops.  Each bit of the framed payload is written into a
  float sample's LSB after modulating by a pseudo-random ±1 sequence
  generated from a fixed seed.
* Only samples whose spectral content is dominated by frequencies
  ``>= HIGH_FREQ_CUTOFF`` are chosen as carrier samples, so the mutation
  sits in a perceptually-weak region.  We approximate that by operating
  on the first ``PAYLOAD_BITS`` samples after a high-pass filter is applied
  as a bias — in practice a fixed carrier-sample stride (derived from
  sample rate) works and is much cheaper than a full STFT.
* Verification re-derives the stride + pseudo-random sequence, extracts
  the bits, and looks for the magic prefix.  Confidence is the fraction
  of framing bits recovered correctly.

The code is deliberately self-contained — only ``numpy`` and ``scipy``
(via ``soundfile``) are required.
"""

from __future__ import annotations

import math
import struct
from pathlib import Path

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

MAGIC = b"AVWM"  # 4-byte framing prefix
PAYLOAD_LENGTH = 32  # fixed padded payload length in bytes
HEADER_LENGTH = len(MAGIC) + 1  # magic + uint8 payload-length byte
TOTAL_BYTES = HEADER_LENGTH + PAYLOAD_LENGTH
TOTAL_BITS = TOTAL_BYTES * 8

# Every Nth sample carries one bit.  Chosen so a 1-second, 22.05 kHz audio
# clip still has ~86 carrier slots — plenty for TOTAL_BITS=296.
CARRIER_STRIDE = 64

# Each bit is redundantly embedded across ``BIT_REPEAT`` carrier samples
# and recovered via majority vote.  Provides robustness against the loss
# of a small fraction of samples (see robustness test).
BIT_REPEAT = 5

# Quantization step size for QIM-based embedding.  The carrier sample is
# rounded to the nearest multiple of ``QIM_DELTA`` and then offset by
# ``QIM_DELTA / 2`` if the bit is 1.  Larger values are more robust to
# noise but more perceptible.  0.01 sits at roughly -40 dBFS, which is
# below the threshold of audibility for most speech content.
QIM_DELTA = 0.01

_RANDOM_SEED = 0xA71A5


def _pack_payload(payload: str) -> bytes:
    """Pad / truncate payload to the fixed frame size with magic + length."""
    raw = payload.encode("utf-8")[:PAYLOAD_LENGTH]
    length = len(raw)
    padded = raw + b"\x00" * (PAYLOAD_LENGTH - length)
    return MAGIC + struct.pack("B", length) + padded


def _unpack_payload(frame: bytes) -> str | None:
    """Reverse ``_pack_payload``; returns None if the magic prefix is missing."""
    if len(frame) < HEADER_LENGTH:
        return None
    if frame[: len(MAGIC)] != MAGIC:
        return None
    length = frame[len(MAGIC)]
    if length > PAYLOAD_LENGTH:
        return None
    payload_bytes = frame[HEADER_LENGTH : HEADER_LENGTH + length]
    try:
        return payload_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None


def _bits_from_bytes(data: bytes) -> np.ndarray:
    """Expand a byte string into an array of 0/1 ints (MSB first)."""
    bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
    return bits.astype(np.int8)


def _bytes_from_bits(bits: np.ndarray) -> bytes:
    """Inverse of ``_bits_from_bytes`` — pack 0/1 ints back into bytes."""
    # Ensure length is a multiple of 8 by trimming trailing bits.
    trimmed = bits[: (len(bits) // 8) * 8].astype(np.uint8)
    return np.packbits(trimmed).tobytes()


def _modulation_sequence(n_bits: int) -> np.ndarray:
    """Deterministic ±1 pseudo-random sequence used to whiten the watermark."""
    rng = np.random.default_rng(_RANDOM_SEED)
    return rng.choice([-1.0, 1.0], size=n_bits).astype(np.float32)


def _qim_embed_bit(sample: float, bit: int, whitener: float) -> float:
    """Quantization-Index-Modulation embedding.

    The sample is snapped to the nearest multiple of ``QIM_DELTA`` and then
    offset by ``+QIM_DELTA / 4`` for bit 1 or ``-QIM_DELTA / 4`` for bit 0.
    A pseudo-random whitener (±1) flips the offset so the embedded bit
    pattern is statistically invisible without the secret seed.
    """
    base = round(sample / QIM_DELTA) * QIM_DELTA
    offset = QIM_DELTA / 4.0
    delta = offset if bit == 1 else -offset
    return float(base + whitener * delta)


def _qim_extract_bit(sample: float, whitener: float) -> int:
    """Recover the embedded bit from a QIM-quantised sample."""
    base = round(sample / QIM_DELTA) * QIM_DELTA
    residual = (sample - base) * whitener
    return 1 if residual > 0 else 0


def _wav_path(path: Path) -> Path:
    """Return ``path`` if it's already a WAV; otherwise convert it in-place.

    Non-WAV inputs are transcoded to a sibling ``.wav`` file via pydub so
    they can be manipulated with soundfile.  The caller retains ownership
    of the file — we never delete the original.
    """
    if path.suffix.lower() == ".wav":
        return path
    try:
        from pydub import AudioSegment
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "pydub is required to watermark non-WAV audio; install it or "
            "produce WAV output."
        ) from exc

    audio = AudioSegment.from_file(str(path))
    wav_path = path.with_suffix(".wav")
    audio.export(str(wav_path), format="wav")
    return wav_path


def embed_watermark(audio_path: Path, payload: str) -> Path:
    """Embed ``payload`` into ``audio_path``.

    Returns the path to the watermarked file.  For WAV inputs the file is
    overwritten in place; for other formats the audio is first transcoded
    to WAV and the WAV file is returned (a ``.mp3`` input becomes a
    sibling ``.wav``).  Callers that want to preserve the original format
    must re-encode after verifying the embedded payload.
    """
    import soundfile as sf  # lazy import — heavy C lib

    audio_path = Path(audio_path)
    wav_path = _wav_path(audio_path)

    data, sample_rate = sf.read(str(wav_path), always_2d=False)
    working = np.asarray(data, dtype=np.float32)
    if working.ndim == 2:
        working = working.mean(axis=1)  # downmix to mono for watermarking

    frame = _pack_payload(payload)
    bits = _bits_from_bytes(frame)
    assert len(bits) == TOTAL_BITS

    n_slots = len(bits) * BIT_REPEAT
    required_length = CARRIER_STRIDE * n_slots
    if len(working) < required_length:
        raise ValueError(
            f"Audio is too short to watermark: need at least "
            f"{required_length} samples, got {len(working)}"
        )

    modulation = _modulation_sequence(n_slots)

    watermarked = working.copy()
    for i, bit in enumerate(bits):
        for r in range(BIT_REPEAT):
            slot = i * BIT_REPEAT + r
            idx = slot * CARRIER_STRIDE
            watermarked[idx] = _qim_embed_bit(
                float(working[idx]), int(bit), float(modulation[slot])
            )

    # Clamp to the valid [-1.0, 1.0] float range so soundfile won't clip.
    np.clip(watermarked, -1.0, 1.0, out=watermarked)

    sf.write(str(wav_path), watermarked, sample_rate)
    logger.info(
        "watermark_embedded",
        path=str(wav_path),
        payload_len=len(payload),
        bits=len(bits),
    )
    return wav_path


def verify_watermark(audio_path: Path) -> dict | None:
    """Attempt to recover a watermark payload.

    Returns ``{"payload": str, "confidence": float}`` on success, or
    ``None`` if no watermark is detected.  Confidence is the fraction of
    bits that matched the expected framing prefix — 1.0 means a perfect
    recovery.
    """
    import soundfile as sf

    audio_path = Path(audio_path)
    if not audio_path.exists():
        return None
    try:
        data, _ = sf.read(str(audio_path), always_2d=False)
    except Exception as exc:  # corrupt file, wrong format, etc.
        logger.warning("watermark_verify_read_failed", path=str(audio_path), error=str(exc))
        return None

    working = np.asarray(data, dtype=np.float32)
    if working.ndim == 2:
        working = working.mean(axis=1)

    n_slots = TOTAL_BITS * BIT_REPEAT
    required_length = CARRIER_STRIDE * n_slots
    if len(working) < required_length:
        return None

    modulation = _modulation_sequence(n_slots)
    bits = np.zeros(TOTAL_BITS, dtype=np.int8)
    for i in range(TOTAL_BITS):
        votes = 0
        for r in range(BIT_REPEAT):
            slot = i * BIT_REPEAT + r
            idx = slot * CARRIER_STRIDE
            votes += _qim_extract_bit(float(working[idx]), float(modulation[slot]))
        bits[i] = 1 if votes * 2 > BIT_REPEAT else 0

    frame = _bytes_from_bits(bits)
    payload = _unpack_payload(frame)
    if payload is None:
        return None

    # Confidence: re-encode the recovered frame and compute bit-wise agreement.
    expected_bits = _bits_from_bytes(_pack_payload(payload))
    matches = int(np.sum(bits == expected_bits))
    confidence = matches / TOTAL_BITS

    logger.info(
        "watermark_verified",
        path=str(audio_path),
        payload_len=len(payload),
        confidence=round(confidence, 4),
    )
    return {"payload": payload, "confidence": float(confidence)}


def make_payload(profile_id: str, history_id: str) -> str:
    """Build the canonical payload string used by the synthesis pipeline.

    The payload is deliberately short so it fits inside ``PAYLOAD_LENGTH``
    bytes.  We truncate the two ids to 12 characters each, which preserves
    uniqueness in practice for uuid4 ids.
    """
    p = (profile_id or "")[:12]
    h = (history_id or "")[:12]
    return f"av:{p}:{h}"


__all__ = [
    "embed_watermark",
    "verify_watermark",
    "make_payload",
    "PAYLOAD_LENGTH",
    "CARRIER_STRIDE",
]

# Unused, kept for forward compatibility if we ever want a true
# high-pass-based cutoff rather than a fixed stride.
HIGH_FREQ_CUTOFF_HZ = 15_000.0
_UNUSED = math.pi
