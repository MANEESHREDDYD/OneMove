import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
