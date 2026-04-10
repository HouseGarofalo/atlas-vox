/**
 * Atlas Vox Theme Library
 *
 * Each theme is a complete visual identity — brand colors, neutrals, and atmosphere.
 * Themes define HSL values that flow through the entire design system via CSS variables.
 */

export interface ThemeColor {
  h: number; // 0-360
  s: number; // 0-100
  l: number; // 0-100 (base lightness, scale is derived)
}

export interface ThemeNeutrals {
  obsidian: string; // "h s% l%" format for HSL
  charcoal: string;
  slate: string;
  silver: string;
  white: string;
}

/**
 * Layout shell — defines the entire application chrome: nav structure,
 * header style, content arrangement, and unique decorative elements.
 * Each value maps to a different React component tree in LayoutSwitcher.
 */
export type LayoutShell =
  | "studio"        // Current: left sidebar channel-strip with VU meters
  | "minimal"       // Linear/Notion: top nav, huge whitespace, typography-first
  | "command"       // Bloomberg terminal: dense grid, ticker strip, data-first
  | "jarvis"        // Iron Man HUD: orbital nav, scanlines, corner brackets
  | "atlas"         // NORAD tactical: grid overlay, mission clock, callsigns
  | "bento";        // Apple bento: tiled asymmetric grid, glass cards

/**
 * ThemePersonality defines the complete look-and-feel beyond color.
 * Each value is written as a CSS variable that components consume.
 */
export interface ThemePersonality {
  // Shape language
  radius: "sharp" | "subtle" | "rounded" | "pill"; // 0px / 4px / 16px / 9999px
  borderWeight: "none" | "subtle" | "thin" | "thick" | "neon"; // 0/1/2/3px + glow

  // Typography
  font: "sans" | "display" | "serif" | "mono";
  headingWeight: "light" | "normal" | "bold" | "black"; // 300/500/700/900
  letterSpacing: "tight" | "normal" | "wide" | "extra-wide"; // -0.02/0/0.05/0.1em
  textTransform: "none" | "uppercase";

  // Visual treatments
  cardStyle: "flat" | "raised" | "glass" | "console" | "outline" | "neon" | "soft";
  shadowIntensity: "none" | "subtle" | "medium" | "dramatic" | "glow";
  gradientUsage: "none" | "subtle" | "vibrant" | "aurora";

  // Background atmosphere
  backgroundPattern: "none" | "dots" | "grid" | "waveform" | "scanlines" | "noise" | "aurora";

  // Density
  density: "compact" | "comfortable" | "spacious";

  // Animation personality
  animationStyle: "none" | "snappy" | "smooth" | "bouncy" | "slow" | "throb";
  hoverEffect: "none" | "lift" | "glow" | "scale" | "tilt";

  // Audio decorations
  showWaveforms: boolean;
  showVUMeters: boolean;
  showReactiveBg: boolean;
}

export interface Theme {
  id: string;
  name: string;
  tagline: string;
  mood: string;
  preferredMode: "dark" | "light" | "both";

  // Brand colors (triad)
  primary: ThemeColor;
  secondary: ThemeColor;
  accent: ThemeColor;

  // Neutral palette (background/text colors)
  neutrals: {
    dark: ThemeNeutrals;
    light: ThemeNeutrals;
  };

  // Gradient used for theme previews
  previewGradient: string;

  // Complete personality (shapes, fonts, animations, decorations)
  personality: ThemePersonality;

  // App shell layout — completely different React component trees
  layout: LayoutShell;

  // Legacy: optional font override (now superseded by personality.font)
  fontFamily?: "display" | "mono" | "serif";
}

// Default balanced personality used by Studio Classic and as fallback
const DEFAULT_PERSONALITY: ThemePersonality = {
  radius: "rounded",
  borderWeight: "subtle",
  font: "sans",
  headingWeight: "bold",
  letterSpacing: "normal",
  textTransform: "none",
  cardStyle: "glass",
  shadowIntensity: "medium",
  gradientUsage: "vibrant",
  backgroundPattern: "waveform",
  density: "comfortable",
  animationStyle: "smooth",
  hoverEffect: "lift",
  showWaveforms: true,
  showVUMeters: true,
  showReactiveBg: true,
};

