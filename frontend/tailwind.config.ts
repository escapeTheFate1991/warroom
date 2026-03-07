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
    },
  },
  plugins: [],
} satisfies Config;
