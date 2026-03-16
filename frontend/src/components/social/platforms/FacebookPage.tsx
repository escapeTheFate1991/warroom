"use client";

import { Facebook } from "lucide-react";
import PlatformPage from "./PlatformPage";

export default function FacebookPage() {
  return (
    <PlatformPage
      platform="facebook"
      platformConfig={{
        name: "Facebook",
        icon: Facebook,
        color: "#1877F2",
        bgColor: "bg-blue-500/10"
      }}
    />
  );
}