// =================================================================
// STUDIO CLASSIC - The signature Atlas Vox look
// =================================================================
const studioClassic: Theme = {
  id: "studio-classic",
  name: "Studio Classic",
  tagline: "The signature Atlas Vox identity",
  mood: "Professional recording studio",
  preferredMode: "both",
  primary: { h: 338, s: 85, l: 52 },    // Electric pink/magenta
  secondary: { h: 47, s: 95, l: 58 },   // Golden yellow
  accent: { h: 195, s: 100, l: 45 },    // Electric blue
  neutrals: {
    dark: {
      obsidian: "220 25% 8%",
      charcoal: "220 15% 16%",
      slate: "220 12% 24%",
      silver: "220 10% 85%",
      white: "0 0% 98%",
    },
    light: {
      obsidian: "220 15% 96%",
      charcoal: "220 10% 92%",
      slate: "220 8% 85%",
      silver: "220 15% 30%",
      white: "0 0% 6%",
    },
  },
  previewGradient: "linear-gradient(135deg, hsl(338 85% 52%), hsl(47 95% 58%), hsl(195 100% 45%))",
  personality: { ...DEFAULT_PERSONALITY },
  layout: "studio",
};

// =================================================================
// CYBERPUNK NEON - Blade Runner meets Night City
// =================================================================
const cyberpunkNeon: Theme = {
  id: "cyberpunk-neon",
  name: "Cyberpunk Neon",
  tagline: "Blade Runner meets Night City",
  mood: "Futuristic dystopian nightlife",
  preferredMode: "dark",
  primary: { h: 320, s: 100, l: 55 },   // Hot magenta
  secondary: { h: 60, s: 100, l: 55 },  // Acid yellow
  accent: { h: 180, s: 100, l: 50 },    // Neon cyan
  neutrals: {
    dark: {
      obsidian: "270 40% 6%",
      charcoal: "270 30% 12%",
      slate: "270 20% 22%",
      silver: "280 15% 80%",
      white: "300 30% 98%",
    },
    light: {
      obsidian: "270 20% 96%",
      charcoal: "270 15% 92%",
      slate: "270 10% 85%",
      silver: "280 20% 30%",
      white: "300 15% 6%",
    },
  },
  previewGradient: "linear-gradient(135deg, hsl(320 100% 55%), hsl(180 100% 50%), hsl(270 80% 40%))",
  personality: {
    radius: "sharp",
    borderWeight: "neon",
    font: "mono",
    headingWeight: "black",
    letterSpacing: "wide",
    textTransform: "uppercase",
    cardStyle: "neon",
    shadowIntensity: "glow",
    gradientUsage: "vibrant",
    backgroundPattern: "scanlines",
    density: "comfortable",
    animationStyle: "snappy",
    hoverEffect: "glow",
    showWaveforms: true,
    showVUMeters: true,
    showReactiveBg: true,
  },
  layout: "command",
};

// =================================================================
// VINTAGE ANALOG - 70s recording gear
// =================================================================
const vintageAnalog: Theme = {
  id: "vintage-analog",
  name: "Vintage Analog",
  tagline: "1970s tape machines and tube amps",
  mood: "Warm nostalgic analog",
  preferredMode: "both",
  primary: { h: 18, s: 78, l: 48 },     // Burnt orange
  secondary: { h: 42, s: 88, l: 58 },   // Amber gold
  accent: { h: 355, s: 65, l: 50 },     // Rust red
  neutrals: {
    dark: {
      obsidian: "25 30% 8%",
      charcoal: "25 22% 15%",
      slate: "25 18% 24%",
      silver: "30 20% 82%",
      white: "35 40% 96%",
    },
    light: {
      obsidian: "35 30% 96%",
      charcoal: "30 20% 92%",
      slate: "25 15% 85%",
      silver: "25 18% 32%",
      white: "20 20% 8%",
    },
  },
  previewGradient: "linear-gradient(135deg, hsl(18 78% 48%), hsl(42 88% 58%), hsl(355 65% 50%))",
  fontFamily: "serif",
  personality: {
    radius: "rounded",
    borderWeight: "thin",
    font: "serif",
    headingWeight: "bold",
    letterSpacing: "normal",
    textTransform: "none",
    cardStyle: "raised",
    shadowIntensity: "dramatic",
    gradientUsage: "subtle",
    backgroundPattern: "noise",
    density: "spacious",
    animationStyle: "slow",
    hoverEffect: "lift",
    showWaveforms: true,
    showVUMeters: false,
    showReactiveBg: false,
  },
  layout: "minimal",
};

