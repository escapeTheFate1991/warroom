import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        warroom: {
          bg: "var(--warroom-bg)",
          surface: "var(--warroom-surface)",
          border: "var(--warroom-border)",
          accent: "var(--warroom-accent)",
          text: "var(--warroom-text)",
          muted: "var(--warroom-muted)",
          success: "var(--warroom-success)",
          danger: "var(--warroom-danger)",
          warning: "var(--warroom-warning)",
        },
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
