import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  // Produce a standalone build output in `.next/standalone`
  output: "standalone",
};

export default nextConfig;
