import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  // Vercel Services does not expose Next's image optimizer route reliably;
  // serve committed local assets directly instead.
  images: { unoptimized: true },
  // Next 16 blocks dev-only assets from unknown hosts; allow the ngrok tunnel
  // used for remote demos while keeping the restriction in production.
  allowedDevOrigins: ["*.ngrok-free.dev", "*.ngrok.io"],
};

export default nextConfig;
