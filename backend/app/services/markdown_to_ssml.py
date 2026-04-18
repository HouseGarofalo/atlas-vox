"""Markdown + custom-directive to SSML compiler.

Converts a small subset of markdown plus Atlas Vox custom directives into
provider-neutral SSML.  The compiler is capability-aware: if the destination
provider does not support SSML, the compiler returns clean plain text with
all tags and directives stripped.

Supported custom directives
---------------------------
* ``[pause:500ms]`` or ``[pause:2s]``         — inserts a ``<break>`` element.
* ``[emphasis:strong]text[/emphasis]``        — wraps text in ``<emphasis>``.
* ``[pitch:+20%]text[/pitch]``                — wraps text in ``<prosody pitch=...>``.
* ``[rate:slow]text[/rate]``                  — wraps text in ``<prosody rate=...>``.
* ``[say-as:characters]ABC[/say-as]``         — wraps in ``<say-as interpret-as=...>``.

Supported markdown
------------------
* ``**bold**``           → ``<emphasis level="strong">...</emphasis>``
* ``*italic*``           → ``<emphasis level="moderate">...</emphasis>``
* Paragraph breaks (blank line) → ``<break time="500ms"/>``.

Reusable across SynthesisLab and AP-41 audiobook stitcher.
"""

from __future__ import annotations

import re
from xml.sax.saxutils import escape as xml_escape

import structlog

from app.providers.base import ProviderCapabilities

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Directive patterns
# ---------------------------------------------------------------------------

# Valid emphasis levels (W3C SSML)
_VALID_EMPHASIS_LEVELS = {"strong", "moderate", "reduced", "none"}

# Valid rate keywords
_VALID_RATE_KEYWORDS = {"x-slow", "slow", "medium", "fast", "x-fast", "default"}

# Valid say-as interpret-as values we recognise
_VALID_SAY_AS = {
    "characters",
    "spell-out",
    "cardinal",
    "number",
    "ordinal",
    "digits",
    "fraction",
    "date",
    "time",
    "telephone",
    "address",
    "expletive",
    "unit",
    "verbatim",
}

# [pause:500ms] / [pause:2s]  (self-closing directive)
_PAUSE_RE = re.compile(r"\[pause:([0-9]+(?:\.[0-9]+)?)(ms|s)\]", re.IGNORECASE)

# Paired directives of the form [name:value]text[/name]
# Captures: 1=name, 2=value, 3=inner text (non-greedy)
_PAIRED_RE = re.compile(
    r"\[(emphasis|pitch|rate|say-as):([^\]]+)\](.*?)\[/\1\]",
    re.IGNORECASE | re.DOTALL,
)

# Bold / italic.  Order matters: process bold before italic.
_BOLD_RE = re.compile(r"\*\*([^*]+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)")

# Markdown heading lines.  Headings contribute no audible text – they are
# stripped.  The audiobook stitcher handles chapter segmentation separately.
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.*)$", re.MULTILINE)

# Strip all XML/HTML-ish tags (used for non-SSML providers).
_TAG_RE = re.compile(r"<[^>]+>")


def _sanitize_duration(raw_value: str, unit: str) -> str | None:
    """Validate and normalize a pause duration token.

    Returns ``"500ms"`` / ``"2s"`` or ``None`` if the value is malformed.
    """
    try:
        value = float(raw_value)
    except ValueError:
        return None
    if value <= 0 or value > 60_000:
        return None
    return f"{raw_value}{unit.lower()}"


def _render_pause(match: re.Match) -> str:
    duration = _sanitize_duration(match.group(1), match.group(2))
    if duration is None:
        return match.group(0)  # pass through malformed as literal
    return f'<break time="{duration}"/>'


