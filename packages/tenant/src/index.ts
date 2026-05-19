import type { TenantConfig } from './types'
import { sage } from './configs/sage'

const configs: Record<string, TenantConfig> = { sage }

const tenantKey = process.env.NEXT_PUBLIC_TENANT ?? 'sage'
const resolved = configs[tenantKey]

if (!resolved) {
  throw new Error(`Unknown tenant: "${tenantKey}". Add it to packages/tenant/src/configs/.`)
}

export const tenant: TenantConfig = resolved
export type { TenantConfig, TenantBrand, TenantCapabilities, TenantCopy } from './types'
