import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Hides the Next.js dev overlay indicator (bottom-left "N") in development.
  // `buildActivity` was removed in Next 15; `false` disables the indicator entirely.
  devIndicators: false,
};

export default nextConfig;