def _render_paired(match: re.Match) -> str:
    name = match.group(1).lower()
    value = match.group(2).strip()
    inner = match.group(3)

    # Recurse so nested directives are expanded.
    inner_rendered = _expand_directives(inner)

    if name == "emphasis":
        level = value.lower()
        if level not in _VALID_EMPHASIS_LEVELS:
            return match.group(0)  # malformed -> literal passthrough
        return f'<emphasis level="{level}">{inner_rendered}</emphasis>'

    if name == "pitch":
        # Accept +20%, -5st, medium, etc.  Be permissive but XML-safe.
        safe_value = xml_escape(value, {'"': "&quot;"})
        return f'<prosody pitch="{safe_value}">{inner_rendered}</prosody>'

    if name == "rate":
        if value.lower() in _VALID_RATE_KEYWORDS or re.match(r"^[0-9]+%$", value):
            safe_value = xml_escape(value, {'"': "&quot;"})
            return f'<prosody rate="{safe_value}">{inner_rendered}</prosody>'
        return match.group(0)

    if name == "say-as":
        if value.lower() not in _VALID_SAY_AS:
            return match.group(0)
        safe_value = xml_escape(value, {'"': "&quot;"})
        # say-as contents are verbatim — do not recurse into inner text.
        return f'<say-as interpret-as="{safe_value}">{xml_escape(inner)}</say-as>'

    # Unknown directive name — shouldn't happen with the regex but be safe.
    return match.group(0)


def _expand_directives(text: str) -> str:
    """Expand directives and simple markdown; assumes `text` is already safe
    (no stray unescaped ``<`` / ``&``).
    """
    # Paired directives first, because they may wrap bold/italic markers.
    text = _PAIRED_RE.sub(_render_paired, text)
    # Pause is self-closing, order independent.
    text = _PAUSE_RE.sub(_render_pause, text)
    # Markdown emphasis.
    text = _BOLD_RE.sub(
        lambda m: f'<emphasis level="strong">{m.group(1)}</emphasis>', text
    )
    text = _ITALIC_RE.sub(
        lambda m: f'<emphasis level="moderate">{m.group(1)}</emphasis>', text
    )
    return text


def _split_paragraphs(markdown: str) -> list[str]:
    """Split markdown into paragraphs on blank lines, after dropping headings."""
    stripped = _HEADING_RE.sub("", markdown)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", stripped) if p.strip()]
    return paragraphs


def compile_to_ssml(
    markdown: str,
    provider_capabilities: ProviderCapabilities,
) -> str:
    """Compile markdown + directives into SSML or plain text.

    Args:
        markdown: Source text with optional markdown and Atlas Vox directives.
        provider_capabilities: Target provider's capability descriptor.

    Returns:
        SSML string wrapped in ``<speak>`` when the provider supports SSML,
        otherwise a plain-text rendering with all tags / directives stripped.
    """
    if not isinstance(markdown, str):
        raise TypeError("markdown must be a string")

    # --- Plain text path ---------------------------------------------------
    if not provider_capabilities.supports_ssml:
        # Strip directives: first pass removes paired directives but keeps
        # their inner text; pauses are removed entirely.
        text = _PAIRED_RE.sub(lambda m: m.group(3), markdown)
        text = _PAUSE_RE.sub("", text)
        text = _BOLD_RE.sub(lambda m: m.group(1), text)
        text = _ITALIC_RE.sub(lambda m: m.group(1), text)
        text = _HEADING_RE.sub(lambda m: m.group(1), text)
        # Remove any lingering XML-ish tags (defensive).
        text = _TAG_RE.sub("", text)
        # Collapse excessive whitespace.
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        logger.debug("ssml_plain_fallback", chars=len(text))
        return text

    # --- SSML path ---------------------------------------------------------
    # Escape XML special characters in the raw source *before* expansion so
    # user text never breaks the markup.  Directive brackets are ASCII and
    # survive escaping unchanged.
    paragraphs = _split_paragraphs(markdown)
    rendered: list[str] = []
    for para in paragraphs:
        safe = xml_escape(para)
        expanded = _expand_directives(safe)
        rendered.append(f"<p>{expanded}</p>")

    body = '<break time="500ms"/>'.join(rendered)
    ssml = f"<speak>{body}</speak>"
    logger.debug("ssml_compiled", paragraphs=len(paragraphs), chars=len(ssml))
    return ssml


__all__ = ["compile_to_ssml"]
