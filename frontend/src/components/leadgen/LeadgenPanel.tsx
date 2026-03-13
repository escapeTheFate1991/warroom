"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Search, MapPin, Globe, Mail, Phone, Loader2, Building2, RefreshCw, Star, Filter, X, AlertTriangle, Clock, Trash2, Rocket } from "lucide-react";
import LeadDrawer, { LeadFull } from "./LeadDrawer";
import { API, authFetch } from "@/lib/api";
import LoadingState from "@/components/ui/LoadingState";
import EmptyState from "@/components/ui/EmptyState";
import { US_STATES } from "@/data/us-cities";
import CityAutocomplete from "@/components/ui/CityAutocomplete";

const PAGE_SIZE = 10;

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
  outreach_status: string;
  contacted_by: string | null;
  contacted_at: string | null;
}

interface SearchJobStatus {
  job_id: number;
  status: string;
  query: string;
  location: string;
  total_found: number;
  total_leads: number;
  enriched: number;
  pending: number;
  failed: number;
  error_message: string | null;
  message: string;
  created_at: string | null;
  age_days: number;
}

interface FreshnessEntry {
  job_id: number;
  query: string;
  location: string;
  status: string;
  total_found: number;
  created_at: string | null;
  age_days: number;
  age_label: string;
  is_stale: boolean;
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

/* ------------------------------------------------------------------ */
/*  Error Banner Component                                             */
/* ------------------------------------------------------------------ */
function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 mb-4">
      <AlertTriangle size={16} className="text-red-400 mt-0.5 shrink-0" />
      <div className="flex-1">
        <p className="text-sm text-red-400">{message}</p>
      </div>
      <button onClick={onDismiss} className="text-red-400/60 hover:text-red-400 transition">
        <X size={14} />
      </button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Freshness Badge                                                    */
/* ------------------------------------------------------------------ */
function FreshnessBadge({ ageDays }: { ageDays: number }) {
  if (ageDays < 0) return null;
  const isStale = ageDays > 30;
  const label =
    ageDays === 0 ? "Today" : ageDays === 1 ? "1 day old" : `${ageDays}d old`;
  return (
    <span
      className={`inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full ${
        isStale
          ? "bg-red-500/15 text-red-400"
          : ageDays > 14
          ? "bg-yellow-500/15 text-yellow-400"
          : "bg-emerald-500/15 text-emerald-400"
      }`}
    >
      <Clock size={8} />
      {label}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Panel                                                         */
/* ------------------------------------------------------------------ */
export default function LeadgenPanel() {
  const [selectedState, setSelectedState] = useState("");
  const [selectedCity, setSelectedCity] = useState("");
  const [radiusMiles, setRadiusMiles] = useState(25);
  const [query, setQuery] = useState("");
  const [leads, setLeads] = useState<Lead[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchStatus, setSearchStatus] = useState("");
  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const [filterTier, setFilterTier] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterWebsite, setFilterWebsite] = useState<string>("");
  const [showAllLeads, setShowAllLeads] = useState(true);
  const [viewTab, setViewTab] = useState<"current" | "historical">("current");

  // Error state
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Freshness data for active job
  const [activeJobAge, setActiveJobAge] = useState<number | null>(null);

  // Drawer state
  const [selectedLead, setSelectedLead] = useState<LeadFull | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Infinite scroll state
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const sentinelRef = useRef<HTMLDivElement>(null);

  // Toast state for pipeline actions
  const [pipelineToast, setPipelineToast] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Auto-dismiss toast
  useEffect(() => {
    if (pipelineToast) {
      const t = setTimeout(() => setPipelineToast(null), 4000);
      return () => clearTimeout(t);
    }
  }, [pipelineToast]);

  const startPipeline = async (lead: Lead, e?: React.MouseEvent) => {
    e?.stopPropagation();
    try {
      const res = await authFetch(`${API}/api/crm/deals/convert-from-lead`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          leadgen_lead_id: lead.id,
          title: lead.business_name,
          business_name: lead.business_name,
          business_category: lead.business_category,
          phone: lead.phone,
          website: lead.website,
          emails: lead.emails,
          address: lead.address,
          city: lead.city,
          state: lead.state,
          // Propagate enrichment data to deal metadata
          google_place_id: (lead as any).google_place_id,
          google_rating: (lead as any).google_rating,
          yelp_url: (lead as any).yelp_url,
          yelp_rating: (lead as any).yelp_rating,
          audit_lite_flags: (lead as any).audit_lite_flags,
          website_audit_score: (lead as any).website_audit_score,
          website_audit_grade: (lead as any).website_audit_grade,
          website_audit_summary: (lead as any).website_audit_summary,
          website_audit_top_fixes: (lead as any).website_audit_top_fixes,
          review_pain_points: (lead as any).review_pain_points,
          review_opportunity_flags: (lead as any).review_opportunity_flags,
          lead_score: (lead as any).lead_score,
          lead_tier: (lead as any).lead_tier,
        }),
      });
      if (res.ok) {
        setPipelineToast({ type: "success", message: `✓ Deal created — ${lead.business_name} added to Lead Discovery` });
      } else {
        setPipelineToast({ type: "error", message: "Failed to create deal" });
      }
    } catch {
      setPipelineToast({ type: "error", message: "Failed to create deal" });
    }
  };
  const scrollRef = useRef<HTMLDivElement>(null);

  // Cache for prefetched pages
  const prefetchCache = useRef<Map<number, Lead[]>>(new Map());

  // Active polling interval ref (for cleanup)
  const enrichmentPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const searchPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const cancelSearch = () => {
    if (searchPollRef.current) {
      clearInterval(searchPollRef.current);
      searchPollRef.current = null;
    }
    setSearching(false);
    setSearchStatus("");
  };

  const dismissError = useCallback(() => setErrorMessage(null), []);

  const buildUrl = useCallback((pageOffset: number) => {
    if (viewTab === "historical") {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(pageOffset),
      });
      if (filterStatus) params.set("outcome", filterStatus);
      return `${API}/api/leadgen/contacts?${params}`;
    }
    const params = new URLSearchParams({
      sort_by: "lead_score",
      sort_dir: "desc",
      limit: String(PAGE_SIZE),
      offset: String(pageOffset),
    });
    if (!showAllLeads && activeJobId) params.set("search_job_id", String(activeJobId));
    if (filterTier) params.set("tier", filterTier);
    if (filterStatus) params.set("outreach_status", filterStatus);
    if (filterWebsite) params.set("has_website", filterWebsite);
    return `${API}/api/leadgen/leads?${params}`;
  }, [activeJobId, filterTier, filterStatus, filterWebsite, showAllLeads, viewTab]);

  // Fetch a page of results
  const fetchPage = useCallback(async (pageOffset: number): Promise<Lead[]> => {
    const cached = prefetchCache.current.get(pageOffset);
    if (cached) {
      prefetchCache.current.delete(pageOffset);
      return cached;
    }
    const resp = await authFetch(buildUrl(pageOffset));
    if (!resp.ok) {
      const detail = await resp.text().catch(() => "Unknown error");
      throw new Error(`Failed to load leads (${resp.status}): ${detail}`);
    }
    return resp.json();
  }, [buildUrl]);

  // Prefetch next page in background
  const prefetchNext = useCallback(async (nextOffset: number) => {
    if (prefetchCache.current.has(nextOffset)) return;
    try {
      const resp = await authFetch(buildUrl(nextOffset));
      if (resp.ok) {
        const data = await resp.json();
        prefetchCache.current.set(nextOffset, data);
      }
    } catch { /* silent prefetch failure */ }
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
      if (data.length >= PAGE_SIZE) {
        prefetchNext(PAGE_SIZE);
        prefetchNext(PAGE_SIZE * 2);
      }
      setErrorMessage(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load leads";
      console.error("Failed to load leads:", msg);
      setErrorMessage(msg);
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
        if (data.length >= PAGE_SIZE) {
          prefetchNext(newOffset);
          prefetchNext(newOffset + PAGE_SIZE);
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load more leads";
      setErrorMessage(msg);
    } finally {
      setLoadingMore(false);
    }
  }, [offset, hasMore, loadingMore, fetchPage, prefetchNext]);

  // Reload on filter/view changes
  useEffect(() => { loadLeads(); }, [loadLeads]);

  // Cleanup enrichment polling on unmount
  useEffect(() => {
    return () => {
      if (enrichmentPollRef.current) clearInterval(enrichmentPollRef.current);
    };
  }, []);

  // Fetch freshness for active job
  useEffect(() => {
    if (!activeJobId) {
      setActiveJobAge(null);
      return;
    }
    (async () => {
      try {
        const resp = await authFetch(`${API}/api/leadgen/search/${activeJobId}/status`);
        if (resp.ok) {
          const data: SearchJobStatus = await resp.json();
          setActiveJobAge(data.age_days);
        }
      } catch { /* silent */ }
    })();
  }, [activeJobId]);

  // Handle lead row click
  const handleLeadClick = async (lead: Lead) => {
    try {
      const response = await authFetch(`${API}/api/leadgen/leads/${lead.id}`);
      if (!response.ok) {
        const detail = await response.text().catch(() => "");
        throw new Error(`Failed to load lead details (${response.status}): ${detail}`);
      }
      const fullLead: LeadFull = await response.json();
      setSelectedLead(fullLead);
      setIsDrawerOpen(true);
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Failed to fetch lead details";
      setErrorMessage(msg);
      // Fallback: use partial data
      const partialLead: LeadFull = {
        ...lead,
        website_audit_summary: null,
        website_audit_top_fixes: [],
        audit_lite_flags: [],
        facebook_url: null,
        instagram_url: null,
        linkedin_url: null,
        twitter_url: null,
        contact_outcome: null,
        contact_notes: null,
        contact_history: [],
        contact_who_answered: null,
        contact_owner_name: null,
        contact_economic_buyer: null,
        contact_champion: null,
        notes: null,
        tags: [],
        website_platform: null,
        // Intel fields
        yelp_rating: 0,
        yelp_reviews_count: 0,
        review_highlights: [],
        review_sentiment_score: 0,
        review_pain_points: [],
        review_opportunity_flags: [],
        bbb_url: '',
        bbb_rating: '',
        bbb_accredited: false,
        bbb_complaints: 0,
        bbb_summary: '',
        glassdoor_url: '',
        glassdoor_rating: 0,
        glassdoor_review_count: 0,
        glassdoor_summary: '',
        reddit_mentions: [],
        news_mentions: [],
        social_scan: {},
        deep_audit_results: null,
        deep_audit_score: null,
        deep_audit_grade: null,
        deep_audit_date: null,
      };
      setSelectedLead(partialLead);
      setIsDrawerOpen(true);
    }
  };

  const handleLeadUpdate = (updatedLead: LeadFull) => {
    setLeads(prevLeads =>
      prevLeads.map(lead =>
        lead.id === updatedLead.id
          ? {
              ...lead,
              outreach_status: updatedLead.outreach_status,
              contacted_by: updatedLead.contacted_by,
              contacted_at: updatedLead.contacted_at,
            }
          : lead
      )
    );
    setSelectedLead(updatedLead);
  };

  const closeDrawer = () => {
    setIsDrawerOpen(false);
    setSelectedLead(null);
  };

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

  // Refresh a specific search job (re-run the same search)
  const refreshSearchJob = async (jobId: number) => {
    try {
      // Get the original search params
      const resp = await authFetch(`${API}/api/leadgen/search/${jobId}`);
      if (!resp.ok) throw new Error("Failed to fetch search job");
      const job = await resp.json();

      // Start a new search with same params
      setQuery(job.query);
      // Try to parse "City, ST" format back into dropdowns
      const locationParts = (job.location as string).split(", ");
      if (locationParts.length === 2) {
        setSelectedState(locationParts[1]);
        setSelectedCity(locationParts[0]);
      }
      setSearching(true);
      setSearchStatus(`Refreshing: ${job.query} in ${job.location}...`);
      setErrorMessage(null);

      const searchResp = await authFetch(`${API}/api/leadgen/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: job.query,
          location: job.location,
          max_results: 60,
          radius_km: Math.round(radiusMiles * 1.60934),
        }),
      });

      if (!searchResp.ok) {
        const detail = await searchResp.text().catch(() => "");
        throw new Error(`Refresh failed (${searchResp.status}): ${detail}`);
      }

      const newJob = await searchResp.json();
      startSearchPolling(newJob.id, job.query, job.location);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to refresh search";
      setErrorMessage(msg);
      setSearching(false);
      setSearchStatus("");
    }
  };

  // Start polling for search job completion
  const startSearchPolling = (jobId: number, searchQuery: string, searchLocation: string) => {
    if (searchPollRef.current) clearInterval(searchPollRef.current);
    const poll = setInterval(async () => {
      try {
        const statusResp = await authFetch(`${API}/api/leadgen/search/${jobId}/status`);
        if (!statusResp.ok) {
          clearInterval(poll);
          setSearching(false);
          setErrorMessage(`Search status check failed (${statusResp.status})`);
          return;
        }
        const status: SearchJobStatus = await statusResp.json();
        setSearchStatus(status.message);

        if (status.status === "complete") {
          clearInterval(poll);
          setSearching(false);
          setActiveJobId(jobId);
          setShowAllLeads(false);
          setActiveJobAge(status.age_days);

          // Enrichment polling
          if (enrichmentPollRef.current) clearInterval(enrichmentPollRef.current);
          let enrichPollCount = 0;
          enrichmentPollRef.current = setInterval(() => {
            enrichPollCount++;
            if (enrichPollCount >= 12) {
              if (enrichmentPollRef.current) clearInterval(enrichmentPollRef.current);
              enrichmentPollRef.current = null;
            }
            loadLeads();
          }, 10000);
        } else if (status.status === "failed") {
          clearInterval(poll);
          setSearching(false);
          setErrorMessage(status.error_message || "Search failed — check server logs");
          setSearchStatus("");
        }
      } catch {
        clearInterval(poll);
        setSearching(false);
        setErrorMessage("Lost connection to server during search");
        setSearchStatus("");
      }
    }, 2000);
    searchPollRef.current = poll;
  };

  const searchBusinesses = async () => {
    const location = selectedCity && selectedState ? `${selectedCity}, ${selectedState}` : "";
    if (!location || !query.trim()) return;
    setSearching(true);
    setSearchStatus(`Searching for ${query} in ${location}...`);
    setErrorMessage(null);

    try {
      const resp = await authFetch(`${API}/api/leadgen/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          location,
          max_results: 60,
          radius_km: Math.round(radiusMiles * 1.60934),
        }),
      });

      if (!resp.ok) {
        const detail = await resp.text().catch(() => "");
        throw new Error(`Search request failed (${resp.status}): ${detail}`);
      }

      const job = await resp.json();
      startSearchPolling(job.id, query, location);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Network error — is the server running?";
      setErrorMessage(msg);
      setSearchStatus("");
      setSearching(false);
    }
  };

  const totalLabel = showAllLeads ? "All Leads" : "Search Results";

  const getLeadStatusClasses = (outreach_status: string) => {
    switch (outreach_status) {
      case "contacted": return { borderColorClass: "border-l-4 border-blue-500", backgroundClass: "" };
      case "in_progress": return { borderColorClass: "border-l-4 border-yellow-500", backgroundClass: "" };
      case "won": return { borderColorClass: "border-l-4 border-green-500", backgroundClass: "bg-green-500/5" };
      case "lost": return { borderColorClass: "border-l-4 border-red-500", backgroundClass: "opacity-60" };
      default: return { borderColorClass: "", backgroundClass: "" };
    }
  };

  const LeadStatusBadge = ({ lead }: { lead: Lead }) => (
    <>
      {lead.contacted_by && lead.contacted_at && (
        <p className="text-xs text-blue-400 mb-0.5">
          Contacted by {lead.contacted_by} · {new Date(lead.contacted_at).toLocaleDateString()}
        </p>
      )}
      {lead.enrichment_status === "pending" && lead.has_website && (
        <p className="text-xs text-yellow-400 mb-0.5">
          <Loader2 size={10} className="inline animate-spin mr-1" />
          Enriching...
        </p>
      )}
      {lead.enrichment_status === "failed" && (
        <p className="text-xs text-red-400 mb-0.5">
          <AlertTriangle size={10} className="inline mr-1" />
          Enrichment failed
        </p>
      )}
      {lead.enrichment_status === "pending" && !lead.has_website && (
        <p className="text-xs text-warroom-muted mb-0.5">No website</p>
      )}
    </>
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-3 sm:px-6 justify-between">
        <h2 className="text-sm font-semibold">Lead Generator</h2>
        <div className="flex items-center gap-3">
          {activeJobAge !== null && !showAllLeads && (
            <FreshnessBadge ageDays={activeJobAge} />
          )}
          <button onClick={loadLeads} disabled={searching} className="text-warroom-muted hover:text-warroom-text transition">
            <RefreshCw size={14} className={searching ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 sm:p-6">
        {/* Error banner */}
        {errorMessage && (
          <ErrorBanner message={errorMessage} onDismiss={dismissError} />
        )}

        {/* Search bar — stacks vertically on mobile */}
        <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 mb-2">
          <div className="flex gap-2 sm:gap-3">
            {/* State dropdown */}
            <div className="relative w-24 sm:w-32 shrink-0">
              <MapPin size={14} className="absolute left-2.5 sm:left-3 top-1/2 -translate-y-1/2 text-warroom-muted pointer-events-none" />
              <select
                value={selectedState}
                onChange={(e) => {
                  setSelectedState(e.target.value);
                  setSelectedCity("");
                }}
                className="w-full bg-warroom-surface border border-warroom-border rounded-lg pl-8 sm:pl-10 pr-6 sm:pr-8 py-2 sm:py-2.5 text-xs sm:text-sm text-warroom-text focus:outline-none focus:border-warroom-accent appearance-none cursor-pointer"
                style={{ colorScheme: "dark" }}
              >
                <option value="" disabled>State</option>
                {US_STATES.map((s) => (
                  <option key={s.abbr} value={s.abbr}>{s.abbr}</option>
                ))}
              </select>
              <svg className="absolute right-2 sm:right-3 top-1/2 -translate-y-1/2 text-warroom-muted pointer-events-none" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 4.5L6 7.5L9 4.5"/></svg>
            </div>

            {/* City autocomplete */}
            <div className="flex-1">
              <CityAutocomplete
                state={selectedState}
                value={selectedCity}
                onChange={setSelectedCity}
              />
            </div>
          </div>

          <div className="flex gap-2 sm:gap-3">
            {/* Business type dropdown */}
            <div className="relative flex-1">
              <Building2 size={14} className="absolute left-2.5 sm:left-3 top-1/2 -translate-y-1/2 text-warroom-muted pointer-events-none" />
              <select
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full bg-warroom-surface border border-warroom-border rounded-lg pl-8 sm:pl-10 pr-6 sm:pr-8 py-2 sm:py-2.5 text-xs sm:text-sm text-warroom-text focus:outline-none focus:border-warroom-accent appearance-none cursor-pointer"
                style={{ colorScheme: "dark" }}
              >
                <option value="" disabled>Business type...</option>
                {BUSINESS_CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
              <svg className="absolute right-2 sm:right-3 top-1/2 -translate-y-1/2 text-warroom-muted pointer-events-none" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 4.5L6 7.5L9 4.5"/></svg>
            </div>

            {/* Search / Cancel button */}
            {searching ? (
              <button
                onClick={cancelSearch}
                className="px-4 sm:px-6 py-2 sm:py-2.5 bg-red-600 hover:bg-red-500 rounded-lg text-xs sm:text-sm font-medium transition flex items-center gap-1.5 sm:gap-2 text-white shrink-0"
              >
                <X size={14} />
                <span className="hidden sm:inline">Cancel</span>
              </button>
            ) : (
              <button
                onClick={searchBusinesses}
                disabled={!selectedState || !selectedCity || !query.trim()}
                className="px-4 sm:px-6 py-2 sm:py-2.5 bg-warroom-accent rounded-lg text-xs sm:text-sm font-medium hover:bg-warroom-accent/80 disabled:opacity-50 transition flex items-center gap-1.5 sm:gap-2 shrink-0"
              >
                <Search size={14} />
                <span className="hidden sm:inline">Search</span>
              </button>
            )}
          </div>
        </div>

        {/* Radius selector */}
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs text-warroom-muted">Radius:</span>
          <select
            value={radiusMiles}
            onChange={(e) => setRadiusMiles(Number(e.target.value))}
            className="bg-warroom-surface border border-warroom-border rounded-lg px-2 py-1 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent appearance-none cursor-pointer"
            style={{ colorScheme: "dark" }}
          >
            <option value={10}>10 mi</option>
            <option value={25}>25 mi</option>
            <option value={50}>50 mi</option>
            <option value={75}>75 mi</option>
            <option value={100}>100 mi</option>
          </select>
        </div>

        {/* Status + filters bar */}
        <div className="space-y-2 sm:space-y-3 mb-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-3">
              {searchStatus && (
                <p className="text-xs text-warroom-muted truncate">{searchStatus}</p>
              )}
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {activeJobId && (
                <>
                  <button
                    onClick={() => refreshSearchJob(activeJobId)}
                    disabled={searching}
                    className="px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 bg-warroom-border/50 text-warroom-muted hover:text-warroom-text disabled:opacity-50"
                    title="Re-run this search with fresh data"
                  >
                    🔄 <span className="hidden sm:inline">Refresh</span>
                  </button>
                  <button
                    onClick={() => setShowAllLeads(!showAllLeads)}
                    className={`px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
                      showAllLeads
                        ? "bg-warroom-border/50 text-warroom-muted hover:text-warroom-text"
                        : "bg-warroom-accent/20 text-warroom-accent"
                    }`}
                  >
                    <Filter size={12} />
                    <span className="hidden sm:inline">{showAllLeads ? "Show Search Results" : "Show All Leads"}</span>
                    <span className="sm:hidden">{showAllLeads ? "Results" : "All"}</span>
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Current / Historical tabs */}
          <div className="flex items-center gap-1 mb-1">
            <button
              onClick={() => setViewTab("current")}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition ${
                viewTab === "current"
                  ? "bg-warroom-accent/20 text-warroom-accent"
                  : "text-warroom-muted hover:text-warroom-text"
              }`}
            >
              Current
            </button>
            <button
              onClick={() => setViewTab("historical")}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition ${
                viewTab === "historical"
                  ? "bg-warroom-accent/20 text-warroom-accent"
                  : "text-warroom-muted hover:text-warroom-text"
              }`}
            >
              Historical
            </button>
          </div>

          {/* Filter row */}
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
            <div className="text-xs text-warroom-muted font-medium">Filters:</div>

            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="bg-warroom-surface border border-warroom-border rounded-lg px-2 sm:px-3 py-1.5 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent appearance-none cursor-pointer"
              style={{ colorScheme: "dark" }}
            >
              <option value="">All</option>
              <option value="none">Not Contacted</option>
              <option value="contacted">Contacted</option>
              <option value="in_progress">In Progress</option>
              <option value="won">Won</option>
              <option value="lost">Lost</option>
            </select>

            <select
              value={filterTier}
              onChange={(e) => setFilterTier(e.target.value)}
              className="bg-warroom-surface border border-warroom-border rounded-lg px-2 sm:px-3 py-1.5 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent appearance-none cursor-pointer"
              style={{ colorScheme: "dark" }}
            >
              <option value="">All Tiers</option>
              <option value="hot">🔥 Hot</option>
              <option value="warm">🟠 Warm</option>
              <option value="cold">🔵 Cold</option>
            </select>

            <select
              value={filterWebsite}
              onChange={(e) => setFilterWebsite(e.target.value)}
              className="bg-warroom-surface border border-warroom-border rounded-lg px-2 sm:px-3 py-1.5 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent appearance-none cursor-pointer"
              style={{ colorScheme: "dark" }}
            >
              <option value="">All Leads</option>
              <option value="true">🌐 Has Website</option>
              <option value="false">❌ No Website</option>
            </select>

            {(filterStatus || filterTier || filterWebsite) && (
              <button
                onClick={() => {
                  setFilterStatus("");
                  setFilterTier("");
                  setFilterWebsite("");
                }}
                className="text-[10px] text-warroom-muted hover:text-warroom-text flex items-center gap-1 transition"
              >
                <X size={10} /> Clear
              </button>
            )}
          </div>
        </div>

        {/* Results */}
        {leads.length > 0 && (
          <div className="bg-warroom-surface border border-warroom-border rounded-lg overflow-hidden">
            <div className="px-3 sm:px-4 py-2 border-b border-warroom-border flex items-center justify-between">
              <span className="text-xs text-warroom-muted">
                {totalLabel} · {leads.length}{hasMore ? "+" : ""}
              </span>
              <div className="flex items-center gap-3">
                {activeJobAge !== null && !showAllLeads && (
                  <FreshnessBadge ageDays={activeJobAge} />
                )}
                {!showAllLeads && activeJobId && (
                  <button
                    onClick={() => { setShowAllLeads(true); setActiveJobId(null); setSearchStatus(""); setActiveJobAge(null); }}
                    className="text-[10px] text-warroom-muted hover:text-warroom-text flex items-center gap-1 transition"
                  >
                    <X size={10} /> Clear
                  </button>
                )}
              </div>
            </div>

            {/* Desktop table — hidden on mobile */}
            <table className="w-full text-sm hidden sm:table">
              <thead>
                <tr className="border-b border-warroom-border">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Business</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Contact</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Website</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Score</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => {
                  const { borderColorClass, backgroundClass } = getLeadStatusClasses(lead.outreach_status);
                  return (
                    <tr
                      key={lead.id}
                      className={`group border-b border-warroom-border/50 hover:bg-warroom-border/20 cursor-pointer ${borderColorClass} ${backgroundClass}`}
                      onClick={() => handleLeadClick(lead)}
                    >
                      <td className="px-4 py-3">
                        <p className="font-medium">{lead.business_name}</p>
                        <LeadStatusBadge lead={lead} />
                        <p className="text-xs text-warroom-muted">{[lead.city, lead.state].filter(Boolean).join(", ") || lead.address}</p>
                        {lead.business_category && (
                          <p className="text-[10px] text-warroom-muted/70 mt-0.5">{lead.business_category.replace(/_/g, " ")}</p>
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
                          <a href={lead.website} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-warroom-accent hover:underline" onClick={(e) => e.stopPropagation()}>
                            <Globe size={10} /> {(() => { try { return new URL(lead.website).hostname; } catch { return lead.website; } })()}
                          </a>
                        ) : (
                          <span className="text-xs text-warroom-danger">No website</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="flex flex-col gap-1">
                            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full w-fit ${TIER_COLORS[lead.lead_tier] || TIER_COLORS.unscored}`}>
                              {lead.lead_tier}
                            </span>
                            <span className="text-xs text-warroom-muted">{lead.lead_score}/100</span>
                          </div>
                          <button
                            onClick={(e) => startPipeline(lead, e)}
                            title="Start Pipeline"
                            className="p-1.5 rounded-md text-warroom-muted hover:text-warroom-accent hover:bg-warroom-accent/10 transition opacity-0 group-hover:opacity-100"
                          >
                            <Rocket size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Mobile card list — hidden on desktop */}
            <div className="sm:hidden divide-y divide-warroom-border/50">
              {leads.map((lead) => {
                const { borderColorClass, backgroundClass } = getLeadStatusClasses(lead.outreach_status);
                return (
                  <div
                    key={lead.id}
                    className={`p-3 active:bg-warroom-border/30 cursor-pointer ${borderColorClass} ${backgroundClass}`}
                    onClick={() => handleLeadClick(lead)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-sm truncate">{lead.business_name}</p>
                        <LeadStatusBadge lead={lead} />
                        <p className="text-xs text-warroom-muted">{[lead.city, lead.state].filter(Boolean).join(", ")}</p>
                      </div>
                      <div className="flex flex-col items-end gap-1 shrink-0">
                        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${TIER_COLORS[lead.lead_tier] || TIER_COLORS.unscored}`}>
                          {lead.lead_tier}
                        </span>
                        <span className="text-[10px] text-warroom-muted">{lead.lead_score}/100</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                      {lead.phone && (
                        <span className="flex items-center gap-1 text-[11px] text-warroom-muted">
                          <Phone size={9} /> {lead.phone}
                        </span>
                      )}
                      {lead.google_rating && (
                        <span className="flex items-center gap-1 text-[11px] text-warroom-muted">
                          <Star size={9} /> {lead.google_rating}
                        </span>
                      )}
                      {lead.website ? (
                        <span className="flex items-center gap-1 text-[11px] text-warroom-accent">
                          <Globe size={9} /> Site
                        </span>
                      ) : (
                        <span className="text-[11px] text-red-400">No site</span>
                      )}
                      {lead.website_audit_grade && (
                        <span className="text-[10px] text-warroom-muted bg-warroom-border/50 px-1 rounded">
                          {lead.website_audit_grade}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

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

        {/* No results state */}
        {leads.length === 0 && !searching && !initialLoading && !errorMessage && (
          <EmptyState
            icon={<Search size={40} />}
            title="No leads found"
            description={
              activeJobId && !showAllLeads
                ? "This search returned no results. Try a different business category or broader location."
                : "Search for businesses to start building your pipeline."
            }
            action={
              activeJobId && !showAllLeads
                ? { label: "Show All Leads", onClick: () => { setShowAllLeads(true); setActiveJobId(null); } }
                : undefined
            }
          />
        )}

        {initialLoading && (
          <LoadingState message="Loading leads..." />
        )}
      </div>

      {/* Lead Drawer */}
      <LeadDrawer
        lead={selectedLead}
        isOpen={isDrawerOpen}
        onClose={closeDrawer}
        onUpdate={handleLeadUpdate}
      />

      {/* Pipeline Toast */}
      {pipelineToast && (
        <div className={`fixed bottom-6 right-6 z-[60] px-4 py-3 rounded-lg shadow-lg text-sm font-medium flex items-center gap-2 animate-in slide-in-from-bottom-2 ${
          pipelineToast.type === "success"
            ? "bg-green-600/90 text-white"
            : "bg-red-600/90 text-white"
        }`}>
          {pipelineToast.message}
          <button onClick={() => setPipelineToast(null)} className="ml-2 opacity-70 hover:opacity-100">
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
