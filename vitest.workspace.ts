import { defineWorkspace } from 'vitest/config'

export default defineWorkspace([
  'apps/web/vitest.config.ts',
  'packages/ui/vitest.config.ts',
  'packages/theme/vitest.config.ts',
  'packages/types/vitest.config.ts',
])
