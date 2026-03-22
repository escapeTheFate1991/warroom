/**
 * Base URL for API requests.
 *
 * Set to "" (empty) so all fetch("/api/...") calls use relative paths.
 * The Next.js rewrite in next.config.js proxies /api/* to the backend,
 * making the app work from any device (LAN, warroom.stuffnthings.io, etc.)
 * without hardcoding a backend IP.
 */
export const API = process.env.NEXT_PUBLIC_API_URL || "";

import { refreshToken, clearAuthData } from "@/lib/auth";

/**
 * Promise-based lock for token refresh.
 * When a 401 triggers a refresh, subsequent 401s wait on the same promise
 * instead of firing concurrent refresh requests.
 */
let refreshPromise: Promise<string | null> | null = null;

/**
 * Authenticated fetch wrapper. Automatically injects the JWT Bearer token
 * from localStorage into every request. Falls back to regular fetch if
 * no token is stored (public endpoints).
 *
 * On 401 responses, attempts a single token refresh and retries the
 * original request. If refresh fails, clears auth data and redirects
 * to /login.
 */
export async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = typeof window !== "undefined" ? localStorage.getItem("warroom_token") : null;

  const buildHeaders = (authToken: string | null): Record<string, string> => {
    // Normalize headers to a plain object regardless of input type
    const incoming = options.headers ?? {};
    const normalized: Record<string, string> =
      incoming instanceof Headers
        ? Object.fromEntries(incoming.entries())
        : Array.isArray(incoming)
          ? Object.fromEntries(incoming)
          : { ...(incoming as Record<string, string>) };

    if (authToken) {
      normalized["Authorization"] = `Bearer ${authToken}`;
    }
    // Only set Content-Type for non-FormData bodies
    if (options.body && !(options.body instanceof FormData) && !normalized["Content-Type"]) {
      normalized["Content-Type"] = "application/json";
    }
    return normalized;
  };

  const response = await fetch(url, { ...options, headers: buildHeaders(token) });

  // If not a 401 or no token was sent, return as-is
  if (response.status !== 401 || !token) {
    return response;
  }

  // 401 with a token — attempt refresh (once)
  // Use a shared promise so concurrent 401s don't fire multiple refreshes
  if (!refreshPromise) {
    refreshPromise = refreshToken().finally(() => {
      refreshPromise = null;
    });
  }

  const newToken = await refreshPromise;

  if (!newToken) {
    // Refresh failed — clear auth and redirect to login
    clearAuthData();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    return response;
  }

  // Retry the original request with the new token
  return fetch(url, { ...options, headers: buildHeaders(newToken) });
}