// =================================================================
// MIDNIGHT STUDIO - Late night professional session
// =================================================================
const midnightStudio: Theme = {
  id: "midnight-studio",
  name: "Midnight Studio",
  tagline: "Late night professional session",
  mood: "Focused, nocturnal, refined",
  preferredMode: "dark",
  primary: { h: 250, s: 75, l: 60 },    // Royal violet
  secondary: { h: 200, s: 80, l: 55 },  // Steel blue
  accent: { h: 170, s: 70, l: 50 },     // Teal
  neutrals: {
    dark: {
      obsidian: "230 35% 6%",
      charcoal: "230 25% 13%",
      slate: "230 20% 22%",
      silver: "220 15% 82%",
      white: "220 30% 97%",
    },
    light: {
      obsidian: "220 20% 97%",
      charcoal: "220 15% 93%",
      slate: "225 12% 86%",
      silver: "225 18% 30%",
      white: "230 20% 6%",
    },
  },
  previewGradient: "linear-gradient(135deg, hsl(250 75% 60%), hsl(200 80% 55%), hsl(170 70% 50%))",
  personality: {
    radius: "subtle",
    borderWeight: "subtle",
    font: "display",
    headingWeight: "normal",
    letterSpacing: "wide",
    textTransform: "none",
    cardStyle: "glass",
    shadowIntensity: "subtle",
    gradientUsage: "subtle",
    backgroundPattern: "none",
    density: "spacious",
    animationStyle: "smooth",
    hoverEffect: "lift",
    showWaveforms: true,
    showVUMeters: true,
    showReactiveBg: false,
  },
  layout: "bento",
};

// =================================================================
// SUNSET VINYL - Warm vinyl record shop
// =================================================================
const sunsetVinyl: Theme = {
  id: "sunset-vinyl",
  name: "Sunset Vinyl",
  tagline: "Golden hour in a record shop",
  mood: "Warm, nostalgic, inviting",
  preferredMode: "light",
  primary: { h: 8, s: 82, l: 58 },      // Coral red
  secondary: { h: 32, s: 92, l: 60 },   // Sunset orange
  accent: { h: 350, s: 75, l: 62 },     // Rose pink
  neutrals: {
    dark: {
      obsidian: "20 35% 8%",
      charcoal: "20 25% 16%",
      slate: "20 18% 26%",
      silver: "25 30% 85%",
      white: "30 50% 98%",
    },
    light: {
      obsidian: "30 30% 97%",
      charcoal: "25 22% 93%",
      slate: "20 15% 86%",
      silver: "20 25% 30%",
      white: "15 20% 8%",
    },
  },
  previewGradient: "linear-gradient(135deg, hsl(8 82% 58%), hsl(32 92% 60%), hsl(350 75% 62%))",
  personality: {
    radius: "pill",
    borderWeight: "subtle",
    font: "display",
    headingWeight: "bold",
    letterSpacing: "tight",
    textTransform: "none",
    cardStyle: "soft",
    shadowIntensity: "medium",
    gradientUsage: "vibrant",
    backgroundPattern: "aurora",
    density: "comfortable",
    animationStyle: "bouncy",
    hoverEffect: "scale",
    showWaveforms: true,
    showVUMeters: true,
    showReactiveBg: true,
  },
  layout: "bento",
};

// =================================================================
// FOREST RECORDING - Organic nature studio
// =================================================================
const forestRecording: Theme = {
  id: "forest-recording",
  name: "Forest Recording",
  tagline: "Studio in the canopy",
  mood: "Organic, calm, grounded",
  preferredMode: "both",
  primary: { h: 155, s: 65, l: 42 },    // Emerald
  secondary: { h: 85, s: 70, l: 48 },   // Moss green
  accent: { h: 28, s: 75, l: 52 },      // Copper
  neutrals: {
    dark: {
      obsidian: "150 30% 7%",
      charcoal: "150 22% 14%",
      slate: "150 18% 22%",
      silver: "140 15% 82%",
      white: "140 30% 96%",
    },
    light: {
      obsidian: "140 20% 96%",
      charcoal: "140 15% 93%",
      slate: "145 12% 85%",
      silver: "150 18% 30%",
      white: "150 15% 7%",
    },
  },
  previewGradient: "linear-gradient(135deg, hsl(155 65% 42%), hsl(85 70% 48%), hsl(28 75% 52%))",
  personality: {
    radius: "rounded",
    borderWeight: "thin",
    font: "serif",
    headingWeight: "normal",
    letterSpacing: "normal",
    textTransform: "none",
    cardStyle: "soft",
    shadowIntensity: "subtle",
    gradientUsage: "subtle",
    backgroundPattern: "noise",
    density: "spacious",
    animationStyle: "throb",
    hoverEffect: "lift",
    showWaveforms: true,
    showVUMeters: false,
    showReactiveBg: true,
  },
  layout: "minimal",
};

