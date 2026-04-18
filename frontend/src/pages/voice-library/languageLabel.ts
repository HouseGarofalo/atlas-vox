/**
 * Shared helpers used by VoiceLibraryPage and its sub-components.
 *
 * Extracted from VoiceLibraryPage.tsx as part of P2-20 (decompose large pages).
 */

import type { Voice } from "../../types";

/** Map language codes to human-readable labels. */
export function languageLabel(code: string): string {
  const map: Record<string, string> = {
    en: "English",
    "en-US": "English (US)",
    "en-GB": "English (UK)",
    "en-AU": "English (AU)",
    "en-IN": "English (IN)",
    "en-IE": "English (IE)",
    "en-CA": "English (CA)",
    "en-NZ": "English (NZ)",
    "en-ZA": "English (ZA)",
    "en-SG": "English (SG)",
    "en-PH": "English (PH)",
    "en-HK": "English (HK)",
    "en-KE": "English (KE)",
    "en-NG": "English (NG)",
    es: "Spanish",
    fr: "French",
    de: "German",
    zh: "Chinese",
    ja: "Japanese",
    ko: "Korean",
    pt: "Portuguese",
    ru: "Russian",
    it: "Italian",
    ar: "Arabic",
    hi: "Hindi",
    nl: "Dutch",
    pl: "Polish",
    tr: "Turkish",
    sv: "Swedish",
    da: "Danish",
    fi: "Finnish",
    no: "Norwegian",
    cs: "Czech",
    uk: "Ukrainian",
  };
  return map[code] ?? code.toUpperCase();
}

/** Try to infer gender from voice name or id patterns (fallback when backend doesn't provide it). */
export function inferGender(voice: Voice): string | null {
  const id = voice.voice_id.toLowerCase();
  const name = voice.name.toLowerCase();

  // Kokoro pattern: af_*, am_*, bf_*, bm_*
  if (/^[ab]f[_-]/.test(id)) return "Female";
  if (/^[ab]m[_-]/.test(id)) return "Male";

  // Common keywords
  if (name.includes("female") || name.includes("woman")) return "Female";
  if (name.includes("male") || name.includes("man ")) return "Male";

  return null;
}
