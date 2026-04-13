/**
 * @midas/tokens — Design tokens for Midas platform
 *
 * Dark mode first, financial-grade palette.
 * Consumed by apps/web (Tailwind) and apps/mobile (NativeWind/Tamagui).
 */

export const colors = {
  // Background
  bg: {
    primary: "#0A0B0E",
    secondary: "#111318",
    surface: "#1A1D24",
    elevated: "#22262F",
  },

  // Text
  text: {
    primary: "#F0F1F3",
    secondary: "#9BA1AD",
    muted: "#5D6370",
    inverse: "#0A0B0E",
  },

  // Accent
  accent: {
    primary: "#3B82F6",
    hover: "#2563EB",
    muted: "#1E3A5F",
  },

  // Regime status
  regime: {
    normal: "#22C55E",
    normalBg: "#0A2E1A",
    cautious: "#F59E0B",
    cautiousBg: "#2E2308",
    turbulent: "#EF4444",
    turbulentBg: "#2E0A0A",
  },

  // Gains / losses
  gain: "#22C55E",
  loss: "#EF4444",
  neutral: "#9BA1AD",

  // Borders
  border: {
    default: "#2A2E37",
    hover: "#3A3F4A",
    focus: "#3B82F6",
  },

  // Sleeve colors (consistent across all charts)
  sleeves: {
    equity_sector: "#3B82F6",
    precious_metals: "#F59E0B",
    govt_bonds_short: "#6366F1",
    govt_bonds_intermediate: "#8B5CF6",
    govt_bonds_long: "#A78BFA",
    ig_corp_bonds: "#06B6D4",
    reits: "#EC4899",
    commodities: "#F97316",
    dividend_etfs: "#14B8A6",
    em_equity: "#EF4444",
    cash: "#9BA1AD",
  },
} as const;

export const typography = {
  fontFamily: {
    sans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    mono: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
  },
  fontSize: {
    xs: "0.75rem",
    sm: "0.875rem",
    base: "1rem",
    lg: "1.125rem",
    xl: "1.25rem",
    "2xl": "1.5rem",
    "3xl": "1.875rem",
    "4xl": "2.25rem",
  },
  fontWeight: {
    normal: "400",
    medium: "500",
    semibold: "600",
    bold: "700",
  },
} as const;

export const spacing = {
  px: "1px",
  0: "0",
  0.5: "0.125rem",
  1: "0.25rem",
  2: "0.5rem",
  3: "0.75rem",
  4: "1rem",
  5: "1.25rem",
  6: "1.5rem",
  8: "2rem",
  10: "2.5rem",
  12: "3rem",
  16: "4rem",
  20: "5rem",
} as const;

export const borderRadius = {
  sm: "0.25rem",
  md: "0.375rem",
  lg: "0.5rem",
  xl: "0.75rem",
  full: "9999px",
} as const;