// =================================================================
// MONOCHROME PRO - Editorial minimalism with red accent
// =================================================================
const monochromePro: Theme = {
  id: "monochrome-pro",
  name: "Monochrome Pro",
  tagline: "Editorial minimalism",
  mood: "Refined, timeless, confident",
  preferredMode: "both",
  primary: { h: 0, s: 85, l: 55 },      // Single red accent
  secondary: { h: 0, s: 0, l: 50 },     // Pure gray
  accent: { h: 0, s: 0, l: 25 },        // Dark gray
  neutrals: {
    dark: {
      obsidian: "0 0% 4%",
      charcoal: "0 0% 11%",
      slate: "0 0% 20%",
      silver: "0 0% 85%",
      white: "0 0% 100%",
    },
    light: {
      obsidian: "0 0% 98%",
      charcoal: "0 0% 94%",
      slate: "0 0% 86%",
      silver: "0 0% 28%",
      white: "0 0% 5%",
    },
  },
  previewGradient: "linear-gradient(135deg, hsl(0 0% 10%), hsl(0 85% 55%), hsl(0 0% 90%))",
  personality: {
    radius: "sharp",
    borderWeight: "thick",
    font: "display",
    headingWeight: "black",
    letterSpacing: "tight",
    textTransform: "uppercase",
    cardStyle: "outline",
    shadowIntensity: "none",
    gradientUsage: "none",
    backgroundPattern: "grid",
    density: "compact",
    animationStyle: "none",
    hoverEffect: "none",
    showWaveforms: false,
    showVUMeters: false,
    showReactiveBg: false,
  },
  layout: "minimal",
};

// =================================================================
// TOKYO NIGHTS - Japanese nightlife neon
// =================================================================
const tokyoNights: Theme = {
  id: "tokyo-nights",
  name: "Tokyo Nights",
  tagline: "Shibuya after midnight",
  mood: "Electric, energetic, urban",
  preferredMode: "dark",
  primary: { h: 330, s: 95, l: 58 },    // Hot pink
  secondary: { h: 280, s: 85, l: 62 },  // Purple
  accent: { h: 210, s: 95, l: 58 },     // Electric blue
  neutrals: {
    dark: {
      obsidian: "250 30% 5%",
      charcoal: "250 22% 12%",
      slate: "250 18% 20%",
      silver: "260 15% 82%",
      white: "280 40% 98%",
    },
    light: {
      obsidian: "260 18% 97%",
      charcoal: "255 14% 93%",
      slate: "250 10% 86%",
      silver: "255 18% 30%",
      white: "250 20% 6%",
    },
  },
  previewGradient: "linear-gradient(135deg, hsl(330 95% 58%), hsl(280 85% 62%), hsl(210 95% 58%))",
  personality: {
    radius: "subtle",
    borderWeight: "neon",
    font: "display",
    headingWeight: "black",
    letterSpacing: "wide",
    textTransform: "uppercase",
    cardStyle: "neon",
    shadowIntensity: "glow",
    gradientUsage: "vibrant",
    backgroundPattern: "dots",
    density: "comfortable",
    animationStyle: "snappy",
    hoverEffect: "glow",
    showWaveforms: true,
    showVUMeters: true,
    showReactiveBg: true,
  },
  layout: "jarvis",
};

// =================================================================
// ARCTIC STUDIO - Scandinavian clean
// =================================================================
const arcticStudio: Theme = {
  id: "arctic-studio",
  name: "Arctic Studio",
  tagline: "Scandinavian clarity",
  mood: "Cool, clean, precise",
  preferredMode: "light",
  primary: { h: 200, s: 85, l: 50 },    // Ice blue
  secondary: { h: 180, s: 45, l: 55 },  // Glacier teal
  accent: { h: 220, s: 55, l: 55 },     // Arctic purple-blue
  neutrals: {
    dark: {
      obsidian: "210 35% 8%",
      charcoal: "210 25% 15%",
      slate: "210 18% 25%",
      silver: "205 25% 88%",
      white: "200 40% 99%",
    },
    light: {
      obsidian: "200 25% 98%",
      charcoal: "205 18% 94%",
      slate: "210 12% 87%",
      silver: "210 20% 30%",
      white: "210 20% 8%",
    },
  },
  previewGradient: "linear-gradient(135deg, hsl(200 85% 50%), hsl(180 45% 55%), hsl(220 55% 55%))",
  personality: {
    radius: "subtle",
    borderWeight: "thin",
    font: "display",
    headingWeight: "light",
    letterSpacing: "wide",
    textTransform: "none",
    cardStyle: "flat",
    shadowIntensity: "subtle",
    gradientUsage: "none",
    backgroundPattern: "none",
    density: "spacious",
    animationStyle: "smooth",
    hoverEffect: "lift",
    showWaveforms: true,
    showVUMeters: false,
    showReactiveBg: false,
  },
  layout: "minimal",
};

