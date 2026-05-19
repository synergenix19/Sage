// apps/web/tailwind.config.ts
// Using Tailwind CSS v3 for compatibility with @cdai/theme which declares tailwindPreset
// as Partial<Config> from tailwindcss v3. Tailwind v4 changed the config contract
// (no more tailwind.config.ts / presets API), so v3 is the correct choice here.
import type { Config } from 'tailwindcss'
import { tailwindPreset } from '@cdai/theme'

const config: Config = {
  presets: [tailwindPreset as Config],
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    '../../packages/ui/src/**/*.{ts,tsx}',
  ],
}

export default config
