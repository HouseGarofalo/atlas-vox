"""SSML sanitization — whitelist-based element filtering.

Prevents SSML injection by stripping unknown elements and limiting nesting depth.
"""

from __future__ import annotations

import re

import structlog

logger = structlog.get_logger(__name__)

# Allowed SSML elements (W3C + Azure extensions)
ALLOWED_ELEMENTS = frozenset({
    # W3C SSML 1.1 core
    "speak", "voice", "prosody", "break", "emphasis",
    "say-as", "phoneme", "sub", "p", "s", "mark",
    "audio", "desc", "lang",
    # Azure-specific extensions (mstts namespace)
    "mstts:express-as", "mstts:silence", "mstts:backgroundaudio",
    "mstts:viseme", "mstts:audioduration",
})

# Maximum nesting depth to prevent DoS via deeply nested elements
MAX_NESTING_DEPTH = 15

# Maximum SSML length (characters)
MAX_SSML_LENGTH = 50_000


def sanitize_ssml(ssml: str) -> str:
    """Sanitize SSML by removing disallowed elements and enforcing limits.

    Args:
        ssml: Raw SSML string from user input.

    Returns:
        Sanitized SSML with only whitelisted elements.

    Raises:
        ValueError: If SSML exceeds length or nesting limits.
    """
    if len(ssml) > MAX_SSML_LENGTH:
        raise ValueError(f"SSML too long ({len(ssml)} chars, max {MAX_SSML_LENGTH})")

    # Check nesting depth by counting max open-tag depth
    depth = 0
    max_depth = 0
    for match in re.finditer(r"<(/?)(\w[\w:-]*)", ssml):
        is_close = match.group(1) == "/"
        if is_close:
            depth = max(0, depth - 1)
        else:
            depth += 1
            max_depth = max(max_depth, depth)

    if max_depth > MAX_NESTING_DEPTH:
        raise ValueError(f"SSML nesting too deep ({max_depth} levels, max {MAX_NESTING_DEPTH})")

    # Remove disallowed elements (keep their text content)
    def _strip_unknown_tags(text: str) -> str:
        def _replace(m: re.Match) -> str:
            tag_name = m.group(2).lower()
            if tag_name in ALLOWED_ELEMENTS:
                return m.group(0)  # keep allowed
            logger.debug("ssml_stripped_element", element=tag_name)
            return ""  # strip unknown

        # Match opening tags, self-closing tags, and closing tags
        result = re.sub(r"<(/?)(\w[\w:-]*)([^>]*)(/?)>", _replace, text)
        return result

    sanitized = _strip_unknown_tags(ssml)
    return sanitized
