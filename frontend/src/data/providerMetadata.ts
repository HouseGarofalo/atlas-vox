export interface ProviderMetadata {
  description: string;
  website: string;
  modelInfo: string;
  pricingTier: "free" | "freemium" | "paid" | "open-source";
  category: "cloud" | "local-cpu" | "local-gpu";
  highlights: string[];
}

export const PROVIDER_METADATA: Record<string, ProviderMetadata> = {
  kokoro: {
    description:
      "Lightweight, fast TTS with 54 built-in voices. CPU-only, no GPU required.",
    website: "https://github.com/hexgrad/kokoro",
    modelInfo: "82M parameters, ONNX runtime",
    pricingTier: "open-source",
    category: "local-cpu",
    highlights: [
      "54 built-in voices",
      "CPU-only, fast inference",
      "American & British English",
    ],
  },
  coqui_xtts: {
    description:
      "State-of-the-art voice cloning from just 6 seconds of audio. Multilingual support for 16 languages.",
    website: "https://github.com/coqui-ai/TTS",
    modelInfo: "XTTS v2, ~1.5B parameters",
    pricingTier: "open-source",
    category: "local-gpu",
    highlights: [
      "Voice cloning from 6s audio",
      "16 languages",
      "Zero-shot synthesis",
    ],
  },
  piper: {
    description:
      "Fast, local TTS optimized for Raspberry Pi and Home Assistant. ONNX-based with many pre-trained voices.",
    website: "https://github.com/rhasspy/piper",
    modelInfo: "ONNX VITS models, various sizes",
    pricingTier: "open-source",
    category: "local-cpu",
    highlights: [
      "Home Assistant compatible",
      "Very low resource usage",
      "16 languages",
    ],
  },
  elevenlabs: {
    description:
      "Industry-leading cloud TTS with natural, expressive voices. Instant voice cloning and multilingual support.",
    website: "https://elevenlabs.io",
    modelInfo: "Proprietary, cloud-hosted",
    pricingTier: "freemium",
    category: "cloud",
    highlights: [
      "Most natural-sounding",
      "Instant voice cloning",
      "Streaming support",
    ],
  },
  azure_speech: {
    description:
      "Microsoft Azure Cognitive Services TTS with neural voices, SSML support, and enterprise reliability.",
    website:
      "https://azure.microsoft.com/en-us/products/ai-services/text-to-speech",
    modelInfo: "Azure Neural TTS",
    pricingTier: "paid",
    category: "cloud",
    highlights: [
      "Full SSML support",
      "Enterprise SLA",
      "400+ neural voices",
    ],
  },
  styletts2: {
    description:
      "Style diffusion and adversarial training for expressive, human-level TTS. Zero-shot voice transfer.",
    website: "https://github.com/yl4579/StyleTTS2",
    modelInfo: "~200M parameters",
    pricingTier: "open-source",
    category: "local-gpu",
    highlights: [
      "Human-level quality",
      "Style transfer",
      "Zero-shot cloning",
    ],
  },
  cosyvoice: {
    description:
      "Alibaba's multilingual TTS with natural prosody. Supports 9 languages with streaming output.",
    website: "https://github.com/FunAudioLLM/CosyVoice",
    modelInfo: "CosyVoice-300M-SFT",
    pricingTier: "open-source",
    category: "local-gpu",
    highlights: ["9 languages", "Natural prosody", "Streaming support"],
  },
  dia: {
    description:
      "Nari Labs dialogue TTS with 1.6B parameters. Generates natural multi-speaker conversations with non-verbal sounds.",
    website: "https://github.com/nari-labs/dia",
    modelInfo: "1.6B parameters",
    pricingTier: "open-source",
    category: "local-gpu",
    highlights: [
      "Multi-speaker dialogue",
      "Non-verbal sounds",
      "Voice cloning",
    ],
  },
  dia2: {
    description:
      "Next-gen dialogue model from Nari Labs with 2B parameters. Streaming support for real-time conversation generation.",
    website: "https://github.com/nari-labs/dia",
    modelInfo: "2B parameters",
    pricingTier: "open-source",
    category: "local-gpu",
    highlights: [
      "2B parameter model",
      "Streaming dialogue",
      "Real-time generation",
    ],
  },
};