// =================================================================
// SYNTHWAVE - 80s retrofuturism
// =================================================================
const synthwave: Theme = {
  id: "synthwave",
  name: "Synthwave",
  tagline: "1984 cassette futurism",
  mood: "Retro-futuristic, nostalgic",
  preferredMode: "dark",
  primary: { h: 315, s: 100, l: 60 },   // Hot magenta
  secondary: { h: 185, s: 100, l: 55 }, // Cyan
  accent: { h: 265, s: 85, l: 62 },     // Purple
  neutrals: {
    dark: {
      obsidian: "260 45% 6%",
      charcoal: "260 35% 13%",
      slate: "260 25% 22%",
      silver: "280 20% 82%",
      white: "300 40% 98%",
    },
    light: {
      obsidian: "280 25% 97%",
      charcoal: "270 18% 93%",
      slate: "265 14% 86%",
      silver: "270 22% 30%",
      white: "260 20% 6%",
    },
  },
  previewGradient: "linear-gradient(135deg, hsl(315 100% 60%), hsl(265 85% 62%), hsl(185 100% 55%))",
  fontFamily: "mono",
  personality: {
    radius: "subtle",
    borderWeight: "neon",
    font: "mono",
    headingWeight: "bold",
    letterSpacing: "extra-wide",
    textTransform: "uppercase",
    cardStyle: "neon",
    shadowIntensity: "glow",
    gradientUsage: "vibrant",
    backgroundPattern: "grid",
    density: "comfortable",
    animationStyle: "throb",
    hoverEffect: "glow",
    showWaveforms: true,
    showVUMeters: true,
    showReactiveBg: true,
  },
  layout: "jarvis",
};

// =================================================================
// MATRIX - Terminal green aesthetic
// =================================================================
const matrix: Theme = {
  id: "matrix",
  name: "Matrix",
  tagline: "Welcome to the real world",
  mood: "Cryptic, technical, mysterious",
  preferredMode: "dark",
  primary: { h: 130, s: 100, l: 45 },   // Matrix green
  secondary: { h: 150, s: 85, l: 55 },  // Bright green
  accent: { h: 90, s: 75, l: 50 },      // Lime
  neutrals: {
    dark: {
      obsidian: "130 15% 4%",
      charcoal: "130 12% 10%",
      slate: "130 10% 18%",
      silver: "130 15% 78%",
      white: "130 40% 95%",
    },
    light: {
      obsidian: "130 15% 97%",
      charcoal: "130 10% 94%",
      slate: "130 8% 87%",
      silver: "130 15% 28%",
      white: "130 20% 5%",
    },
  },
  previewGradient: "linear-gradient(135deg, hsl(130 100% 45%), hsl(150 85% 55%), hsl(130 15% 10%))",
  fontFamily: "mono",
  personality: {
    radius: "sharp",
    borderWeight: "thin",
    font: "mono",
    headingWeight: "normal",
    letterSpacing: "wide",
    textTransform: "uppercase",
    cardStyle: "outline",
    shadowIntensity: "glow",
    gradientUsage: "none",
    backgroundPattern: "scanlines",
    density: "compact",
    animationStyle: "snappy",
    hoverEffect: "glow",
    showWaveforms: true,
    showVUMeters: true,
    showReactiveBg: false,
  },
  layout: "command",
};

// =================================================================
// LAVENDER DREAMS - Soft dreamy pastels
// =================================================================
const lavenderDreams: Theme = {
  id: "lavender-dreams",
  name: "Lavender Dreams",
  tagline: "Soft pastel daydream",
  mood: "Gentle, romantic, ethereal",
  preferredMode: "light",
  primary: { h: 270, s: 65, l: 68 },    // Lavender
  secondary: { h: 330, s: 70, l: 72 },  // Pink blush
  accent: { h: 160, s: 55, l: 62 },     // Mint
  neutrals: {
    dark: {
      obsidian: "280 25% 10%",
      charcoal: "280 20% 18%",
      slate: "280 15% 28%",
      silver: "280 20% 88%",
      white: "290 50% 99%",
    },
    light: {
      obsidian: "290 30% 98%",
      charcoal: "285 18% 94%",
      slate: "280 12% 88%",
      silver: "280 20% 30%",
      white: "275 15% 10%",
    },
  },
  previewGradient: "linear-gradient(135deg, hsl(270 65% 68%), hsl(330 70% 72%), hsl(160 55% 62%))",
  personality: {
    radius: "pill",
    borderWeight: "none",
    font: "display",
    headingWeight: "light",
    letterSpacing: "wide",
    textTransform: "none",
    cardStyle: "soft",
    shadowIntensity: "subtle",
    gradientUsage: "aurora",
    backgroundPattern: "aurora",
    density: "spacious",
    animationStyle: "throb",
    hoverEffect: "scale",
    showWaveforms: false,
    showVUMeters: false,
    showReactiveBg: true,
  },
  layout: "bento",
};

