import type { Metadata } from "next";
import "./globals.css";
import { AuthGate } from "@/components/AuthGate";

export const metadata: Metadata = {
  title: "WAR ROOM",
  description: "Mission Control — yieldlabs",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-warroom-bg">
        <AuthGate>{children}</AuthGate>
      </body>
    </html>
  );
}
