"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Search, MapPin, Globe, Mail, Phone, Loader2, Building2, RefreshCw, Star, Filter, X } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";
const PAGE_SIZE = 50;

interface Lead {
  id: number;
  business_name: string;
  address: string | null;
  city: string | null;
  state: string | null;
  phone: string | null;
  website: string | null;
  google_rating: number | null;
  google_reviews_count: number;
  business_category: string | null;
  emails: string[];
  has_website: boolean;
  website_audit_score: number | null;
  website_audit_grade: string | null;
  lead_score: number;
  lead_tier: string;
  enrichment_status: string;
  search_job_id: number | null;
}

const BUSINESS_CATEGORIES = [
  "Plumbers",
  "Electricians",
  "HVAC Contractors",
  "Roofers",
  "Landscapers",
  "General Contractors",
  "Painters",
  "Pest Control",
  "Cleaning Services",
  "Moving Companies",
  "Restaurants",
  "Cafes & Coffee Shops",
  "Bars & Nightclubs",
  "Bakeries",
  "Food Trucks",
  "Catering Services",
  "Dentists",
  "Chiropractors",
  "Veterinarians",
  "Optometrists",
  "Medical Clinics",
  "Physical Therapy",
  "Mental Health Counselors",
  "Pharmacies",
  "Law Firms",
  "Accounting Firms",
  "Insurance Agents",
  "Financial Advisors",
  "Real Estate Agents",
  "Mortgage Brokers",
  "Auto Repair Shops",
  "Auto Dealerships",
  "Car Wash",
  "Towing Services",
  "Hair Salons",
  "Barber Shops",
  "Nail Salons",
  "Spas & Wellness",
  "Gyms & Fitness Centers",
  "Yoga Studios",
  "Martial Arts Studios",
  "Daycare Centers",
  "Tutoring Services",
  "Dog Grooming",
  "Pet Boarding",
  "Photography Studios",
  "Wedding Venues",
  "Event Planners",
  "Florists",
  "Printing Services",
  "IT Services",
  "Web Design Agencies",
  "Marketing Agencies",
  "Staffing Agencies",
  "Storage Facilities",
  "Hotels & Motels",
];

const TIER_COLORS: Record<string, string> = {
  hot: "bg-red-500/20 text-red-400",
  warm: "bg-orange-500/20 text-orange-400",
  cold: "bg-blue-500/20 text-blue-400",
  unscored: "bg-warroom-muted/20 text-warroom-muted",
};

