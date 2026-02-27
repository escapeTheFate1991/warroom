"use client";

import { useState, useEffect, useRef, useCallback } from "react";

interface ContentLoaderOptions<T> {
  /** Fetch function — receives page number, returns items */
  fetchFn: (page: number, pageSize: number) => Promise<T[]>;
  /** Items per page */
  pageSize?: number;
  /** How many pages ahead to prefetch (warm area) */
  prefetchAhead?: number;
  /** Enable infinite scroll (auto-load on scroll) */
  infinite?: boolean;
  /** Initial fetch on mount */
  autoLoad?: boolean;
}

interface ContentLoaderResult<T> {
  items: T[];
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  error: string | null;
  /** Ref to attach to the sentinel element at the bottom */
  sentinelRef: (node: HTMLDivElement | null) => void;
  /** Manually load next page */
  loadMore: () => void;
  /** Reset and reload from page 1 */
  refresh: () => void;
  /** Total pages loaded */
  page: number;
}

export function useContentLoader<T>(options: ContentLoaderOptions<T>): ContentLoaderResult<T> {
  const {
    fetchFn,
    pageSize = 20,
    prefetchAhead = 3,
    infinite = true,
    autoLoad = true,
  } = options;

  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);

  // Prefetch cache: stores next N pages
  const prefetchCache = useRef<Map<number, T[]>>(new Map());
  const isFetching = useRef(false);

  const fetchPage = useCallback(
    async (pageNum: number): Promise<T[]> => {
      // Check cache first
      const cached = prefetchCache.current.get(pageNum);
      if (cached) {
        prefetchCache.current.delete(pageNum);
        return cached;
      }
      return fetchFn(pageNum, pageSize);
    },
    [fetchFn, pageSize]
  );

  // Prefetch upcoming pages in background
  const prefetch = useCallback(
    async (currentPage: number) => {
      for (let i = 1; i <= prefetchAhead; i++) {
        const targetPage = currentPage + i;
        if (prefetchCache.current.has(targetPage)) continue;
        try {
          const data = await fetchFn(targetPage, pageSize);
          if (data.length > 0) {
            prefetchCache.current.set(targetPage, data);
          }
        } catch {
          // Silent prefetch failure is fine
        }
      }
    },
    [fetchFn, pageSize, prefetchAhead]
  );

  const loadMore = useCallback(async () => {
    if (isFetching.current || !hasMore) return;
    isFetching.current = true;

    const nextPage = page + 1;
    const isFirst = nextPage === 1;

    if (isFirst) setLoading(true);
    else setLoadingMore(true);

    try {
      const data = await fetchPage(nextPage);
      if (data.length < pageSize) setHasMore(false);
      if (data.length === 0) {
        setHasMore(false);
      } else {
        setItems((prev) => (isFirst ? data : [...prev, ...data]));
        setPage(nextPage);
        // Start prefetching next pages
        prefetch(nextPage);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load content");
    } finally {
      setLoading(false);
      setLoadingMore(false);
      isFetching.current = false;
    }
  }, [page, hasMore, fetchPage, pageSize, prefetch]);

  const refresh = useCallback(() => {
    setItems([]);
    setPage(0);
    setHasMore(true);
    setError(null);
    prefetchCache.current.clear();
    isFetching.current = false;
  }, []);

  // Auto-load first page
  useEffect(() => {
    if (autoLoad && page === 0 && items.length === 0 && hasMore) {
      loadMore();
    }
  }, [autoLoad, page, items.length, hasMore, loadMore]);

  // Re-trigger load after refresh resets state
  useEffect(() => {
    if (page === 0 && items.length === 0 && hasMore && autoLoad) {
      loadMore();
    }
  }, [page, items.length, hasMore, autoLoad, loadMore]);

  // Intersection Observer for infinite scroll
  const sentinelRef = useCallback(
    (node: HTMLDivElement | null) => {
      if (!node || !infinite) return;

      const observer = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting && hasMore && !isFetching.current) {
            loadMore();
          }
        },
        { rootMargin: "400px" } // Start loading 400px before reaching bottom
      );

      observer.observe(node);
      return () => observer.disconnect();
    },
    [infinite, hasMore, loadMore]
  );

  return {
    items,
    loading,
    loadingMore,
    hasMore,
    error,
    sentinelRef,
    loadMore,
    refresh,
    page,
  };
}

/** Skeleton loader component for consistent loading states */
export function ContentSkeleton({ rows = 3, className = "" }: { rows?: number; className?: string }) {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="bg-warroom-surface border border-warroom-border rounded-lg p-4 animate-pulse">
          <div className="flex gap-3">
            <div className="w-10 h-10 bg-warroom-border rounded-lg" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-warroom-border rounded w-3/4" />
              <div className="h-3 bg-warroom-border rounded w-1/2" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/** Grid skeleton for card layouts */
export function GridSkeleton({ cards = 6, className = "" }: { cards?: number; className?: string }) {
  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 ${className}`}>
      {Array.from({ length: cards }).map((_, i) => (
        <div key={i} className="bg-warroom-surface border border-warroom-border rounded-lg overflow-hidden animate-pulse">
          <div className="h-36 bg-warroom-border" />
          <div className="p-3 space-y-2">
            <div className="h-4 bg-warroom-border rounded w-3/4" />
            <div className="h-3 bg-warroom-border rounded w-1/2" />
            <div className="h-3 bg-warroom-border rounded w-1/3" />
          </div>
        </div>
      ))}
    </div>
  );
}
