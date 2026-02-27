"use client";

import { Calendar } from "lucide-react";

export default function ActivitiesPanel() {
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 justify-between">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <Calendar size={16} />
          Activities
        </h2>
      </div>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center text-warroom-muted">
          <Calendar size={48} className="mx-auto mb-4 opacity-20" />
          <p className="text-sm">Activities management coming soon</p>
        </div>
      </div>
    </div>
  );
}