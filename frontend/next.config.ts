// frontend\next.config.ts

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  output: "standalone", // Включаем режим минимального билда
};

export default nextConfig;