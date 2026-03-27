interface ProviderLogoProps {
  name: string;
  size?: number;
  className?: string;
}

export default function ProviderLogo({
  name,
  size = 32,
  className = "",
}: ProviderLogoProps) {
  const logo = LOGOS[name] ?? LOGOS._default;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label={`${name} logo`}
    >
      {logo}
    </svg>
  );
}

/* ---------- per-provider SVG content ---------- */

const LOGOS: Record<string, React.ReactNode> = {
  /* Kokoro - Heart (kokoro = heart in Japanese) */
  kokoro: (
    <>
      <circle cx="16" cy="16" r="15" fill="#FDE8E8" />
      <path
        d="M16 26C16 26 6 20 6 13.5C6 10.46 8.46 8 11.5 8C13.24 8 14.79 8.81 16 10.09C17.21 8.81 18.76 8 20.5 8C23.54 8 26 10.46 26 13.5C26 20 16 26 16 26Z"
        fill="#E53E3E"
      />
    </>
  ),

  /* Coqui XTTS - Frog silhouette */
  coqui_xtts: (
    <>
      <circle cx="16" cy="16" r="15" fill="#E6FFED" />
      <ellipse cx="11" cy="11" rx="3.5" ry="3.5" fill="#38A169" />
      <ellipse cx="21" cy="11" rx="3.5" ry="3.5" fill="#38A169" />
      <circle cx="11" cy="10.5" r="1.5" fill="white" />
      <circle cx="21" cy="10.5" r="1.5" fill="white" />
      <circle cx="11.5" cy="10.5" r="0.8" fill="#1A202C" />
      <circle cx="21.5" cy="10.5" r="0.8" fill="#1A202C" />
      <path
        d="M9 18C9 18 12 22 16 22C20 22 23 18 23 18"
        stroke="#38A169"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <ellipse cx="16" cy="17" rx="7" ry="5" fill="#48BB78" opacity="0.5" />
    </>
  ),

  /* Piper - Pipe/flute icon */
  piper: (
    <>
      <circle cx="16" cy="16" r="15" fill="#FEFCBF" />
      <rect x="6" y="13" width="18" height="6" rx="3" fill="#C05621" />
      <circle cx="10" cy="16" r="1.2" fill="#FEFCBF" />
      <circle cx="14" cy="16" r="1.2" fill="#FEFCBF" />
      <circle cx="18" cy="16" r="1.2" fill="#FEFCBF" />
      <path
        d="M24 14.5C24 14.5 27 13 27 16C27 19 24 17.5 24 17.5"
        fill="#C05621"
      />
    </>
  ),

  /* ElevenLabs - "XI" in a rounded square */
  elevenlabs: (
    <>
      <rect x="2" y="2" width="28" height="28" rx="7" fill="#1A1A2E" />
      <text
        x="16"
        y="22"
        textAnchor="middle"
        fontFamily="Arial, sans-serif"
        fontWeight="bold"
        fontSize="16"
        fill="white"
      >
        XI
      </text>
    </>
  ),

  /* Azure Speech - Azure cloud icon */
  azure_speech: (
    <>
      <circle cx="16" cy="16" r="15" fill="#E1F0FF" />
      <path
        d="M10 22H23C25.2 22 27 20.2 27 18C27 15.8 25.2 14 23 14H22.7C22.4 11.2 20 9 17 9C14.5 9 12.4 10.6 11.5 12.8C9 13.2 7 15.4 7 18C7 20.2 8.8 22 11 22H10Z"
        fill="#0078D4"
      />
      <path
        d="M14 16L16.5 19L20 14"
        stroke="white"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </>
  ),

  /* StyleTTS2 - Stylized "S2" with sound wave */
  styletts2: (
    <>
      <circle cx="16" cy="16" r="15" fill="#F3E8FF" />
      <text
        x="13"
        y="22"
        fontFamily="Arial, sans-serif"
        fontWeight="bold"
        fontSize="15"
        fill="#7C3AED"
      >
        S2
      </text>
      <path
        d="M26 11C27.5 13 27.5 19 26 21"
        stroke="#7C3AED"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M28.5 9C30.5 12 30.5 20 28.5 23"
        stroke="#7C3AED"
        strokeWidth="1.5"
        strokeLinecap="round"
        opacity="0.5"
      />
    </>
  ),

  /* CosyVoice - Cozy speech bubble with warmth */
  cosyvoice: (
    <>
      <circle cx="16" cy="16" r="15" fill="#FFF5E6" />
      <path
        d="M8 12C8 9.79 9.79 8 12 8H20C22.21 8 24 9.79 24 12V17C24 19.21 22.21 21 20 21H14L10 25V21H12C9.79 21 8 19.21 8 17V12Z"
        fill="#ED8936"
      />
      <path
        d="M13 13.5C13 13.5 14.5 12 16 14C17.5 12 19 13.5 19 13.5C19 15.5 16 17.5 16 17.5C16 17.5 13 15.5 13 13.5Z"
        fill="white"
        opacity="0.9"
      />
    </>
  ),

  /* Dia - Dialogue split bubble (two speakers) */
  dia: (
    <>
      <circle cx="16" cy="16" r="15" fill="#E6FFFA" />
      <path
        d="M6 10C6 8.34 7.34 7 9 7H16C17.66 7 19 8.34 19 10V14C19 15.66 17.66 17 16 17H12L9 20V17H9C7.34 17 6 15.66 6 14V10Z"
        fill="#319795"
      />
      <path
        d="M13 14C13 12.34 14.34 11 16 11H23C24.66 11 26 12.34 26 14V18C26 19.66 24.66 21 23 21H23V24L20 21H16C14.34 21 13 19.66 13 18V14Z"
        fill="#4FD1C5"
      />
    </>
  ),

  /* Dia2 - Dialogue bubble with streaming lines */
  dia2: (
    <>
      <circle cx="16" cy="16" r="15" fill="#E6FFFA" />
      <path
        d="M6 10C6 8.34 7.34 7 9 7H16C17.66 7 19 8.34 19 10V14C19 15.66 17.66 17 16 17H12L9 20V17H9C7.34 17 6 15.66 6 14V10Z"
        fill="#2C7A7B"
      />
      <path
        d="M13 14C13 12.34 14.34 11 16 11H23C24.66 11 26 12.34 26 14V18C26 19.66 24.66 21 23 21H23V24L20 21H16C14.34 21 13 19.66 13 18V14Z"
        fill="#38B2AC"
      />
      {/* streaming lines */}
      <line
        x1="8.5"
        y1="11"
        x2="16.5"
        y2="11"
        stroke="white"
        strokeWidth="1.2"
        strokeLinecap="round"
        opacity="0.8"
      />
      <line
        x1="8.5"
        y1="13.5"
        x2="14"
        y2="13.5"
        stroke="white"
        strokeWidth="1.2"
        strokeLinecap="round"
        opacity="0.6"
      />
      <line
        x1="15.5"
        y1="15"
        x2="23.5"
        y2="15"
        stroke="white"
        strokeWidth="1.2"
        strokeLinecap="round"
        opacity="0.8"
      />
      <line
        x1="15.5"
        y1="17.5"
        x2="21"
        y2="17.5"
        stroke="white"
        strokeWidth="1.2"
        strokeLinecap="round"
        opacity="0.6"
      />
    </>
  ),

  /* Fish Speech - Fish icon, blue/teal */
  fish_speech: (
    <>
      <circle cx="16" cy="16" r="15" fill="#E6FFFA" />
      <ellipse cx="14" cy="16" rx="9" ry="5.5" fill="#0D9488" />
      <polygon points="24,16 28,12 28,20" fill="#0D9488" />
      <circle cx="10" cy="14.5" r="1.2" fill="white" />
      <circle cx="10.4" cy="14.5" r="0.6" fill="#1A202C" />
      <path
        d="M13 11C14.5 9.5 17 9.5 18.5 11"
        stroke="#0D9488"
        strokeWidth="1.2"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M13 21C14.5 22.5 17 22.5 18.5 21"
        stroke="#0D9488"
        strokeWidth="1.2"
        strokeLinecap="round"
        fill="none"
      />
    </>
  ),

  /* Chatterbox - Chat bubble with sound waves, orange */
  chatterbox: (
    <>
      <circle cx="16" cy="16" r="15" fill="#FFF7ED" />
      <path
        d="M7 10C7 8.34 8.34 7 10 7H22C23.66 7 25 8.34 25 10V18C25 19.66 23.66 21 22 21H14L10 25V21H10C8.34 21 7 19.66 7 18V10Z"
        fill="#EA580C"
      />
      <path
        d="M12 12.5H20"
        stroke="white"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M12 15.5H18"
        stroke="white"
        strokeWidth="1.5"
        strokeLinecap="round"
        opacity="0.7"
      />
      <path
        d="M27 12C28.2 13.5 28.2 17.5 27 19"
        stroke="#EA580C"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M29 10.5C30.5 13 30.5 18 29 20.5"
        stroke="#EA580C"
        strokeWidth="1.5"
        strokeLinecap="round"
        opacity="0.5"
      />
    </>
  ),

  /* F5-TTS - "F5" text in a rounded square, purple */
  f5_tts: (
    <>
      <rect x="2" y="2" width="28" height="28" rx="7" fill="#7C3AED" />
      <text
        x="16"
        y="22"
        textAnchor="middle"
        fontFamily="Arial, sans-serif"
        fontWeight="bold"
        fontSize="16"
        fill="white"
      >
        F5
      </text>
    </>
  ),

  /* OpenVoice v2 - Open microphone icon, green */
  openvoice_v2: (
    <>
      <circle cx="16" cy="16" r="15" fill="#ECFDF5" />
      <rect x="12" y="6" width="8" height="12" rx="4" fill="#16A34A" />
      <path
        d="M9 15C9 19.42 12.13 23 16 23C19.87 23 23 19.42 23 15"
        stroke="#16A34A"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
      />
      <line
        x1="16"
        y1="23"
        x2="16"
        y2="27"
        stroke="#16A34A"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <line
        x1="12"
        y1="27"
        x2="20"
        y2="27"
        stroke="#16A34A"
        strokeWidth="2"
        strokeLinecap="round"
      />
      {/* "open" indicator arcs */}
      <path
        d="M7 12C6 14 6 18 7 20"
        stroke="#16A34A"
        strokeWidth="1.2"
        strokeLinecap="round"
        opacity="0.5"
      />
      <path
        d="M25 12C26 14 26 18 25 20"
        stroke="#16A34A"
        strokeWidth="1.2"
        strokeLinecap="round"
        opacity="0.5"
      />
    </>
  ),

  /* Orpheus - Lyre/harp icon, gold/amber */
  orpheus: (
    <>
      <circle cx="16" cy="16" r="15" fill="#FFFBEB" />
      <path
        d="M10 8C10 8 8 14 8 20C8 22.2 9.8 24 12 24H20C22.2 24 24 22.2 24 20C24 14 22 8 22 8"
        stroke="#D97706"
        strokeWidth="2.5"
        strokeLinecap="round"
        fill="none"
      />
      <line
        x1="10"
        y1="8"
        x2="22"
        y2="8"
        stroke="#D97706"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <line
        x1="13"
        y1="10"
        x2="13"
        y2="22"
        stroke="#D97706"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <line
        x1="16"
        y1="9"
        x2="16"
        y2="23"
        stroke="#D97706"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <line
        x1="19"
        y1="10"
        x2="19"
        y2="22"
        stroke="#D97706"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </>
  ),

  /* Piper Training - Pipe with a gear, brown/copper */
  piper_training: (
    <>
      <circle cx="16" cy="16" r="15" fill="#FEF3C7" />
      <rect x="5" y="13" width="14" height="6" rx="3" fill="#92400E" />
      <circle cx="9" cy="16" r="1" fill="#FEF3C7" />
      <circle cx="13" cy="16" r="1" fill="#FEF3C7" />
      <path
        d="M19 14.5C19 14.5 22 13 22 16C22 19 19 17.5 19 17.5"
        fill="#92400E"
      />
      {/* gear */}
      <circle cx="25" cy="22" r="4" fill="#B45309" />
      <circle cx="25" cy="22" r="1.8" fill="#FEF3C7" />
      <rect x="24.2" y="17" width="1.6" height="2.5" rx="0.5" fill="#B45309" />
      <rect x="24.2" y="24.5" width="1.6" height="2.5" rx="0.5" fill="#B45309" />
      <rect x="20" y="21.2" width="2.5" height="1.6" rx="0.5" fill="#B45309" />
      <rect x="27.5" y="21.2" width="2.5" height="1.6" rx="0.5" fill="#B45309" />
    </>
  ),

  /* Default fallback - Speaker/microphone icon */
  _default: (
    <>
      <circle cx="16" cy="16" r="15" fill="#EDF2F7" />
      <rect x="12" y="8" width="8" height="11" rx="4" fill="#A0AEC0" />
      <path
        d="M10 16C10 19.31 12.69 22 16 22C19.31 22 22 19.31 22 16"
        stroke="#A0AEC0"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <line
        x1="16"
        y1="22"
        x2="16"
        y2="26"
        stroke="#A0AEC0"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <line
        x1="12"
        y1="26"
        x2="20"
        y2="26"
        stroke="#A0AEC0"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </>
  ),
};
