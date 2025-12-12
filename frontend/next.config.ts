import type { NextConfig } from "next";

const backendApiBaseUrl =
  process.env.BACKEND_API_BASE_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendApiBaseUrl}/api/:path*`,
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
        pathname: "/conversations/files/**",
      },
      {
        protocol: "https",
        hostname: "*.railway.app",
        pathname: "/conversations/files/**",
      },
    ],
  },
};

export default nextConfig;
