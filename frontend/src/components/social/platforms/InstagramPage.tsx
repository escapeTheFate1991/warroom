"use client";

import { Instagram } from "lucide-react";
import PlatformPage from "./PlatformPage";

export default function InstagramPage() {
  return (
    <PlatformPage
      platform="instagram"
      platformConfig={{
        name: "Instagram",
        icon: Instagram,
        color: "#E4405F",
        bgColor: "bg-pink-500/10"
      }}
    />
  );
}