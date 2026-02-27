"use client";

import { Users } from "lucide-react";

export default function ContactsManager() {
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 justify-between">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <Users size={16} />
          Contacts
        </h2>
      </div>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center text-warroom-muted">
          <Users size={48} className="mx-auto mb-4 opacity-20" />
          <p className="text-sm">Contacts management coming soon</p>
        </div>
      </div>
    </div>
  );
}