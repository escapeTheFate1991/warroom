"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function TopContentPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to main app with intelligence tab active
    router.replace("/?tab=intelligence");
  }, [router]);

  return (
    <div className="h-screen flex items-center justify-center bg-warroom-bg text-warroom-text">
      <p className="text-sm text-warroom-muted">Redirecting to Competitor Intelligence...</p>
    </div>
  );
}