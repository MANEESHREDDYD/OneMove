import type { NextConfig } from "next";

const ONEMOVE_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

const nextConfig: NextConfig = {
  // Browser code calls /api/v1/* as a same-origin path, which previously hit the
  // Next.js server (404) and surfaced as "Failed to load network topology" over an
  // empty map. Proxying to the OneMove API keeps the browser same-origin while the
  // data comes from the real service.
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${ONEMOVE_API_URL}/api/v1/:path*`,
      },
    ];
  },
  async redirects() {
    return [
      {
        source: '/driver',
        destination: '/partner',
        permanent: true,
      },
      {
        source: '/admin/ai-lab',
        destination: '/admin/ml-lab',
        permanent: true,
      },
    ]
  },
};

export default nextConfig;
