"use client";

import { useState, useEffect } from "react";
import { User, Mail, Phone, Building2, Save, CheckCircle, Loader2 } from "lucide-react";
import { authFetch, API } from "@/lib/api";

interface ProfileField {
  key: string;
  label: string;
  icon: React.ElementType;
  placeholder: string;
  type?: string;
}

const PROFILE_FIELDS: ProfileField[] = [
  { key: "your_name", label: "Your Name", icon: User, placeholder: "Eddy" },
  { key: "your_email", label: "Email", icon: Mail, placeholder: "eddy@stuffnthings.io", type: "email" },
  { key: "your_phone", label: "Phone", icon: Phone, placeholder: "(555) 123-4567", type: "tel" },
  { key: "company_name", label: "Company", icon: Building2, placeholder: "Stuff N Things" },
];

export default function ProfilePage() {
  const [fields, setFields] = useState<Record<string, string>>({});
  const [original, setOriginal] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    authFetch(`${API}/api/settings?category=general`)
      .then((r) => (r.ok ? r.json() : []))
      .then((items: any[]) => {
        const map: Record<string, string> = {};
        for (const s of items) {
          if (PROFILE_FIELDS.some((f) => f.key === s.key)) {
            map[s.key] = s.value || "";
          }
        }
        setFields(map);
        setOriginal(map);
      })
      .catch(() => {});
  }, []);

  const hasChanges = PROFILE_FIELDS.some((f) => (fields[f.key] || "") !== (original[f.key] || ""));

  const handleSave = async () => {
    setSaving(true);
    const promises = PROFILE_FIELDS.filter(
      (f) => (fields[f.key] || "") !== (original[f.key] || "")
    ).map((f) =>
      authFetch(`${API}/api/settings/${f.key}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: fields[f.key] || "", category: "general" }),
      })
    );

    try {
      await Promise.all(promises);
      setOriginal({ ...fields });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-lg mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <div className="w-16 h-16 rounded-full bg-warroom-accent/20 flex items-center justify-center">
            <User size={28} className="text-warroom-accent" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-warroom-text">
              {fields.your_name || "Your Profile"}
            </h1>
            <p className="text-sm text-warroom-muted">
              This info is used in cold emails, call scripts, and contracts.
            </p>
          </div>
        </div>

        {/* Fields */}
        <div className="space-y-4">
          {PROFILE_FIELDS.map((f) => {
            const Icon = f.icon;
            return (
              <div key={f.key}>
                <label className="text-xs font-medium text-warroom-muted mb-1.5 block">
                  {f.label}
                </label>
                <div className="relative">
                  <Icon
                    size={15}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted"
                  />
                  <input
                    type={f.type || "text"}
                    value={fields[f.key] || ""}
                    onChange={(e) =>
                      setFields((prev) => ({ ...prev, [f.key]: e.target.value }))
                    }
                    placeholder={f.placeholder}
                    className="w-full pl-10 pr-4 py-2.5 bg-warroom-bg border border-warroom-border rounded-lg text-sm text-warroom-text placeholder:text-warroom-muted/40 focus:outline-none focus:border-warroom-accent/50 transition"
                  />
                </div>
              </div>
            );
          })}
        </div>

        {/* Save */}
        <div className="mt-6">
          <button
            onClick={handleSave}
            disabled={!hasChanges || saving}
            className="flex items-center gap-2 px-5 py-2.5 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-sm font-medium transition"
          >
            {saving ? (
              <Loader2 size={15} className="animate-spin" />
            ) : saved ? (
              <CheckCircle size={15} />
            ) : (
              <Save size={15} />
            )}
            {saving ? "Saving..." : saved ? "Saved" : "Save Profile"}
          </button>
        </div>
      </div>
    </div>
  );
}
