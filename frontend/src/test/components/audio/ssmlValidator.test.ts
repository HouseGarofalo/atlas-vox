import { describe, it, expect } from "vitest";
import {
  validateSSML,
  type SSMLDiagnostic,
} from "../../../components/audio/ssmlValidator";
import { tagsForProvider, findTag } from "../../../components/audio/ssmlSchema";

describe("ssml schema", () => {
  it("filters Azure-only tags for non-Azure providers", () => {
    const azureOnly = tagsForProvider("kokoro").some((t) => t.name === "mstts:express-as");
    expect(azureOnly).toBe(false);
    const azure = tagsForProvider("azure_speech").some((t) => t.name === "mstts:express-as");
    expect(azure).toBe(true);
  });

  it("returns universal tags when no provider specified", () => {
    const tags = tagsForProvider(null);
    expect(tags.find((t) => t.name === "speak")).toBeTruthy();
    expect(tags.find((t) => t.name === "mstts:express-as")).toBeUndefined();
  });

  it("findTag returns schema entries", () => {
    expect(findTag("prosody")?.attributes.some((a) => a.name === "rate")).toBe(true);
    expect(findTag("nope")).toBeUndefined();
  });
});

describe("validateSSML", () => {
  function msgs(d: SSMLDiagnostic[]): string[] {
    return d.map((x) => `${x.severity}:${x.message}`);
  }

  it("clean valid SSML produces no diagnostics", () => {
    const src = `<speak version="1.0">\n  <voice name="x">\n    <prosody rate="medium">Hello</prosody>\n  </voice>\n</speak>`;
    expect(validateSSML(src, null)).toEqual([]);
  });

  it("flags unknown tags as errors", () => {
    const src = `<speak><bogus>hi</bogus></speak>`;
    const out = validateSSML(src, null);
    expect(msgs(out)).toEqual(
      expect.arrayContaining([expect.stringMatching(/Unknown SSML tag <bogus>/)]),
    );
  });

  it("flags mismatched close tags", () => {
    const src = `<speak><voice name="a">hi</prosody></speak>`;
    const out = validateSSML(src, null);
    expect(msgs(out)).toEqual(
      expect.arrayContaining([expect.stringMatching(/Mismatched closing tag/)]),
    );
  });

  it("flags unclosed tags", () => {
    const src = `<speak><voice name="a">`;
    const out = validateSSML(src, null);
    expect(msgs(out)).toEqual(
      expect.arrayContaining([expect.stringMatching(/Unclosed tag <voice>/)]),
    );
  });

  it("self-closing break tag does not trigger unclosed error", () => {
    const src = `<speak><break time="500ms"/></speak>`;
    expect(validateSSML(src, null)).toEqual([]);
  });

  it("warns when a provider-specific tag is used with a different provider", () => {
    const src = `<speak><mstts:express-as style="cheerful">hi</mstts:express-as></speak>`;
    const out = validateSSML(src, "kokoro");
    expect(out.some((d) => d.severity === "warning" && /not supported/.test(d.message))).toBe(true);
  });

  it("accepts the same tag for the advertised provider", () => {
    const src = `<speak><mstts:express-as style="cheerful">hi</mstts:express-as></speak>`;
    const out = validateSSML(src, "azure_speech");
    expect(out.filter((d) => d.severity !== "info")).toEqual([]);
  });

  it("warns on undeclared attribute", () => {
    const src = `<speak><prosody unicorn="y">x</prosody></speak>`;
    const out = validateSSML(src, null);
    expect(out.some((d) => /unicorn/.test(d.message))).toBe(true);
  });

  it("reports accurate line numbers", () => {
    const src = `<speak>\n  <bogus/>\n</speak>`;
    const out = validateSSML(src, null);
    expect(out[0].startLine).toBe(2);
  });
});