// =================================================================
// JARVIS HOLOGRAPHIC - Iron Man HUD interface
// =================================================================
const jarvisHolographic: Theme = {
  id: "jarvis",
  name: "J.A.R.V.I.S.",
  tagline: "Just A Rather Very Intelligent System",
  mood: "Holographic AI assistant",
  preferredMode: "dark",
  primary: { h: 195, s: 100, l: 55 },   // Iron Man HUD blue
  secondary: { h: 30, s: 100, l: 58 },  // Arc reactor gold
  accent: { h: 200, s: 100, l: 70 },    // Bright hologram blue
  neutrals: {
    dark: {
      obsidian: "210 60% 4%",
      charcoal: "210 50% 9%",
      slate: "210 40% 18%",
      silver: "200 60% 80%",
      white: "200 80% 97%",
    },
    light: {
      obsidian: "200 40% 97%",
      charcoal: "205 30% 94%",
      slate: "210 22% 87%",
      silver: "205 35% 28%",
      white: "210 40% 6%",
    },
  },
  previewGradient: "linear-gradient(135deg, hsl(195 100% 55%), hsl(200 100% 70%), hsl(30 100% 58%))",
  personality: {
    radius: "subtle",
    borderWeight: "neon",
    font: "display",
    headingWeight: "light",
    letterSpacing: "extra-wide",
    textTransform: "uppercase",
    cardStyle: "outline",
    shadowIntensity: "glow",
    gradientUsage: "vibrant",
    backgroundPattern: "grid",
    density: "comfortable",
    animationStyle: "smooth",
    hoverEffect: "glow",
    showWaveforms: true,
    showVUMeters: true,
    showReactiveBg: true,
  },
  layout: "jarvis",
};

// =================================================================
// ATLAS TACTICAL - NORAD mission command
// =================================================================
const atlasTactical: Theme = {
  id: "atlas",
  name: "ATLAS Tactical",
  tagline: "Mission command operations center",
  mood: "Military-grade tactical",
  preferredMode: "dark",
  primary: { h: 15, s: 90, l: 55 },     // Tactical amber-orange
  secondary: { h: 100, s: 70, l: 50 },  // Olive drab
  accent: { h: 0, s: 85, l: 55 },       // Alert red
  neutrals: {
    dark: {
      obsidian: "100 15% 5%",
      charcoal: "100 12% 11%",
      slate: "100 10% 20%",
      silver: "80 15% 78%",
      white: "60 30% 96%",
    },
    light: {
      obsidian: "80 12% 96%",
      charcoal: "90 10% 93%",
      slate: "95 8% 86%",
      silver: "90 15% 30%",
      white: "100 12% 6%",
    },
  },
  previewGradient: "linear-gradient(135deg, hsl(15 90% 55%), hsl(100 70% 50%), hsl(0 85% 55%))",
  personality: {
    radius: "sharp",
    borderWeight: "thin",
    font: "mono",
    headingWeight: "bold",
    letterSpacing: "wide",
    textTransform: "uppercase",
    cardStyle: "outline",
    shadowIntensity: "subtle",
    gradientUsage: "none",
    backgroundPattern: "grid",
    density: "compact",
    animationStyle: "snappy",
    hoverEffect: "glow",
    showWaveforms: true,
    showVUMeters: true,
    showReactiveBg: false,
  },
  layout: "atlas",
};

