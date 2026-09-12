import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The contracts workspace package ships TypeScript source.
  transpilePackages: ["@visual-learning/contracts"],
};

export default nextConfig;
