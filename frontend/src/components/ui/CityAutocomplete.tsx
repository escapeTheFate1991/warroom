"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MapPin } from "lucide-react";

interface CityAutocompleteProps {
  state: string; // 2-letter state code
  value: string;
  onChange: (city: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

/**
 * Searchable city dropdown with autocomplete.
 * Loads 29k+ US cities lazily per-state, filters as you type.
 * Keyboard nav: ArrowDown/Up to move, Enter to select, Escape to close.
 */
export default function CityAutocomplete({
  state,
  value,
  onChange,
  disabled = false,
  placeholder,
  className = "",
}: CityAutocompleteProps) {
  const [query, setQuery] = useState(value);
  const [open, setOpen] = useState(false);
  const [cities, setCities] = useState<string[]>([]);
  const [highlighted, setHighlighted] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Load cities for the selected state (lazy import to avoid 335KB in initial bundle)
  useEffect(() => {
    if (!state) {
      setCities([]);
      return;
    }
    import("@/data/us-all-cities").then((mod) => {
      const stateCities = mod.US_ALL_CITIES[state] || [];
      setCities(stateCities);
    });
  }, [state]);

  // Sync external value changes
  useEffect(() => {
    setQuery(value);
  }, [value]);

  // Filtered results (max 100 shown for performance)
  const filtered = useMemo(() => {
    if (!query) return cities.slice(0, 100);
    const q = query.toLowerCase();
    // Prioritize: starts-with first, then includes
    const startsWith: string[] = [];
    const includes: string[] = [];
    for (const city of cities) {
      const lower = city.toLowerCase();
      if (lower.startsWith(q)) startsWith.push(city);
      else if (lower.includes(q)) includes.push(city);
      if (startsWith.length + includes.length >= 100) break;
    }
    return [...startsWith, ...includes];
  }, [query, cities]);

  const selectCity = useCallback((city: string) => {
    setQuery(city);
    onChange(city);
    setOpen(false);
    setHighlighted(-1);
  }, [onChange]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open && e.key === "ArrowDown") {
      setOpen(true);
      return;
    }
    if (!open) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted((h) => Math.min(h + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (highlighted >= 0 && highlighted < filtered.length) {
        selectCity(filtered[highlighted]);
      }
    } else if (e.key === "Escape") {
      setOpen(false);
      setHighlighted(-1);
    }
  };

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlighted >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll("[data-city]");
      items[highlighted]?.scrollIntoView({ block: "nearest" });
    }
  }, [highlighted]);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (inputRef.current && !inputRef.current.parentElement?.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div className="relative flex-1">
      <MapPin size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted pointer-events-none z-10" />
      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          setHighlighted(-1);
          // If user clears, also clear the selected value
          if (!e.target.value) onChange("");
        }}
        onFocus={() => { if (cities.length > 0) setOpen(true); }}
        onKeyDown={handleKeyDown}
        disabled={disabled || !state}
        placeholder={state ? (placeholder || "Type city or town...") : "Select state first..."}
        className={`w-full bg-warroom-surface border border-warroom-border rounded-lg pl-9 pr-4 py-2.5 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
        style={{ colorScheme: "dark" }}
        autoComplete="off"
      />

      {/* Dropdown */}
      {open && filtered.length > 0 && (
        <div
          ref={listRef}
          className="absolute z-50 top-full mt-1 w-full max-h-60 overflow-y-auto bg-warroom-surface border border-warroom-border rounded-lg shadow-lg"
        >
          {filtered.map((city, i) => (
            <button
              key={city}
              data-city={city}
              onMouseDown={(e) => {
                e.preventDefault(); // Prevent input blur
                selectCity(city);
              }}
              onMouseEnter={() => setHighlighted(i)}
              className={`w-full text-left px-3 py-2 text-sm transition ${
                i === highlighted
                  ? "bg-warroom-accent/20 text-warroom-accent"
                  : "text-warroom-text hover:bg-warroom-bg"
              }`}
            >
              {city}
            </button>
          ))}
          {filtered.length === 100 && (
            <div className="px-3 py-2 text-[10px] text-warroom-muted text-center border-t border-warroom-border/50">
              Type more to narrow results...
            </div>
          )}
        </div>
      )}

      {open && state && filtered.length === 0 && query && (
        <div className="absolute z-50 top-full mt-1 w-full bg-warroom-surface border border-warroom-border rounded-lg shadow-lg p-3 text-xs text-warroom-muted text-center">
          No cities found matching &ldquo;{query}&rdquo;
        </div>
      )}
    </div>
  );
}