// =================================================================
// LINEAR MINIMAL - Modern productivity app
// =================================================================
const linearMinimal: Theme = {
  id: "linear-minimal",
  name: "Linear Minimal",
  tagline: "Modern productivity clarity",
  mood: "Focused, clean, purposeful",
  preferredMode: "both",
  primary: { h: 240, s: 65, l: 58 },    // Indigo
  secondary: { h: 262, s: 75, l: 62 },  // Purple
  accent: { h: 180, s: 60, l: 50 },     // Teal
  neutrals: {
    dark: {
      obsidian: "220 15% 6%",
      charcoal: "220 12% 10%",
      slate: "220 10% 18%",
      silver: "220 8% 80%",
      white: "220 20% 98%",
    },
    light: {
      obsidian: "220 12% 98%",
      charcoal: "220 10% 95%",
      slate: "220 8% 88%",
      silver: "220 10% 30%",
      white: "220 12% 6%",
    },
  },
  previewGradient: "linear-gradient(135deg, hsl(240 65% 58%), hsl(262 75% 62%), hsl(180 60% 50%))",
  personality: {
    radius: "subtle",
    borderWeight: "thin",
    font: "display",
    headingWeight: "bold",
    letterSpacing: "tight",
    textTransform: "none",
    cardStyle: "flat",
    shadowIntensity: "subtle",
    gradientUsage: "none",
    backgroundPattern: "none",
    density: "spacious",
    animationStyle: "snappy",
    hoverEffect: "none",
    showWaveforms: false,
    showVUMeters: false,
    showReactiveBg: false,
  },
  layout: "minimal",
};

// =================================================================
// THEME LIBRARY EXPORT
// =================================================================
export const THEMES: Theme[] = [
  studioClassic,
  jarvisHolographic,
  atlasTactical,
  linearMinimal,
  cyberpunkNeon,
  vintageAnalog,
  midnightStudio,
  sunsetVinyl,
  forestRecording,
  monochromePro,
  tokyoNights,
  arcticStudio,
  synthwave,
  matrix,
  lavenderDreams,
];

export const THEME_BY_ID: Record<string, Theme> = THEMES.reduce(
  (acc, theme) => {
    acc[theme.id] = theme;
    return acc;
  },
  {} as Record<string, Theme>
);

export const DEFAULT_THEME_ID = "studio-classic";

/**
 * Apply a theme to the document root by setting CSS variables.
 * This is called by the design store whenever a theme is selected.
 */
export function applyThemeToDOM(theme: Theme): void {
  const root = document.documentElement;
  const isDark = root.classList.contains("dark");
  const neutrals = isDark ? theme.neutrals.dark : theme.neutrals.light;

  // === Brand colors — write both split (H/S/L) and combined HSL triplet ===
  // Split form enables scale variables to override lightness
  root.style.setProperty("--studio-primary-h", String(theme.primary.h));
  root.style.setProperty("--studio-primary-s", `${theme.primary.s}%`);
  root.style.setProperty("--studio-primary-l", `${theme.primary.l}%`);
  root.style.setProperty(
    "--studio-primary",
    `${theme.primary.h} ${theme.primary.s}% ${theme.primary.l}%`
  );

  root.style.setProperty("--studio-secondary-h", String(theme.secondary.h));
  root.style.setProperty("--studio-secondary-s", `${theme.secondary.s}%`);
  root.style.setProperty("--studio-secondary-l", `${theme.secondary.l}%`);
  root.style.setProperty(
    "--studio-secondary",
    `${theme.secondary.h} ${theme.secondary.s}% ${theme.secondary.l}%`
  );

  root.style.setProperty("--studio-accent-h", String(theme.accent.h));
  root.style.setProperty("--studio-accent-s", `${theme.accent.s}%`);
  root.style.setProperty("--studio-accent-l", `${theme.accent.l}%`);
  root.style.setProperty(
    "--studio-accent",
    `${theme.accent.h} ${theme.accent.s}% ${theme.accent.l}%`
  );

  // === Studio neutrals ===
  root.style.setProperty("--studio-obsidian", neutrals.obsidian);
  root.style.setProperty("--studio-charcoal", neutrals.charcoal);
  root.style.setProperty("--studio-slate", neutrals.slate);
  root.style.setProperty("--studio-silver", neutrals.silver);
  root.style.setProperty("--studio-white", neutrals.white);

  // === Legacy accent scale compatibility (for older components) ===
  root.style.setProperty("--accent-h", String(theme.primary.h));
  root.style.setProperty("--accent-s", `${theme.primary.s}%`);

  // === Apply personality (drives layout/shape/font/animation across the app) ===
  applyPersonalityToDOM(theme.personality);

  // === Theme font (overridden by personality.font, kept for back-compat) ===
  if (theme.personality.font === "serif") {
    root.style.setProperty(
      "--font-display",
      '"Playfair Display", "Georgia", "Times New Roman", serif'
    );
    root.style.setProperty(
      "--font-body",
      '"Lora", "Georgia", serif'
    );
  } else if (theme.personality.font === "mono") {
    root.style.setProperty(
      "--font-display",
      '"JetBrains Mono", "Fira Code", "SF Mono", monospace'
    );
    root.style.setProperty(
      "--font-body",
      '"JetBrains Mono", "Fira Code", "SF Mono", monospace'
    );
  } else {
    root.style.setProperty(
      "--font-display",
      '"Inter Display", "SF Pro Display", -apple-system, BlinkMacSystemFont, system-ui, sans-serif'
    );
    root.style.setProperty(
      "--font-body",
      '"Inter", "SF Pro Text", -apple-system, BlinkMacSystemFont, system-ui, sans-serif'
    );
  }

  // Store theme ID + personality keys on data attributes for CSS hooks
  root.dataset.theme = theme.id;
  root.dataset.radius = theme.personality.radius;
  root.dataset.cardStyle = theme.personality.cardStyle;
  root.dataset.bgPattern = theme.personality.backgroundPattern;
  root.dataset.animation = theme.personality.animationStyle;
  root.dataset.density = theme.personality.density;
  root.dataset.shadow = theme.personality.shadowIntensity;
  root.dataset.hoverEffect = theme.personality.hoverEffect;
}

