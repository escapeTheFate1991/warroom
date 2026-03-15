/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    // Backend runs on host network (port 8300). Frontend container uses
    // bridge networking so we need the host's LAN IP to reach it.
    // This is a build-time value — if NEXT_PUBLIC_API_URL is empty (for
    // client-side relative paths), fall back to a hard backend URL.
    const backendUrl = process.env.REWRITE_BACKEND_URL || "http://10.0.0.1:8300";
    return [
      {
        // Proxy all /api/* through the frontend domain so OAuth callbacks
        // (Google Calendar, social platforms) and REST calls work via
        // warroom.stuffnthings.io without hitting the auth gate.
        // Extended timeout for content-intel endpoints (scraping operations)
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
  // Configure proxy timeout for slow content-intel endpoints
  experimental: {
    proxyTimeout: 120000, // 2 minutes for scraping operations
  },
};
module.exports = nextConfig;
