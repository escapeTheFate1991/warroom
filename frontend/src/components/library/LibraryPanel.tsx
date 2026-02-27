"use client";

import { useState, useEffect } from "react";
import { Search, Database, FileText, Loader2 } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface Collection {
  name: string;
  points: number;
  vectors: number;
}

interface SearchResult {
  id: string;
  score: number;
  payload: Record<string, unknown>;
}

export default function LibraryPanel() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollection, setSelectedCollection] = useState("friday-knowledge");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/library/collections`)
      .then((r) => r.json())
      .then((data) => setCollections(data.collections || []))
      .catch(() => {});
  }, []);

  const search = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const resp = await fetch(`${API}/api/library/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, collection: selectedCollection, limit: 10 }),
      });
      const data = await resp.json();
      setResults(data.results || []);
    } catch {
      console.error("Search failed");
    }
    setSearching(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") search();
  };

  return (
    <div className="flex flex-col h-full">
      <div className="h-14 border-b border-warroom-border flex items-center px-6">
        <h2 className="text-sm font-semibold">Mental Library</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {/* Collection selector + search */}
        <div className="flex gap-3 mb-6">
          <select
            value={selectedCollection}
            onChange={(e) => setSelectedCollection(e.target.value)}
            className="bg-warroom-surface border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text"
          >
            {collections.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name} ({c.points})
              </option>
            ))}
          </select>
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search knowledge..."
              className="w-full bg-warroom-surface border border-warroom-border rounded-lg pl-10 pr-4 py-2 text-sm text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
            />
          </div>
          <button
            onClick={search}
            disabled={searching}
            className="px-4 py-2 bg-warroom-accent rounded-lg text-sm font-medium hover:bg-warroom-accent/80 disabled:opacity-50 transition"
          >
            {searching ? <Loader2 size={16} className="animate-spin" /> : "Search"}
          </button>
        </div>

        {/* Collection stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          {collections.map((c) => (
            <div
              key={c.name}
              onClick={() => setSelectedCollection(c.name)}
              className={`bg-warroom-surface border rounded-lg p-3 cursor-pointer transition ${
                selectedCollection === c.name
                  ? "border-warroom-accent"
                  : "border-warroom-border hover:border-warroom-accent/30"
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <Database size={14} className="text-warroom-accent" />
                <span className="text-xs font-medium truncate">{c.name.replace("friday-", "")}</span>
              </div>
              <p className="text-lg font-semibold">{c.points}</p>
              <p className="text-[10px] text-warroom-muted">documents</p>
            </div>
          ))}
        </div>

        {/* Results */}
        <div className="space-y-3">
          {results.map((r) => (
            <div
              key={r.id}
              className="bg-warroom-surface border border-warroom-border rounded-lg p-4"
            >
              <div className="flex items-center gap-2 mb-2">
                <FileText size={14} className="text-warroom-accent" />
                <span className="text-xs text-warroom-muted">Score: {(r.score * 100).toFixed(1)}%</span>
              </div>
              <p className="text-sm whitespace-pre-wrap">
                {(r.payload.text as string) || JSON.stringify(r.payload)}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
