// apps/web/next.config.ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  transpilePackages: ['@cdai/ui', '@cdai/theme', '@cdai/tenant', '@cdai/types'],
}

export default nextConfig
