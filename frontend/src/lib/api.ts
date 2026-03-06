/**
 * Base URL for API requests.
 *
 * Set to "" (empty) so all fetch("/api/...") calls use relative paths.
 * The Next.js rewrite in next.config.js proxies /api/* to the backend,
 * making the app work from any device (LAN, warroom.stuffnthings.io, etc.)
 * without hardcoding a backend IP.
 */
export const API = process.env.NEXT_PUBLIC_API_URL || "";

/**
 * Authenticated fetch wrapper. Automatically injects the JWT Bearer token
 * from localStorage into every request. Falls back to regular fetch if
 * no token is stored (public endpoints).
 */
export function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = typeof window !== "undefined" ? localStorage.getItem("warroom_token") : null;
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  // Only set Content-Type for non-FormData bodies
  if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  return fetch(url, { ...options, headers });
}
