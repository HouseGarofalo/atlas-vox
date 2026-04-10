import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Primary (Electric Pink/Magenta) Scale
        primary: {
          50: "var(--accent-50)",
          100: "var(--accent-100)",
          200: "var(--accent-200)",
          300: "var(--accent-300)",
          400: "var(--accent-400)",
          500: "var(--accent-500)",
          600: "var(--accent-600)",
          700: "var(--accent-700)",
          800: "var(--accent-800)",
          900: "var(--accent-900)",
          950: "var(--accent-950)",
        },
        // Secondary (Golden Yellow) Scale
        secondary: {
          50: "var(--secondary-50)",
          100: "var(--secondary-100)",
          200: "var(--secondary-200)",
          300: "var(--secondary-300)",
          400: "var(--secondary-400)",
          500: "var(--secondary-500)",
          600: "var(--secondary-600)",
          700: "var(--secondary-700)",
          800: "var(--secondary-800)",
          900: "var(--secondary-900)",
        },
        // Electric Blue Scale
        electric: {
          50: "var(--electric-50)",
          100: "var(--electric-100)",
          200: "var(--electric-200)",
          300: "var(--electric-300)",
          400: "var(--electric-400)",
          500: "var(--electric-500)",
          600: "var(--electric-600)",
          700: "var(--electric-700)",
          800: "var(--electric-800)",
          900: "var(--electric-900)",
        },
        // Studio Equipment Colors
        studio: {
          obsidian: "hsl(var(--studio-obsidian))",
          charcoal: "hsl(var(--studio-charcoal))",
          slate: "hsl(var(--studio-slate))",
          silver: "hsl(var(--studio-silver))",
          white: "hsl(var(--studio-white))",
        },
        // LED Status Colors
        led: {
          green: "var(--color-led-green)",
          yellow: "var(--color-led-yellow)",
          red: "var(--color-led-red)",
        },
      },
      borderRadius: {
        DEFAULT: "var(--radius)",
        sm: "var(--radius-sm)",
        lg: "var(--radius-lg)",
        full: "var(--radius-full)",
      },
      fontFamily: {
        display: ["var(--font-display)"],
        sans: ["var(--font-body)"],
        mono: ["var(--font-mono)"],
      },
      fontSize: {
        base: "var(--font-size-base)",
      },
      spacing: {
        sidebar: "var(--sidebar-width)",
      },
      boxShadow: {
        studio: "var(--shadow-studio)",
        console: "var(--shadow-console)",
        knob: "var(--shadow-knob)",
      },
      animation: {
        "pulse-slow": "pulse-slow 4s ease-in-out infinite",
        "bounce-random": "bounce-random 0.8s ease-in-out infinite",
        "led-pulse": "led-pulse 1.5s ease-in-out infinite",
        "spectrum": "spectrum-shift 3s ease infinite",
        "waveform-drift": "waveform-drift 20s ease-in-out infinite",
        "fade-in-up": "fadeInUp 300ms cubic-bezier(0.23, 1, 0.32, 1)",
      },
      backdropBlur: {
        xs: "2px",
      },
      backgroundImage: {
        "gradient-studio": "linear-gradient(135deg, hsl(var(--studio-primary)), hsl(var(--studio-accent)))",
        "gradient-gold": "linear-gradient(135deg, hsl(var(--studio-secondary)), hsl(var(--studio-primary)))",
        "gradient-console": "linear-gradient(145deg, hsl(var(--studio-obsidian)), hsl(var(--studio-charcoal)))",
      },
    },
  },
  plugins: [],
} satisfies Config;
