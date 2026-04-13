import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: {
          primary: "#0A0B0E",
          secondary: "#111318",
          surface: "#1A1D24",
          elevated: "#22262F",
        },
        text: {
          primary: "#F0F1F3",
          secondary: "#9BA1AD",
          muted: "#5D6370",
        },
        accent: {
          primary: "#3B82F6",
          hover: "#2563EB",
          muted: "#1E3A5F",
        },
        regime: {
          normal: "#22C55E",
          "normal-bg": "#0A2E1A",
          cautious: "#F59E0B",
          "cautious-bg": "#2E2308",
          turbulent: "#EF4444",
          "turbulent-bg": "#2E0A0A",
        },
        gain: "#22C55E",
        loss: "#EF4444",
        border: {
          DEFAULT: "#2A2E37",
          hover: "#3A3F4A",
          focus: "#3B82F6",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
