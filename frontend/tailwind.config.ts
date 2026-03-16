import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        warroom: {
          bg: "var(--warroom-bg)",
          surface: "var(--warroom-surface)",
          surface2: "var(--warroom-surface-2)",
          border: "var(--warroom-border)",
          borderGlow: "var(--warroom-border-glow)",
          accent: "var(--warroom-accent)",
          accentSoft: "var(--warroom-accent-soft)",
          accentGlow: "var(--warroom-accent-glow)",
          text: "var(--warroom-text)",
          muted: "var(--warroom-muted)",
          success: "var(--warroom-success)",
          danger: "var(--warroom-danger)",
          warning: "var(--warroom-warning)",
        },
      },
      backgroundImage: {
        "warroom-gradient": "linear-gradient(135deg, var(--warroom-gradient-start), var(--warroom-gradient-end))",
        "warroom-gradient-subtle": "linear-gradient(135deg, var(--warroom-surface-2) 0%, var(--warroom-surface) 100%)",
      },
      boxShadow: {
        glow: "0 0 20px var(--warroom-accent-glow)",
        "glow-sm": "0 0 10px var(--warroom-accent-glow)",
      },
      keyframes: {
        "slide-in-right": {
          "0%": { transform: "translateX(100%)" },
          "100%": { transform: "translateX(0)" },
        },
        shrink: {
          "0%": { width: "100%" },
          "100%": { width: "0%" },
        },
      },
      animation: {
        "slide-in-right": "slide-in-right 0.2s ease-out",
        shrink: "shrink 2.5s linear forwards",
      },
    },
  },
  plugins: [],
} satisfies Config;
