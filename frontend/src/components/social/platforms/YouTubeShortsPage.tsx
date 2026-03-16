"use client";

import { Youtube } from "lucide-react";
import PlatformPage from "./PlatformPage";

export default function YouTubeShortsPage() {
  return (
    <PlatformPage
      platform="youtube"
      platformConfig={{
        name: "YouTube Shorts",
        icon: Youtube,
        color: "#FF0000",
        bgColor: "bg-red-500/10"
      }}
    />
  );
}