"use client";

import PlatformPage from "./PlatformPage";

// Custom TikTok icon since Lucide doesn't have one
function TikTokIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <path d="M19.589 6.686a4.793 4.793 0 0 1-3.77-4.245V2h-3.445v13.672a2.896 2.896 0 0 1-5.201 1.743l-.002-.001.002.001a2.895 2.895 0 0 1 3.183-4.51v-3.5a6.329 6.329 0 0 0-1.183-.11C5.6 8.205 2.17 11.634 2.17 15.98c0 4.344 3.429 7.674 7.774 7.674 4.344 0 7.874-3.33 7.874-7.674V10.12a8.23 8.23 0 0 0 4.715 1.49V8.56a4.831 4.831 0 0 1-2.944-1.874z"/>
    </svg>
  );
}

export default function TikTokPage() {
  return (
    <PlatformPage
      platform="tiktok"
      platformConfig={{
        name: "TikTok",
        icon: TikTokIcon,
        color: "#000000",
        bgColor: "bg-gray-900/10"
      }}
    />
  );
}