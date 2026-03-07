"use client";

import { createContext, useContext, ReactNode } from "react";
import { useTheme } from "@/hooks/useTheme";

type Theme = "dark" | "light";

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType>({
  theme: "dark",
  setTheme: () => {},
  toggleTheme: () => {},
});

export const useThemeContext = () => useContext(ThemeContext);

export default function ThemeProvider({ children }: { children: ReactNode }) {
  const themeState = useTheme();
  return (
    <ThemeContext.Provider value={themeState}>
      {children}
    </ThemeContext.Provider>
  );
}
