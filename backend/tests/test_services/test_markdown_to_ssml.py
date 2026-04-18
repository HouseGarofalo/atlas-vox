"""Tests for the markdown-to-SSML compiler (AP-42)."""

from __future__ import annotations

from app.providers.base import ProviderCapabilities
from app.services.markdown_to_ssml import compile_to_ssml


def _ssml_caps() -> ProviderCapabilities:
    return ProviderCapabilities(supports_ssml=True)


def _plain_caps() -> ProviderCapabilities:
    return ProviderCapabilities(supports_ssml=False)


class TestDirectives:
    def test_pause_directive_ms(self):
        out = compile_to_ssml("Hello [pause:500ms] world", _ssml_caps())
        assert '<break time="500ms"/>' in out

    def test_pause_directive_seconds(self):
        out = compile_to_ssml("Wait [pause:2s] now", _ssml_caps())
        assert '<break time="2s"/>' in out

    def test_emphasis_strong(self):
        out = compile_to_ssml(
            "Say [emphasis:strong]important[/emphasis] now", _ssml_caps()
        )
        assert '<emphasis level="strong">important</emphasis>' in out

    def test_emphasis_moderate(self):
        out = compile_to_ssml(
            "Say [emphasis:moderate]it[/emphasis]", _ssml_caps()
        )
        assert '<emphasis level="moderate">it</emphasis>' in out

    def test_pitch_directive(self):
        out = compile_to_ssml("[pitch:+20%]high[/pitch]", _ssml_caps())
        assert '<prosody pitch="+20%">high</prosody>' in out

    def test_rate_directive_keyword(self):
        out = compile_to_ssml("[rate:slow]slow text[/rate]", _ssml_caps())
        assert '<prosody rate="slow">slow text</prosody>' in out

    def test_rate_directive_percent(self):
        out = compile_to_ssml("[rate:75%]text[/rate]", _ssml_caps())
        assert '<prosody rate="75%">text</prosody>' in out

    def test_say_as_characters(self):
        out = compile_to_ssml("[say-as:characters]ABC[/say-as]", _ssml_caps())
        assert '<say-as interpret-as="characters">ABC</say-as>' in out


class TestMarkdown:
    def test_bold_becomes_strong_emphasis(self):
        out = compile_to_ssml("This is **bold** text", _ssml_caps())
        assert '<emphasis level="strong">bold</emphasis>' in out

    def test_italic_becomes_moderate_emphasis(self):
        out = compile_to_ssml("This is *italic* text", _ssml_caps())
        assert '<emphasis level="moderate">italic</emphasis>' in out

    def test_paragraph_break_inserted(self):
        md = "First paragraph.\n\nSecond paragraph."
        out = compile_to_ssml(md, _ssml_caps())
        assert out.count("<p>") == 2
        assert '<break time="500ms"/>' in out

    def test_wraps_in_speak(self):
        out = compile_to_ssml("Hello world", _ssml_caps())
        assert out.startswith("<speak>")
        assert out.endswith("</speak>")


class TestNesting:
    def test_nested_directives(self):
        md = "[rate:slow]He said [emphasis:strong]stop[/emphasis] now[/rate]"
        out = compile_to_ssml(md, _ssml_caps())
        assert '<prosody rate="slow">' in out
        assert '<emphasis level="strong">stop</emphasis>' in out

    def test_bold_inside_directive(self):
        md = "[rate:slow]this is **very** loud[/rate]"
        out = compile_to_ssml(md, _ssml_caps())
        assert '<emphasis level="strong">very</emphasis>' in out
        assert '<prosody rate="slow">' in out


class TestMalformed:
    def test_malformed_pause_passed_through(self):
        # Pause without unit is malformed.
        out = compile_to_ssml("[pause:foo] text", _ssml_caps())
        assert "[pause:foo]" in out

    def test_unknown_emphasis_level_passthrough(self):
        out = compile_to_ssml("[emphasis:bogus]x[/emphasis]", _ssml_caps())
        assert "[emphasis:bogus]x[/emphasis]" in out

    def test_unknown_say_as_passthrough(self):
        out = compile_to_ssml("[say-as:whatever]x[/say-as]", _ssml_caps())
        assert "[say-as:whatever]x[/say-as]" in out


class TestPlainFallback:
    def test_strips_all_directives_when_no_ssml(self):
        md = "[pause:500ms]Say [emphasis:strong]hello[/emphasis] **world**"
        out = compile_to_ssml(md, _plain_caps())
        assert "<" not in out
        assert "[pause" not in out
        assert "hello" in out
        assert "world" in out

    def test_plain_drops_heading_markers(self):
        md = "# Chapter One\n\nNarration here."
        out = compile_to_ssml(md, _plain_caps())
        assert "#" not in out
        assert "Chapter One" in out
        assert "Narration here." in out

    def test_xml_special_chars_escaped(self):
        # Ampersand + angle brackets must not appear raw in SSML output.
        out = compile_to_ssml("Tom & Jerry say <hi>", _ssml_caps())
        assert "&amp;" in out
        assert "&lt;hi&gt;" in out