export default function LeadgenPanel() {
  const [location, setLocation] = useState("");
  const [query, setQuery] = useState("");
  const [leads, setLeads] = useState<Lead[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchStatus, setSearchStatus] = useState("");
  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const [filterTier, setFilterTier] = useState<string>("");
  const [showAllLeads, setShowAllLeads] = useState(true);

  // Infinite scroll state
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Cache for prefetched pages
  const prefetchCache = useRef<Map<number, Lead[]>>(new Map());

  const buildUrl = useCallback((pageOffset: number) => {
    const params = new URLSearchParams({
      sort_by: "lead_score",
      sort_dir: "desc",
      limit: String(PAGE_SIZE),
      offset: String(pageOffset),
    });
    if (!showAllLeads && activeJobId) params.set("search_job_id", String(activeJobId));
    if (filterTier) params.set("tier", filterTier);
    return `${API}/api/leadgen/leads?${params}`;
  }, [activeJobId, filterTier, showAllLeads]);

  // Fetch a page of results
  const fetchPage = useCallback(async (pageOffset: number): Promise<Lead[]> => {
    // Check cache first
    const cached = prefetchCache.current.get(pageOffset);
    if (cached) {
      prefetchCache.current.delete(pageOffset);
      return cached;
    }
    const resp = await fetch(buildUrl(pageOffset));
    if (!resp.ok) return [];
    return resp.json();
  }, [buildUrl]);

  // Prefetch next page in background
  const prefetchNext = useCallback(async (nextOffset: number) => {
    if (prefetchCache.current.has(nextOffset)) return;
    try {
      const resp = await fetch(buildUrl(nextOffset));
      if (resp.ok) {
        const data = await resp.json();
        prefetchCache.current.set(nextOffset, data);
      }
    } catch { /* silent */ }
  }, [buildUrl]);

  // Load initial page (reset)
  const loadLeads = useCallback(async () => {
    setInitialLoading(true);
    setOffset(0);
    setHasMore(true);
    prefetchCache.current.clear();
    try {
      const data = await fetchPage(0);
      setLeads(data);
      setHasMore(data.length >= PAGE_SIZE);
      setOffset(PAGE_SIZE);
      // Prefetch page 2 & 3
      if (data.length >= PAGE_SIZE) {
        prefetchNext(PAGE_SIZE);
        prefetchNext(PAGE_SIZE * 2);
      }
    } catch {
      console.error("Failed to load leads");
    } finally {
      setInitialLoading(false);
    }
  }, [fetchPage, prefetchNext]);

  // Load more (append)
  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const data = await fetchPage(offset);
      if (data.length === 0) {
        setHasMore(false);
      } else {
        setLeads((prev) => [...prev, ...data]);
        const newOffset = offset + PAGE_SIZE;
        setOffset(newOffset);
        setHasMore(data.length >= PAGE_SIZE);
        // Prefetch next 2 pages
        if (data.length >= PAGE_SIZE) {
          prefetchNext(newOffset);
          prefetchNext(newOffset + PAGE_SIZE);
        }
      }
    } catch {
      console.error("Failed to load more");
    } finally {
      setLoadingMore(false);
    }
  }, [offset, hasMore, loadingMore, fetchPage, prefetchNext]);

  // Reload on filter/view changes
  useEffect(() => { loadLeads(); }, [loadLeads]);

  // IntersectionObserver for infinite scroll
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore && !initialLoading) {
          loadMore();
        }
      },
      { root: scrollRef.current, rootMargin: "400px" }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMore, loadingMore, initialLoading, loadMore]);

  const searchBusinesses = async () => {
    if (!location.trim() || !query.trim()) return;
    setSearching(true);
    setSearchStatus("Starting search...");
    try {
      const resp = await fetch(`${API}/api/leadgen/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, location, max_results: 60 }),
      });
      if (!resp.ok) { setSearchStatus("Search failed"); setSearching(false); return; }
      const job = await resp.json();
      setSearchStatus(`Searching for ${query} in ${location}...`);

      const poll = setInterval(async () => {
        try {
          const statusResp = await fetch(`${API}/api/leadgen/search/${job.id}`);
          const status = await statusResp.json();
          if (status.status === "complete") {
            clearInterval(poll);
            setSearchStatus(`Found ${status.total_found} businesses in ${location}`);
            setSearching(false);
            // Switch to showing only this search's results
            setActiveJobId(job.id);
            setShowAllLeads(false);
          } else if (status.status === "failed") {
            clearInterval(poll);
            setSearchStatus("Search failed");
            setSearching(false);
          } else {
            setSearchStatus(`Processing... (${status.total_found || 0} found so far)`);
          }
        } catch { clearInterval(poll); setSearching(false); }
      }, 2000);
    } catch {
      setSearchStatus("Network error");
      setSearching(false);
    }
  };

  const totalLabel = showAllLeads ? "All Leads" : `Search Results`;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 justify-between">
        <h2 className="text-sm font-semibold">Lead Generator</h2>
        <button onClick={loadLeads} disabled={searching} className="text-warroom-muted hover:text-warroom-text transition">
          <RefreshCw size={14} className={searching ? "animate-spin" : ""} />
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6">
        {/* Search bar */}
        <div className="flex gap-3 mb-3">
          <div className="relative flex-1">
            <MapPin size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && searchBusinesses()}
              placeholder="Location (e.g. Austin, TX)"
              className="w-full bg-warroom-surface border border-warroom-border rounded-lg pl-10 pr-4 py-2.5 text-sm text-warroom-text placeholder-warroom-muted focus:outline-none focus:border-warroom-accent"
            />
          </div>
          <div className="relative flex-1">
            <Building2 size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted pointer-events-none" />
            <select
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full bg-warroom-surface border border-warroom-border rounded-lg pl-10 pr-4 py-2.5 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent appearance-none cursor-pointer"
              style={{ colorScheme: "dark" }}
            >
              <option value="" disabled>Select business type...</option>
              {BUSINESS_CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
            <svg className="absolute right-3 top-1/2 -translate-y-1/2 text-warroom-muted pointer-events-none" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 4.5L6 7.5L9 4.5"/></svg>
          </div>
          <button
            onClick={searchBusinesses}
            disabled={searching || !location.trim() || !query.trim()}
            className="px-6 py-2.5 bg-warroom-accent rounded-lg text-sm font-medium hover:bg-warroom-accent/80 disabled:opacity-50 transition flex items-center gap-2"
          >
            {searching ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            Search
          </button>
        </div>

        {/* Status + filters bar */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            {searchStatus && (
              <p className="text-xs text-warroom-muted">{searchStatus}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Tier filter */}
            <select
              value={filterTier}
              onChange={(e) => setFilterTier(e.target.value)}
              className="bg-warroom-surface border border-warroom-border rounded-lg px-3 py-1.5 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent appearance-none cursor-pointer"
              style={{ colorScheme: "dark" }}
            >
              <option value="">All Tiers</option>
              <option value="hot">🔥 Hot</option>
              <option value="warm">🟠 Warm</option>
              <option value="cold">🔵 Cold</option>
            </select>

            {/* Toggle: search results vs all */}
            {activeJobId && (
              <button
                onClick={() => setShowAllLeads(!showAllLeads)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
                  showAllLeads
                    ? "bg-warroom-border/50 text-warroom-muted hover:text-warroom-text"
                    : "bg-warroom-accent/20 text-warroom-accent"
                }`}
              >
                <Filter size={12} />
                {showAllLeads ? "Show Search Results" : "Show All Leads"}
              </button>
            )}
          </div>
        </div>

        {/* Results table */}
        {leads.length > 0 && (
          <div className="bg-warroom-surface border border-warroom-border rounded-lg overflow-hidden">
            <div className="px-4 py-2 border-b border-warroom-border flex items-center justify-between">
              <span className="text-xs text-warroom-muted">
                {totalLabel} · {leads.length} loaded{hasMore ? "+" : ""}
              </span>
              {!showAllLeads && activeJobId && (
                <button
                  onClick={() => { setShowAllLeads(true); setActiveJobId(null); setSearchStatus(""); }}
                  className="text-[10px] text-warroom-muted hover:text-warroom-text flex items-center gap-1 transition"
                >
                  <X size={10} /> Clear filter
                </button>
              )}
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-warroom-border">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Business</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Contact</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Website</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Score</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr key={lead.id} className="border-b border-warroom-border/50 hover:bg-warroom-border/20">
                    <td className="px-4 py-3">
                      <p className="font-medium">{lead.business_name}</p>
                      <p className="text-xs text-warroom-muted">{[lead.city, lead.state].filter(Boolean).join(", ") || lead.address}</p>
                      {lead.business_category && (
                        <p className="text-[10px] text-warroom-muted/70 mt-0.5">{lead.business_category}</p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {lead.phone && (
                        <div className="flex items-center gap-1 text-xs text-warroom-muted">
                          <Phone size={10} /> {lead.phone}
                        </div>
                      )}
                      {lead.emails?.[0] && (
                        <div className="flex items-center gap-1 text-xs text-warroom-accent mt-0.5">
                          <Mail size={10} /> {lead.emails[0]}
                        </div>
                      )}
                      {lead.google_rating && (
                        <div className="flex items-center gap-1 text-[10px] text-warroom-muted mt-0.5">
                          <Star size={8} /> {lead.google_rating} ({lead.google_reviews_count})
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {lead.website ? (
                        <a href={lead.website} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-warroom-accent hover:underline">
                          <Globe size={10} /> {(() => { try { return new URL(lead.website).hostname; } catch { return lead.website; } })()}
                        </a>
                      ) : (
                        <span className="text-xs text-warroom-danger">No website</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1">
                        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full w-fit ${TIER_COLORS[lead.lead_tier] || TIER_COLORS.unscored}`}>
                          {lead.lead_tier}
                        </span>
                        <span className="text-xs text-warroom-muted">{lead.lead_score}/100</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Infinite scroll sentinel */}
            <div ref={sentinelRef} className="h-1" />

            {loadingMore && (
              <div className="flex items-center justify-center py-4 text-warroom-muted">
                <Loader2 size={16} className="animate-spin mr-2" />
                <span className="text-xs">Loading more...</span>
              </div>
            )}

            {!hasMore && leads.length > 0 && (
              <div className="text-center py-3 text-xs text-warroom-muted/50">
                All {leads.length} leads loaded
              </div>
            )}
          </div>
        )}

        {leads.length === 0 && !searching && !initialLoading && (
          <div className="flex flex-col items-center justify-center py-20 text-warroom-muted">
            <Search size={48} className="mb-4 opacity-20" />
            <p className="text-sm">Search for businesses to populate your lead database</p>
          </div>
        )}

        {initialLoading && (
          <div className="flex items-center justify-center py-20 text-warroom-muted">
            <Loader2 size={24} className="animate-spin mr-3" />
            <span className="text-sm">Loading leads...</span>
          </div>
        )}
      </div>
    </div>
  );
}
