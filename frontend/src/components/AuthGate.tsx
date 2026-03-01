"use client";

import { usePathname } from "next/navigation";
import { AuthProvider } from "@/components/AuthProvider";

const PUBLIC_PATHS = ["/login", "/signup"];

export function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // Login and signup pages render without auth protection
  if (PUBLIC_PATHS.includes(pathname)) {
    return <>{children}</>;
  }

  // All other pages require authentication
  return <AuthProvider>{children}</AuthProvider>;
}
