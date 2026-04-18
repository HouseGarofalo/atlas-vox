/**
 * SSML 1.1 tag/attribute schema used by the Monaco SSML editor for
 * autocomplete, hover hints, and provider-aware validation.
 *
 * References:
 *  - W3C SSML 1.1 Recommendation
 *  - Azure Cognitive Services Speech SSML extensions (mstts:*)
 *  - ElevenLabs SSML-like subset (break, emphasis, prosody limited)
 */

export interface SSMLAttributeDef {
  name: string;
  description: string;
  values?: string[];
}

export interface SSMLTagDef {
  name: string;
  description: string;
  attributes: SSMLAttributeDef[];
  /**
   * Provider names (as used in `provider_registry`) for which this tag is
   * supported. Null ⇒ supported by every SSML-capable provider.
   */
  supportedBy: string[] | null;
}

export const SSML_TAGS: SSMLTagDef[] = [
  {
    name: "speak",
    description: "SSML root element. Required.",
    supportedBy: null,
    attributes: [
      { name: "version", description: "SSML version", values: ["1.0", "1.1"] },
      { name: "xmlns", description: "XML namespace (http://www.w3.org/2001/10/synthesis)" },
      { name: "xml:lang", description: "Primary language code", values: ["en-US", "en-GB", "es-ES", "fr-FR", "de-DE", "ja-JP", "zh-CN"] },
    ],
  },
  {
    name: "voice",
    description: "Select a specific voice to speak the enclosed text.",
    supportedBy: null,
    attributes: [
      { name: "name", description: "Voice identifier or short-name" },
      { name: "gender", description: "Voice gender", values: ["male", "female", "neutral"] },
      { name: "xml:lang", description: "Language override for this voice" },
    ],
  },
  {
    name: "prosody",
    description: "Control rate, pitch, and volume of the enclosed text.",
    supportedBy: null,
    attributes: [
      { name: "rate", description: "Speaking rate", values: ["x-slow", "slow", "medium", "fast", "x-fast", "-50%", "+50%"] },
      { name: "pitch", description: "Pitch adjustment", values: ["x-low", "low", "medium", "high", "x-high", "-50%", "+50%"] },
      { name: "volume", description: "Volume level", values: ["silent", "x-soft", "soft", "medium", "loud", "x-loud"] },
      { name: "contour", description: "Pitch contour (provider-specific)" },
      { name: "range", description: "Pitch range" },
    ],
  },
  {
    name: "emphasis",
    description: "Indicate stress. Providers render varying levels.",
    supportedBy: null,
    attributes: [
      { name: "level", description: "Emphasis level", values: ["strong", "moderate", "none", "reduced"] },
    ],
  },
  {
    name: "break",
    description: "Insert a pause. Self-closing.",
    supportedBy: null,
    attributes: [
      { name: "time", description: "Pause length (e.g. 500ms, 2s)" },
      { name: "strength", description: "Pause strength", values: ["none", "x-weak", "weak", "medium", "strong", "x-strong"] },
    ],
  },
  {
    name: "say-as",
    description: "Interpret enclosed text as a specific content type.",
    supportedBy: null,
    attributes: [
      { name: "interpret-as", description: "Content type", values: ["characters", "spell-out", "cardinal", "ordinal", "digits", "fraction", "unit", "date", "time", "telephone", "address", "currency"] },
      { name: "format", description: "Format hint (for date/time)" },
      { name: "detail", description: "Detail level" },
    ],
  },
  {
    name: "phoneme",
    description: "Provide an explicit pronunciation for the enclosed text.",
    supportedBy: null,
    attributes: [
      { name: "alphabet", description: "Phoneme alphabet", values: ["ipa", "x-sampa"] },
      { name: "ph", description: "Phonetic transcription" },
    ],
  },
  {
    name: "sub",
    description: "Substitute alternate text for pronunciation.",
    supportedBy: null,
    attributes: [
      { name: "alias", description: "Alternate text to pronounce" },
    ],
  },
  {
    name: "lexicon",
    description: "External pronunciation lexicon reference. Self-closing.",
    supportedBy: null,
    attributes: [
      { name: "uri", description: "Lexicon URI" },
      { name: "xml:id", description: "Lexicon identifier" },
    ],
  },
  {
    name: "audio",
    description: "Insert pre-recorded audio. Self-closing when empty.",
    supportedBy: null,
    attributes: [
      { name: "src", description: "Audio resource URL" },
      { name: "soundLevel", description: "Level adjustment (provider-specific)" },
    ],
  },
  {
    name: "p",
    description: "Paragraph. Usually adds surrounding pauses.",
    supportedBy: null,
    attributes: [],
  },
  {
    name: "s",
    description: "Sentence. Usually adds surrounding pauses.",
    supportedBy: null,
    attributes: [],
  },
  {
    name: "lang",
    description: "Mark a language span (cross-lingual providers).",
    supportedBy: null,
    attributes: [
      { name: "xml:lang", description: "Language code" },
    ],
  },
  // Azure-specific mstts: extensions
  {
    name: "mstts:express-as",
    description: "Azure expressive style (emotion).",
    supportedBy: ["azure_speech"],
    attributes: [
      { name: "style", description: "Emotion style", values: ["neutral", "cheerful", "sad", "angry", "excited", "friendly", "hopeful", "whispering", "terrified", "unfriendly", "shouting", "empathetic", "calm", "gentle", "serious", "assistant", "chat", "customer-service", "newscast-casual", "newscast-formal", "narration-professional"] },
      { name: "styledegree", description: "Style intensity (0.01-2.0)" },
      { name: "role", description: "Role play", values: ["Girl", "Boy", "YoungAdultFemale", "YoungAdultMale", "OlderAdultFemale", "OlderAdultMale", "SeniorFemale", "SeniorMale"] },
    ],
  },
  {
    name: "mstts:silence",
    description: "Azure custom silence insertion.",
    supportedBy: ["azure_speech"],
    attributes: [
      { name: "type", description: "Silence type", values: ["Leading", "Tailing", "Sentenceboundary", "Comma-exact", "Semicolon-exact", "Enumerationcomma-exact"] },
      { name: "value", description: "Silence duration" },
    ],
  },
];

const SELF_CLOSING = new Set(["break", "lexicon", "audio"]);

export function isSelfClosing(tag: string): boolean {
  return SELF_CLOSING.has(tag);
}

/**
 * Subset of SSML tags supported by the given provider name. Tags with
 * ``supportedBy === null`` are considered universal; tags with an explicit
 * list must include the provider.
 */
export function tagsForProvider(providerName: string | null | undefined): SSMLTagDef[] {
  if (!providerName) return SSML_TAGS.filter((t) => t.supportedBy === null);
  return SSML_TAGS.filter((t) => t.supportedBy === null || t.supportedBy.includes(providerName));
}

export function findTag(name: string): SSMLTagDef | undefined {
  return SSML_TAGS.find((t) => t.name === name);
}