/**
 * Write personality values as CSS variables that components consume.
 * These drive layout, spacing, shape, animation, and decoration across the entire app.
 */
function applyPersonalityToDOM(p: ThemePersonality): void {
  const root = document.documentElement;

  // === Radius scale ===
  const radiusMap = {
    sharp: { sm: "0px", md: "0px", lg: "0px", xl: "0px", full: "0px" },
    subtle: { sm: "4px", md: "6px", lg: "8px", xl: "12px", full: "9999px" },
    rounded: { sm: "8px", md: "12px", lg: "16px", xl: "24px", full: "9999px" },
    pill: { sm: "12px", md: "20px", lg: "28px", xl: "36px", full: "9999px" },
  }[p.radius];
  root.style.setProperty("--radius-sm", radiusMap.sm);
  root.style.setProperty("--radius", radiusMap.lg);
  root.style.setProperty("--radius-lg", radiusMap.xl);

  // === Border weight ===
  const borderMap = {
    none: "0px",
    subtle: "1px",
    thin: "1px",
    thick: "2px",
    neon: "1px",
  };
  root.style.setProperty("--theme-border-width", borderMap[p.borderWeight]);

  // === Heading font weight ===
  const weightMap = { light: "300", normal: "500", bold: "700", black: "900" };
  root.style.setProperty("--theme-heading-weight", weightMap[p.headingWeight]);

  // === Letter spacing ===
  const spacingMap = {
    tight: "-0.02em",
    normal: "0em",
    wide: "0.05em",
    "extra-wide": "0.12em",
  };
  root.style.setProperty("--theme-letter-spacing", spacingMap[p.letterSpacing]);

  // === Text transform ===
  root.style.setProperty(
    "--theme-text-transform",
    p.textTransform === "uppercase" ? "uppercase" : "none"
  );

  // === Density (spacing multiplier) ===
  const densityMap = { compact: "0.75", comfortable: "1", spacious: "1.4" };
  root.style.setProperty("--density", densityMap[p.density]);

  // === Shadow intensity ===
  const shadowMap = {
    none: "none",
    subtle: "0 2px 8px hsl(0 0% 0% / 0.08)",
    medium: "0 8px 24px -8px hsl(var(--studio-primary) / 0.25)",
    dramatic: "0 20px 50px -12px hsl(var(--studio-primary) / 0.4)",
    glow: "0 0 30px hsl(var(--studio-primary) / 0.5), 0 0 60px hsl(var(--studio-primary) / 0.3)",
  };
  root.style.setProperty("--shadow-studio", shadowMap[p.shadowIntensity]);

  // === Animation duration & easing ===
  const animMap = {
    none: { dur: "0ms", ease: "linear" },
    snappy: { dur: "120ms", ease: "cubic-bezier(0.4, 0, 0.2, 1)" },
    smooth: { dur: "300ms", ease: "cubic-bezier(0.23, 1, 0.32, 1)" },
    bouncy: { dur: "500ms", ease: "cubic-bezier(0.34, 1.56, 0.64, 1)" },
    slow: { dur: "600ms", ease: "cubic-bezier(0.25, 0.1, 0.25, 1)" },
    throb: { dur: "1200ms", ease: "cubic-bezier(0.4, 0, 0.6, 1)" },
  };
  root.style.setProperty("--theme-anim-duration", animMap[p.animationStyle].dur);
  root.style.setProperty("--theme-anim-ease", animMap[p.animationStyle].ease);

  // === Show/hide audio decorations ===
  root.style.setProperty("--show-waveforms", p.showWaveforms ? "block" : "none");
  root.style.setProperty("--show-vu-meters", p.showVUMeters ? "block" : "none");
  root.style.setProperty("--show-reactive-bg", p.showReactiveBg ? "block" : "none");
}
