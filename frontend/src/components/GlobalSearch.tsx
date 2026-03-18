"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { 
  Search, 
  User, 
  TrendingUp, 
  Users, 
  FileText, 
  Sparkles,
  ArrowRight,
  Clock,
  X,
  Loader2
} from "lucide-react";
import { authFetch, API } from "@/lib/api";

interface SearchResult {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  url: string;
}

interface SearchResponse {
  results: SearchResult[];
}

interface RecentSearch {
  query: string;
  timestamp: number;
}

const RECENT_SEARCHES_KEY = "warroom_recent_searches";
const MAX_RECENT_SEARCHES = 5;

const TYPE_ICONS = {
  Contact: User,
  Deal: TrendingUp,
  Lead: Users,
  Competitor: Users,
  Post: FileText,
  "Digital Copy": Sparkles,
} as const;

const TYPE_COLORS = {
  Contact: "text-blue-500",
  Deal: "text-green-500",
  Lead: "text-purple-500",
  Competitor: "text-orange-500",
  Post: "text-yellow-500",
  "Digital Copy": "text-pink-500",
} as const;

export default function GlobalSearch() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>([]);

  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  // Load recent searches on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(RECENT_SEARCHES_KEY);
      if (saved) {
        try {
          setRecentSearches(JSON.parse(saved));
        } catch (e) {
          console.error("Failed to parse recent searches:", e);
        }
      }
    }
  }, []);

  // Save recent searches to localStorage
  const saveRecentSearches = useCallback((searches: RecentSearch[]) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(searches));
    }
  }, []);

  // Add to recent searches
  const addRecentSearch = useCallback((searchQuery: string) => {
    if (!searchQuery.trim()) return;
    
    setRecentSearches(prev => {
      const filtered = prev.filter(s => s.query !== searchQuery);
      const updated = [{ query: searchQuery, timestamp: Date.now() }, ...filtered]
        .slice(0, MAX_RECENT_SEARCHES);
      saveRecentSearches(updated);
      return updated;
    });
  }, [saveRecentSearches]);

  // Remove from recent searches
  const removeRecentSearch = useCallback((searchQuery: string) => {
    setRecentSearches(prev => {
      const updated = prev.filter(s => s.query !== searchQuery);
      saveRecentSearches(updated);
      return updated;
    });
  }, [saveRecentSearches]);

  // Debounced search
  const performSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      setLoading(false);
      return;
    }

    try {
      const response = await authFetch(`${API}/api/search?q=${encodeURIComponent(searchQuery)}&limit=10`);
      if (response.ok) {
        const data: SearchResponse = await response.json();
        setResults(data.results);
      } else {
        console.error("Search failed:", response.statusText);
        setResults([]);
      }
    } catch (error) {
      console.error("Search error:", error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Handle input change with debounce
  const handleInputChange = useCallback((value: string) => {
    setQuery(value);
    setSelectedIndex(-1);

    // Clear previous debounce
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (value.trim()) {
      setLoading(true);
      debounceRef.current = setTimeout(() => {
        performSearch(value);
      }, 300);
    } else {
      setResults([]);
      setLoading(false);
    }
  }, [performSearch]);

  // Navigate to result
  const navigateToResult = useCallback((result: SearchResult) => {
    addRecentSearch(query);
    setIsOpen(false);
    setQuery("");
    setResults([]);
    window.location.href = result.url;
  }, [query, addRecentSearch]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!isOpen) return;

    const allItems = query.trim() ? results : recentSearches.map(r => ({ 
      id: `recent-${r.query}`, 
      type: "Recent", 
      title: r.query, 
      subtitle: "Recent search", 
      url: "" 
    }));

    switch (e.key) {
      case "Escape":
        setIsOpen(false);
        setQuery("");
        setResults([]);
        setSelectedIndex(-1);
        break;
      case "ArrowDown":
        e.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, allItems.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, -1));
        break;
      case "Enter":
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < allItems.length) {
          const item = allItems[selectedIndex];
          if (item.type === "Recent") {
            setQuery(item.title);
            handleInputChange(item.title);
            setSelectedIndex(-1);
          } else {
            navigateToResult(item as SearchResult);
          }
        }
        break;
    }
  }, [isOpen, results, recentSearches, query, selectedIndex, handleInputChange, navigateToResult]);

  // Global keyboard shortcut (Cmd+K / Ctrl+K)
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
        inputRef.current?.focus();
      }
    };

    document.addEventListener('keydown', handleGlobalKeyDown);
    return () => document.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  // Group results by type
  const groupedResults = results.reduce((acc, result) => {
    if (!acc[result.type]) {
      acc[result.type] = [];
    }
    acc[result.type].push(result);
    return acc;
  }, {} as Record<string, SearchResult[]>);

  const showRecents = !query.trim() && recentSearches.length > 0;
  const showResults = query.trim() && results.length > 0;
  const showNoResults = query.trim() && !loading && results.length === 0;

  return (
    <div ref={containerRef} className="relative w-full max-w-xl">
      <div className="relative">
        <Search 
          size={15} 
          className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" 
        />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => handleInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsOpen(true)}
          placeholder="Search everything... (⌘K)"
          className="glass-card inner-glow w-full pl-9 pr-4 py-2 text-sm text-warroom-text placeholder:text-warroom-muted/50 focus:outline-none focus:shadow-glow-sm focus:border-warroom-accent"
        />
        {loading && (
          <Loader2 
            size={15} 
            className="absolute right-3 top-1/2 -translate-y-1/2 text-warroom-muted animate-spin" 
          />
        )}
      </div>

      {isOpen && (
        <div 
          ref={resultsRef}
          className="absolute top-full mt-2 w-full glass-card shadow-2xl shadow-black/20 border border-warroom-border/50 max-h-96 overflow-y-auto z-50"
        >
          {/* Recent Searches */}
          {showRecents && (
            <div className="p-2">
              <div className="flex items-center gap-2 px-2 py-1 mb-2">
                <Clock size={14} className="text-warroom-muted" />
                <span className="text-xs font-medium text-warroom-muted uppercase tracking-wide">
                  Recent Searches
                </span>
              </div>
              {recentSearches.map((recent, index) => (
                <div
                  key={`recent-${recent.query}`}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                    selectedIndex === index 
                      ? "bg-warroom-accent/15 text-warroom-accent" 
                      : "hover:bg-warroom-border/30 text-warroom-text/70"
                  }`}
                  onClick={() => {
                    setQuery(recent.query);
                    handleInputChange(recent.query);
                    setSelectedIndex(-1);
                  }}
                >
                  <Clock size={14} className="text-warroom-muted flex-shrink-0" />
                  <span className="text-sm flex-1">{recent.query}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeRecentSearch(recent.query);
                    }}
                    className="p-1 hover:bg-warroom-border/50 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X size={12} className="text-warroom-muted" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Search Results */}
          {showResults && (
            <div className="p-2">
              {Object.entries(groupedResults).map(([type, typeResults]) => (
                <div key={type} className="mb-4 last:mb-2">
                  <div className="px-2 py-1 mb-2">
                    <span className="text-xs font-medium text-warroom-muted uppercase tracking-wide">
                      {type}s
                    </span>
                  </div>
                  {typeResults.map((result, typeIndex) => {
                    const globalIndex = results.indexOf(result);
                    const Icon = TYPE_ICONS[result.type as keyof typeof TYPE_ICONS] || FileText;
                    const colorClass = TYPE_COLORS[result.type as keyof typeof TYPE_COLORS] || "text-warroom-muted";
                    
                    return (
                      <div
                        key={result.id}
                        className={`flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors group ${
                          selectedIndex === globalIndex
                            ? "bg-warroom-accent/15 text-warroom-accent"
                            : "hover:bg-warroom-border/30"
                        }`}
                        onClick={() => navigateToResult(result)}
                      >
                        <Icon size={16} className={`flex-shrink-0 ${colorClass}`} />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-warroom-text truncate">
                            {result.title}
                          </div>
                          {result.subtitle && (
                            <div className="text-xs text-warroom-muted truncate">
                              {result.subtitle}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          <span className="text-xs px-1.5 py-0.5 rounded bg-warroom-border/30 text-warroom-muted">
                            {result.type}
                          </span>
                          <ArrowRight size={12} className="text-warroom-muted opacity-0 group-hover:opacity-100 transition-opacity" />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          )}

          {/* No Results */}
          {showNoResults && (
            <div className="p-6 text-center">
              <Search size={24} className="mx-auto mb-2 text-warroom-muted/50" />
              <p className="text-sm text-warroom-muted">No results found for "{query}"</p>
              <p className="text-xs text-warroom-muted/70 mt-1">
                Try searching for contacts, deals, or competitors
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}