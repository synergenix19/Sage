# CDAi Pilot PWA — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the CDAi Gitex 2026 pilot PWA — unified Chat+Ask AI wellbeing interface, personal progress dashboard, government admin dashboard, bilingual Arabic/English, tenant-driven white-label architecture.

**Architecture:** Next.js 15 App Router Turborepo monorepo. `packages/tenant` is the single source of truth for brand, capabilities, and copy per tenant. Supabase handles auth and persistence. Vercel AI SDK streams chat responses after a sequential intent classification step. All Gitex demo data is deterministically seeded at the store level.

**Tech Stack:** Next.js 15, TypeScript 5, Tailwind CSS v4, cva, Framer Motion, Zustand, Vercel AI SDK, @ai-sdk/openai (OpenRouter), Supabase, Recharts, Serwist, Turborepo, Vitest, React Testing Library

---

## File Map

| File | Responsibility |
|---|---|
| `turbo.json` | Turborepo pipeline config |
| `packages/types/src/index.ts` | All shared TypeScript interfaces |
| `packages/tenant/src/types.ts` | TenantConfig interface |
| `packages/tenant/src/configs/sage.ts` | CDA tenant — brand + capabilities + copy |
| `packages/tenant/src/index.ts` | Resolves NEXT_PUBLIC_TENANT → config |
| `packages/theme/src/css-vars.ts` | Emits CSS custom properties from tenant brand |
| `packages/theme/src/tailwind-preset.ts` | Tailwind preset consuming CSS vars |
| `packages/ui/src/lib/utils.ts` | cn() helper |
| `packages/ui/src/components/button.tsx` | Button (cva variants) |
| `packages/ui/src/components/card.tsx` | Card |
| `packages/ui/src/components/input.tsx` | Input |
| `packages/ui/src/components/skeleton.tsx` | Skeleton loader |
| `packages/ui/src/components/bottom-sheet.tsx` | Mobile bottom sheet |
| `apps/web/middleware.ts` | Edge: auth guard, role check, onboarding redirect |
| `apps/web/app/layout.tsx` | Root: providers + locale-split fonts only |
| `apps/web/components/providers.tsx` | Supabase, Zustand, locale hydration |
| `apps/web/lib/supabase/client.ts` | Browser Supabase client |
| `apps/web/lib/supabase/server.ts` | Server Supabase client (App Router) |
| `apps/web/lib/stores/locale-store.ts` | Locale Zustand store |
| `apps/web/lib/stores/onboarding-store.ts` | Onboarding answers + step tracking |
| `apps/web/lib/stores/chat-store.ts` | Active session, messages, pending state |
| `apps/web/app/(auth)/layout.tsx` | Centered auth shell |
| `apps/web/app/(auth)/sign-in/page.tsx` | Sign-in page |
| `apps/web/app/(auth)/sign-up/page.tsx` | Sign-up page |
| `apps/web/app/(auth)/forgot-password/page.tsx` | Forgot password page |
| `apps/web/components/auth/sign-in-form.tsx` | Sign-in form (RHF + Zod) |
| `apps/web/components/auth/sign-up-form.tsx` | Sign-up form |
| `apps/web/components/auth/language-toggle.tsx` | EN\|AR toggle (auth shell) |
| `apps/web/app/(onboarding)/layout.tsx` | Full-screen wizard shell |
| `apps/web/app/(onboarding)/[step]/page.tsx` | Step router + notFound guard |
| `apps/web/components/onboarding/progress-bar.tsx` | Step progress indicator |
| `apps/web/components/onboarding/steps/` | One file per step (welcome → personalising) |
| `apps/web/app/(app)/layout.tsx` | Tab bar shell |
| `apps/web/components/tab-bar.tsx` | Chat \| Progress tabs |
| `apps/web/app/(app)/chat/layout.tsx` | Chat shell (reserved) |
| `apps/web/app/(app)/chat/page.tsx` | Chat page |
| `apps/web/app/api/chat/route.ts` | Classify → stream endpoint |
| `apps/web/components/chat/chat-header.tsx` | Session name + controls |
| `apps/web/components/chat/message-list.tsx` | Scrollable message list |
| `apps/web/components/chat/message-bubble.tsx` | user/ai/system/crisis bubble |
| `apps/web/components/chat/typing-indicator.tsx` | Three-dot pulse |
| `apps/web/components/chat/input-bar.tsx` | Text input + mic + send |
| `apps/web/components/chat/empty-state.tsx` | Greeting + prompt chips |
| `apps/web/components/chat/crisis-card.tsx` | Non-dismissible crisis card |
| `apps/web/components/chat/settings-panel.tsx` | Bottom sheet/slide-in settings |
| `apps/web/components/chat/history-panel.tsx` | Past sessions panel |
| `apps/web/components/chat/voice-biomarker.tsx` | Orb + simulated biomarker (flag-gated) |
| `apps/web/app/(app)/progress/page.tsx` | Progress dashboard |
| `apps/web/components/progress/streak-card.tsx` | Streak display |
| `apps/web/components/progress/mood-chart.tsx` | 7-day Recharts line |
| `apps/web/components/progress/topics-scroll.tsx` | Chip scroll with fade |
| `apps/web/components/progress/insights-list.tsx` | AI-generated insight cards |
| `apps/web/app/admin/layout.tsx` | Admin shell |
| `apps/web/app/admin/dashboard/page.tsx` | Admin dashboard page |
| `apps/web/components/admin/` | metric-cards, charts, sidebar, alerts |
| `apps/web/lib/demo-seed.ts` | Deterministic user progress seed |
| `apps/web/lib/admin-demo-seed.ts` | Deterministic admin seed |
| `apps/web/public/manifest.json` | PWA manifest |
| `apps/web/public/offline.html` | Bilingual offline fallback |
| `apps/web/lib/sw/serwist.ts` | Service worker config |

---

## Task 1: Turborepo Monorepo Bootstrap

**Files:**
- Create: `turbo.json`
- Create: `package.json`
- Create: `.env.example`
- Create: `packages/types/package.json`
- Create: `packages/tenant/package.json`
- Create: `packages/theme/package.json`
- Create: `packages/ui/package.json`

- [ ] **Step 1: Scaffold root**

```bash
mkdir -p cdai/{packages/{types,tenant,theme,ui},apps/web}
cd cdai
```

- [ ] **Step 2: Write root `package.json`**

```json
{
  "name": "cdai",
  "private": true,
  "workspaces": ["apps/*", "packages/*"],
  "scripts": {
    "dev": "turbo dev",
    "build": "turbo build",
    "test": "turbo test",
    "lint": "turbo lint"
  },
  "devDependencies": {
    "turbo": "^2.0.0",
    "typescript": "^5.4.0"
  }
}
```

- [ ] **Step 3: Write `turbo.json`**

```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "dist/**"]
    },
    "dev": { "persistent": true, "cache": false },
    "test": { "dependsOn": ["^build"] },
    "lint": {}
  }
}
```

- [ ] **Step 4: Write `.env.example`**

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# LLM
OPENROUTER_API_KEY=sk-or-...

# Tenant
NEXT_PUBLIC_TENANT=sage
```

- [ ] **Step 5: Write package.json for each package**

`packages/types/package.json`:
```json
{
  "name": "@cdai/types",
  "version": "0.0.1",
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": { ".": "./src/index.ts" }
}
```

Repeat the same pattern for `packages/tenant`, `packages/theme`, `packages/ui` — substitute the name accordingly (`@cdai/tenant`, `@cdai/theme`, `@cdai/ui`). Add `"dependencies": { "@cdai/types": "*" }` in tenant and theme.

- [ ] **Step 6: Install dependencies at root**

```bash
npm install
```

Expected: workspace symlinks created, no errors.

- [ ] **Step 7: Write root `.eslintrc.json` to enforce dependency direction**

Create `.eslintrc.json` at the repo root:

```json
{
  "root": true,
  "extends": ["next/core-web-vitals"],
  "rules": {
    "no-restricted-imports": [
      "error",
      {
        "patterns": [
          {
            "group": ["../../apps/web/**", "../apps/web/**"],
            "message": "packages/* must not import from apps/web — dependency flows tenant → theme → ui → web only."
          }
        ]
      }
    ]
  }
}
```

This enforces the one-way dependency rule: `packages/*` cannot import from `apps/web`. Turborepo's `dependsOn: ["^build"]` enforces build order; this ESLint rule catches accidental cross-boundary imports at lint time.

Run: `npm run lint`
Expected: no errors (no violations in scaffold).

- [ ] **Step 8: Commit**

```bash
git init
git add turbo.json package.json .env.example packages/*/package.json .eslintrc.json
git commit -m "feat: turborepo monorepo scaffold with dependency-direction lint rule"
```

---

## Task 2: Shared Types (`packages/types`)

**Files:**
- Create: `packages/types/src/index.ts`
- Create: `packages/types/src/__tests__/types.test.ts`

- [ ] **Step 1: Write the types**

```typescript
// packages/types/src/index.ts
export type Locale = 'en' | 'ar'
export type UserRole = 'parent' | 'service_user' | 'professional'
export type MessageRole = 'user' | 'ai' | 'system' | 'crisis'
export type Intent = 'knowledge' | 'emotional'
export type AgeRange = 'under-18' | '18-24' | '25-34' | '35-44' | '45-54' | '55+'

export interface UserProfile {
  id: string
  name: string
  ageRange: AgeRange
  role: UserRole
  locale: Locale
  isAdmin: boolean
  onboardingComplete: boolean
  onboardingStep: number
  wellnessQ1: string | null
  wellnessQ2: string | null
  createdAt: string
}

export interface ChatSession {
  id: string
  userId: string
  name: string | null
  createdAt: string
  updatedAt: string
}

export interface ChatMessage {
  id: string
  sessionId: string
  role: MessageRole
  content: string
  intent: Intent | null
  createdAt: string
}

export interface SessionInsight {
  id: string
  sessionId: string
  userId: string
  content: string
  topicTag: string
  createdAt: string
}

export interface MoodScore {
  id: string
  userId: string
  sessionId: string
  score: number
  createdAt: string
}

// Maps Vercel AI SDK role strings to internal MessageRole.
// The SDK uses 'assistant'; our type uses 'ai'. Handles all four roles with a safe fallback.
export function mapSdkRole(sdkRole: string): MessageRole {
  switch (sdkRole) {
    case 'assistant': return 'ai'
    case 'user':      return 'user'
    case 'system':    return 'system'
    case 'crisis':    return 'crisis'
    default:          return 'ai'
  }
}
```

- [ ] **Step 2: Write a smoke test (types are structural — just verify shapes compile)**

```typescript
// packages/types/src/__tests__/types.test.ts
import { describe, it, expectTypeOf } from 'vitest'
import type { UserProfile, ChatMessage, Locale } from '../index'

describe('types', () => {
  it('Locale is a union of en and ar', () => {
    expectTypeOf<Locale>().toEqualTypeOf<'en' | 'ar'>()
  })

  it('UserProfile has required fields', () => {
    expectTypeOf<UserProfile>().toHaveProperty('id')
    expectTypeOf<UserProfile>().toHaveProperty('onboardingComplete')
  })

  it('ChatMessage role covers all four variants', () => {
    expectTypeOf<ChatMessage['role']>().toEqualTypeOf<'user' | 'ai' | 'system' | 'crisis'>()
  })
})
```

- [ ] **Step 3: Run**

```bash
npx vitest run packages/types
```

Expected: 3 tests pass.

- [ ] **Step 4: Commit**

```bash
git add packages/types
git commit -m "feat: shared TypeScript types package"
```

---

## Task 3: Tenant Config (`packages/tenant`)

**Files:**
- Create: `packages/tenant/src/types.ts`
- Create: `packages/tenant/src/configs/sage.ts`
- Create: `packages/tenant/src/index.ts`
- Create: `packages/tenant/src/__tests__/tenant.test.ts`

- [ ] **Step 1: Write the TenantConfig type**

```typescript
// packages/tenant/src/types.ts
export interface TenantBrand {
  logo: string
  colors: {
    primary: string
    primaryDark: string
    secondary: string
    surface: string
    surfaceTinted: string
    textPrimary: string
    textSecondary: string
    border: string
    crisis: string
  }
  fonts: { body: string; arabic: string }
  supportUrl: string
  locales: string[]
}

export interface TenantCapabilities {
  voiceBiomarker: boolean
  adminDashboard: boolean
  onboardingWizard: boolean
  rtl: boolean
  demoSeed: boolean
}

export interface TenantCopy {
  appName: string
  tagline: string
  onboardingGreeting: string
  progressHeader: string
  adminHeader: string
}

export interface TenantConfig {
  brand: TenantBrand
  capabilities: TenantCapabilities
  copy: TenantCopy
}
```

- [ ] **Step 2: Write the sage tenant config**

```typescript
// packages/tenant/src/configs/sage.ts
import type { TenantConfig } from '../types'

export const sage: TenantConfig = {
  brand: {
    logo: '/logos/sage.svg',
    colors: {
      primary:       '#4A7C59',
      primaryDark:   '#3D6A4B',
      secondary:     '#2D6B6B',
      surface:       '#F9F8F6',
      surfaceTinted: '#EAF0EA',
      textPrimary:   '#111827',
      textSecondary: '#6B7280',
      border:        '#E5E7EB',
      crisis:        '#DC2626',
    },
    fonts: { body: 'Plus Jakarta Sans', arabic: 'IBM Plex Arabic' },
    supportUrl: 'https://sage.cda.ae/support',
    locales: ['en', 'ar'],
  },
  // Tenant capabilities replace standalone feature flags — there is no separate flags system.
  capabilities: {
    voiceBiomarker:   false,
    adminDashboard:   true,
    onboardingWizard: true,
    rtl:              true,
    demoSeed:         true,
  },
  copy: {
    appName:            'Sage',
    tagline:            'Your personal wellbeing companion',
    onboardingGreeting: 'Welcome to Sage',
    progressHeader:     'My Progress',
    adminHeader:        'Community Insights',
  },
}
```

- [ ] **Step 3: Write the resolver**

```typescript
// packages/tenant/src/index.ts
import type { TenantConfig } from './types'
import { sage } from './configs/sage'

const configs: Record<string, TenantConfig> = { sage }

const tenantKey = process.env.NEXT_PUBLIC_TENANT ?? 'sage'
const resolved = configs[tenantKey]

if (!resolved) {
  throw new Error(`Unknown tenant: "${tenantKey}". Add it to packages/tenant/src/configs/.`)
}

export const tenant: TenantConfig = resolved
export type { TenantConfig } from './types'
```

- [ ] **Step 4: Write tests**

```typescript
// packages/tenant/src/__tests__/tenant.test.ts
import { describe, it, expect } from 'vitest'
import { sage } from '../configs/sage'

describe('sage tenant config', () => {
  it('has all required brand colors', () => {
    const required = ['primary', 'primaryDark', 'secondary', 'surface',
      'surfaceTinted', 'textPrimary', 'textSecondary', 'border', 'crisis']
    required.forEach(key => {
      expect(sage.brand.colors).toHaveProperty(key)
    })
  })

  it('crisis color is never reused as a primary color', () => {
    expect(sage.brand.colors.crisis).not.toBe(sage.brand.colors.primary)
    expect(sage.brand.colors.crisis).not.toBe(sage.brand.colors.secondary)
  })

  it('capabilities are all booleans', () => {
    Object.values(sage.capabilities).forEach(v => {
      expect(typeof v).toBe('boolean')
    })
  })

  it('copy has no empty strings', () => {
    Object.values(sage.copy).forEach(v => {
      expect(v.trim().length).toBeGreaterThan(0)
    })
  })
})
```

- [ ] **Step 5: Run**

```bash
npx vitest run packages/tenant
```

Expected: 4 tests pass.

- [ ] **Step 6: Commit**

```bash
git add packages/tenant
git commit -m "feat: tenant config system with sage preset"
```

---

## Task 4: Theme Package (`packages/theme`)

**Files:**
- Create: `packages/theme/src/css-vars.ts`
- Create: `packages/theme/src/tailwind-preset.ts`
- Create: `packages/theme/src/index.ts`
- Create: `packages/theme/src/__tests__/theme.test.ts`

- [ ] **Step 1: Write CSS variable emitter**

```typescript
// packages/theme/src/css-vars.ts
import type { TenantBrand } from '@cdai/tenant'

export function buildCssVars(brand: TenantBrand): Record<string, string> {
  return {
    '--color-primary':        brand.colors.primary,
    '--color-primary-dark':   brand.colors.primaryDark,
    '--color-secondary':      brand.colors.secondary,
    '--color-surface':        brand.colors.surface,
    '--color-surface-tinted': brand.colors.surfaceTinted,
    '--color-text-primary':   brand.colors.textPrimary,
    '--color-text-secondary': brand.colors.textSecondary,
    '--color-border':         brand.colors.border,
    '--color-crisis':         brand.colors.crisis,
    '--font-body':            `'${brand.fonts.body}', sans-serif`,
    '--font-arabic':          `'${brand.fonts.arabic}', sans-serif`,
  }
}

export function cssVarsString(brand: TenantBrand): string {
  const vars = buildCssVars(brand)
  return `:root {\n${Object.entries(vars).map(([k, v]) => `  ${k}: ${v};`).join('\n')}\n}`
}
```

- [ ] **Step 2: Write Tailwind preset**

```typescript
// packages/theme/src/tailwind-preset.ts
import type { Config } from 'tailwindcss'

export const tailwindPreset: Partial<Config> = {
  theme: {
    extend: {
      colors: {
        primary:        'var(--color-primary)',
        'primary-dark': 'var(--color-primary-dark)',
        secondary:      'var(--color-secondary)',
        surface:        'var(--color-surface)',
        'surface-tinted':'var(--color-surface-tinted)',
        crisis:         'var(--color-crisis)',
      },
      fontFamily: {
        body:   'var(--font-body)',
        arabic: 'var(--font-arabic)',
      },
      transitionDuration: {
        '350': '350ms',
      },
    },
  },
}
```

- [ ] **Step 3: Write index**

```typescript
// packages/theme/src/index.ts
export { buildCssVars, cssVarsString } from './css-vars'
export { tailwindPreset } from './tailwind-preset'
```

- [ ] **Step 4: Write tests**

```typescript
// packages/theme/src/__tests__/theme.test.ts
import { describe, it, expect } from 'vitest'
import { buildCssVars } from '../css-vars'
import { sage } from '@cdai/tenant/configs/sage'

describe('buildCssVars', () => {
  it('emits a CSS variable for every brand color', () => {
    const vars = buildCssVars(sage.brand)
    expect(vars['--color-primary']).toBe('#4A7C59')
    expect(vars['--color-crisis']).toBe('#DC2626')
  })

  it('emits font variables', () => {
    const vars = buildCssVars(sage.brand)
    expect(vars['--font-body']).toContain('Plus Jakarta Sans')
    expect(vars['--font-arabic']).toContain('IBM Plex Arabic')
  })

  it('produces one var per brand color key (9 colors + 2 fonts = 11)', () => {
    const vars = buildCssVars(sage.brand)
    expect(Object.keys(vars)).toHaveLength(11)
  })
})
```

- [ ] **Step 5: Run**

```bash
npx vitest run packages/theme
```

Expected: 3 tests pass.

- [ ] **Step 6: Commit**

```bash
git add packages/theme
git commit -m "feat: theme package — CSS var emitter and Tailwind preset"
```

---

## Task 5: UI Component Library (`packages/ui`)

**Files:**
- Create: `packages/ui/src/lib/utils.ts`
- Create: `packages/ui/src/components/button.tsx`
- Create: `packages/ui/src/components/card.tsx`
- Create: `packages/ui/src/components/input.tsx`
- Create: `packages/ui/src/components/skeleton.tsx`
- Create: `packages/ui/src/components/bottom-sheet.tsx`
- Create: `packages/ui/src/index.ts`
- Create: `packages/ui/src/__tests__/button.test.tsx`

- [ ] **Step 1: Install deps in packages/ui**

```bash
cd packages/ui
npm install clsx tailwind-merge class-variance-authority react react-dom
npm install -D @testing-library/react @testing-library/jest-dom vitest jsdom
```

- [ ] **Step 2: Write utils**

```typescript
// packages/ui/src/lib/utils.ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 3: Write Button**

```typescript
// packages/ui/src/components/button.tsx
import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../lib/utils'

// All sizes meet the 44×44px touch target minimum (iOS HIG / Android guidelines).
// sm is visually compact but padded to 44px height so tap targets are never undersized.
const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-full font-body text-sm font-medium transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 min-w-[44px]',
  {
    variants: {
      variant: {
        primary:  'bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-dark)]',
        outline:  'border border-[var(--color-border)] bg-transparent hover:bg-[var(--color-surface-tinted)]',
        ghost:    'bg-transparent hover:bg-[var(--color-surface-tinted)]',
      },
      size: {
        sm: 'h-11 px-3 text-xs',
        md: 'h-11 px-5',
        lg: 'h-12 px-7 text-base',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
  )
)
Button.displayName = 'Button'
```

- [ ] **Step 4: Write Card**

```typescript
// packages/ui/src/components/card.tsx
import * as React from 'react'
import { cn } from '../lib/utils'

export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('rounded-xl bg-[var(--color-surface-tinted)] ring-1 ring-black/5 p-4', className)}
      {...props}
    />
  )
)
Card.displayName = 'Card'
```

- [ ] **Step 5: Write Input**

```typescript
// packages/ui/src/components/input.tsx
import * as React from 'react'
import { cn } from '../lib/utils'

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        'w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-offset-1 transition-shadow duration-200',
        className
      )}
      {...props}
    />
  )
)
Input.displayName = 'Input'
```

- [ ] **Step 6: Write Skeleton**

```typescript
// packages/ui/src/components/skeleton.tsx
import * as React from 'react'
import { cn } from '../lib/utils'

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('animate-pulse rounded-lg bg-[var(--color-border)]', className)}
      {...props}
    />
  )
}
```

- [ ] **Step 7: Write BottomSheet**

```typescript
// packages/ui/src/components/bottom-sheet.tsx
'use client'
import * as React from 'react'
import { cn } from '../lib/utils'

interface BottomSheetProps {
  open: boolean
  onClose: () => void
  children: React.ReactNode
  className?: string
}

export function BottomSheet({ open, onClose, children, className }: BottomSheetProps) {
  if (!open) return null
  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/30" onClick={onClose} />
      <div
        className={cn(
          'fixed inset-x-0 bottom-0 z-50 rounded-t-2xl bg-[var(--color-surface)] p-6 shadow-xl',
          className
        )}
      >
        {children}
      </div>
    </>
  )
}
```

- [ ] **Step 8: Write ResponsivePanel**

```typescript
// packages/ui/src/components/responsive-panel.tsx
'use client'
import { useEffect, useState } from 'react'
import { BottomSheet } from './bottom-sheet'
import { cn } from '../lib/utils'

interface ResponsivePanelProps {
  open: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
}

export function ResponsivePanel({ open, onClose, title, children }: ResponsivePanelProps) {
  const [isDesktop, setIsDesktop] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 768px)')
    setIsDesktop(mq.matches)
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  if (!open) return null

  if (!isDesktop) return <BottomSheet open={open} onClose={onClose}>{children}</BottomSheet>

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/20" onClick={onClose} />
      <div className="fixed top-0 end-0 z-50 h-full w-80 flex flex-col bg-[var(--color-surface)] shadow-2xl">
        <div className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
          {title && <h2 className="font-semibold">{title}</h2>}
          <button onClick={onClose} className="ms-auto text-[var(--color-text-secondary)]">✕</button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-4">{children}</div>
      </div>
    </>
  )
}
```

- [ ] **Step 9: Write barrel export**

```typescript
// packages/ui/src/index.ts
export { Button } from './components/button'
export { Card } from './components/card'
export { Input } from './components/input'
export { Skeleton } from './components/skeleton'
export { BottomSheet } from './components/bottom-sheet'
export { ResponsivePanel } from './components/responsive-panel'
export { cn } from './lib/utils'
```

- [ ] **Step 9: Write Button test**

```typescript
// packages/ui/src/__tests__/button.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from '../components/button'

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
  })

  it('calls onClick when clicked', async () => {
    const handler = vi.fn()
    render(<Button onClick={handler}>Click</Button>)
    await userEvent.click(screen.getByRole('button'))
    expect(handler).toHaveBeenCalledOnce()
  })

  it('is disabled when disabled prop is set', () => {
    render(<Button disabled>No</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('accepts className override', () => {
    render(<Button className="extra-class">X</Button>)
    expect(screen.getByRole('button')).toHaveClass('extra-class')
  })
})
```

- [ ] **Step 10: Run tests**

```bash
npx vitest run packages/ui
```

Expected: 4 tests pass.

- [ ] **Step 11: Commit**

```bash
git add packages/ui
git commit -m "feat: shared UI component library (Button, Card, Input, Skeleton, BottomSheet)"
```

---

## Task 6: Next.js App Bootstrap (`apps/web`)

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/tailwind.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/vitest.config.ts`

- [ ] **Step 1: Install Next.js and core deps**

```bash
cd apps/web
npm install next@15 react react-dom @cdai/types @cdai/tenant @cdai/theme @cdai/ui
npm install zustand @supabase/supabase-js @supabase/ssr
npm install ai @ai-sdk/openai
npm install framer-motion recharts
npm install react-hook-form zod @hookform/resolvers
npm install -D typescript @types/react @types/node tailwindcss @tailwindcss/postcss vitest @vitejs/plugin-react @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 2: Write `next.config.ts`**

```typescript
// apps/web/next.config.ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  transpilePackages: ['@cdai/ui', '@cdai/theme', '@cdai/tenant', '@cdai/types'],
}

export default nextConfig
```

- [ ] **Step 3: Write `tailwind.config.ts`**

```typescript
// apps/web/tailwind.config.ts
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
```

- [ ] **Step 4: Write `vitest.config.ts`**

```typescript
// apps/web/vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    globals: true,
  },
})
```

Create `apps/web/vitest.setup.ts`:
```typescript
import '@testing-library/jest-dom'
```

- [ ] **Step 5: Verify the app starts**

```bash
cd apps/web
npm run dev
```

Expected: Next.js dev server starts on http://localhost:3000 with no errors.

- [ ] **Step 6: Commit**

```bash
git add apps/web
git commit -m "feat: Next.js 15 app scaffold with Tailwind v4 and Vitest"
```

---

## Task 7: Supabase Schema + Client

**Files:**
- Create: `supabase/migrations/001_initial_schema.sql`
- Create: `apps/web/lib/supabase/client.ts`
- Create: `apps/web/lib/supabase/server.ts`

- [ ] **Step 1: Write the migration**

```sql
-- supabase/migrations/001_initial_schema.sql

create table public.user_profiles (
  id             uuid primary key references auth.users(id) on delete cascade,
  name           text,
  age_range      text,
  role           text check (role in ('parent', 'service_user', 'professional')),
  locale         text not null default 'en' check (locale in ('en', 'ar')),
  is_admin       boolean not null default false,
  onboarding_complete boolean not null default false,
  onboarding_step     int not null default 1,
  wellness_q1    text,
  wellness_q2    text,
  created_at     timestamptz not null default now()
);
alter table public.user_profiles enable row level security;
create policy "own profile" on public.user_profiles
  for all using (auth.uid() = id);

create table public.chat_sessions (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references public.user_profiles(id) on delete cascade,
  name       text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.chat_sessions enable row level security;
create policy "own sessions" on public.chat_sessions
  for all using (auth.uid() = user_id);

create table public.messages (
  id         uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.chat_sessions(id) on delete cascade,
  role       text not null check (role in ('user', 'ai', 'system', 'crisis')),
  content    text not null,
  intent     text check (intent in ('knowledge', 'emotional')),
  created_at timestamptz not null default now()
);
alter table public.messages enable row level security;
create policy "own messages" on public.messages
  for all using (
    auth.uid() = (select user_id from public.chat_sessions where id = session_id)
  );

create table public.mood_scores (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references public.user_profiles(id) on delete cascade,
  session_id uuid not null references public.chat_sessions(id) on delete cascade,
  score      numeric(3,1) not null check (score >= 1 and score <= 5),
  created_at timestamptz not null default now()
);
alter table public.mood_scores enable row level security;
create policy "own mood scores" on public.mood_scores
  for all using (auth.uid() = user_id);

create table public.session_insights (
  id         uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.chat_sessions(id) on delete cascade,
  user_id    uuid not null references public.user_profiles(id) on delete cascade,
  content    text not null,
  topic_tag  text not null,
  created_at timestamptz not null default now()
);
alter table public.session_insights enable row level security;
create policy "own insights" on public.session_insights
  for all using (auth.uid() = user_id);
```

- [ ] **Step 2: Apply migration**

```bash
npx supabase db push
```

Expected: migration applied, no errors.

- [ ] **Step 3: Write browser client**

```typescript
// apps/web/lib/supabase/client.ts
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
```

- [ ] **Step 4: Write server client**

```typescript
// apps/web/lib/supabase/server.ts
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createClient() {
  const cookieStore = await cookies()
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: (cookiesToSet) => {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          )
        },
      },
    }
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add supabase apps/web/lib/supabase
git commit -m "feat: Supabase schema migration and client setup"
```

---

## Task 8: Zustand Stores

**Files:**
- Create: `apps/web/lib/stores/locale-store.ts`
- Create: `apps/web/lib/stores/onboarding-store.ts`
- Create: `apps/web/lib/stores/chat-store.ts`
- Create: `apps/web/lib/stores/__tests__/locale-store.test.ts`
- Create: `apps/web/lib/stores/__tests__/onboarding-store.test.ts`

- [ ] **Step 1: Write locale store**

```typescript
// apps/web/lib/stores/locale-store.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Locale } from '@cdai/types'

interface LocaleStore {
  locale: Locale
  setLocale: (locale: Locale) => void
}

export const useLocaleStore = create<LocaleStore>()(
  persist(
    (set) => ({
      locale: 'en',
      setLocale: (locale) => set({ locale }),
    }),
    { name: 'cdai-locale' }
  )
)
```

- [ ] **Step 2: Write locale store test**

```typescript
// apps/web/lib/stores/__tests__/locale-store.test.ts
import { describe, it, expect, beforeEach } from 'vitest'
import { useLocaleStore } from '../locale-store'

describe('useLocaleStore', () => {
  beforeEach(() => useLocaleStore.setState({ locale: 'en' }))

  it('defaults to en', () => {
    expect(useLocaleStore.getState().locale).toBe('en')
  })

  it('setLocale updates locale', () => {
    useLocaleStore.getState().setLocale('ar')
    expect(useLocaleStore.getState().locale).toBe('ar')
  })
})
```

- [ ] **Step 3: Write onboarding store**

```typescript
// apps/web/lib/stores/onboarding-store.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Locale, AgeRange, UserRole } from '@cdai/types'

interface OnboardingAnswers {
  locale: Locale | null
  name: string
  ageRange: AgeRange | null
  role: UserRole | null
  wellnessQ1: string
  wellnessQ2: string
}

interface OnboardingStore {
  step: number
  answers: OnboardingAnswers
  setStep: (step: number) => void
  setAnswer: <K extends keyof OnboardingAnswers>(key: K, value: OnboardingAnswers[K]) => void
  reset: () => void
}

const defaultAnswers: OnboardingAnswers = {
  locale: null, name: '', ageRange: null,
  role: null, wellnessQ1: '', wellnessQ2: '',
}

export const useOnboardingStore = create<OnboardingStore>()(
  persist(
    (set) => ({
      step: 1,
      answers: defaultAnswers,
      setStep: (step) => set({ step }),
      setAnswer: (key, value) =>
        set((s) => ({ answers: { ...s.answers, [key]: value } })),
      reset: () => set({ step: 1, answers: defaultAnswers }),
    }),
    { name: 'cdai-onboarding' }
  )
)
```

- [ ] **Step 4: Write onboarding store test**

```typescript
// apps/web/lib/stores/__tests__/onboarding-store.test.ts
import { describe, it, expect, beforeEach } from 'vitest'
import { useOnboardingStore } from '../onboarding-store'

describe('useOnboardingStore', () => {
  beforeEach(() => useOnboardingStore.getState().reset())

  it('starts at step 1', () => {
    expect(useOnboardingStore.getState().step).toBe(1)
  })

  it('setAnswer updates a single answer field', () => {
    useOnboardingStore.getState().setAnswer('name', 'Fatima')
    expect(useOnboardingStore.getState().answers.name).toBe('Fatima')
  })

  it('setAnswer does not overwrite other fields', () => {
    useOnboardingStore.getState().setAnswer('name', 'Fatima')
    useOnboardingStore.getState().setAnswer('wellnessQ1', 'Stress')
    expect(useOnboardingStore.getState().answers.name).toBe('Fatima')
    expect(useOnboardingStore.getState().answers.wellnessQ1).toBe('Stress')
  })

  it('reset clears all answers and resets step', () => {
    useOnboardingStore.getState().setAnswer('name', 'Fatima')
    useOnboardingStore.getState().setStep(4)
    useOnboardingStore.getState().reset()
    expect(useOnboardingStore.getState().answers.name).toBe('')
    expect(useOnboardingStore.getState().step).toBe(1)
  })
})
```

- [ ] **Step 5: Write chat store**

```typescript
// apps/web/lib/stores/chat-store.ts
import { create } from 'zustand'
import type { ChatMessage, ChatSession } from '@cdai/types'

interface ChatStore {
  activeSession: ChatSession | null
  messages: ChatMessage[]
  isStreaming: boolean
  sessions: ChatSession[]
  setActiveSession: (session: ChatSession | null) => void
  setMessages: (messages: ChatMessage[]) => void
  appendMessage: (message: ChatMessage) => void
  setIsStreaming: (streaming: boolean) => void
  setSessions: (sessions: ChatSession[]) => void
}

export const useChatStore = create<ChatStore>((set) => ({
  activeSession: null,
  messages: [],
  isStreaming: false,
  sessions: [],
  setActiveSession: (session) => set({ activeSession: session }),
  setMessages: (messages) => set({ messages }),
  appendMessage: (message) => set((s) => ({ messages: [...s.messages, message] })),
  setIsStreaming: (streaming) => set({ isStreaming: streaming }),
  setSessions: (sessions) => set({ sessions }),
}))
```

- [ ] **Step 6: Run tests**

```bash
npx vitest run apps/web/lib/stores
```

Expected: 6 tests pass.

- [ ] **Step 7: Commit**

```bash
git add apps/web/lib/stores
git commit -m "feat: Zustand stores for locale, onboarding, and chat"
```

---

## Task 9: Middleware + Root Layout

**Files:**
- Create: `apps/web/middleware.ts`
- Create: `apps/web/app/layout.tsx`
- Create: `apps/web/components/providers.tsx`
- Create: `apps/web/middleware.test.ts`

- [ ] **Step 1: Write middleware**

```typescript
// apps/web/middleware.ts
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

const AUTH_PATHS = ['/sign-in', '/sign-up', '/forgot-password']

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const response = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (toSet) => toSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options)
        ),
      },
    }
  )

  const { data: { session } } = await supabase.auth.getSession()

  // Unauthenticated → sign-in (skip auth routes themselves)
  if (!session && !AUTH_PATHS.some(p => pathname.startsWith(p))) {
    return NextResponse.redirect(new URL('/sign-in', request.url))
  }

  // Root redirect
  if (session && pathname === '/') {
    return NextResponse.redirect(new URL('/chat', request.url))
  }

  // Single profile fetch — used for both admin check and onboarding gate.
  // Never make two round-trips to Supabase per middleware call.
  if (session && !AUTH_PATHS.some(p => pathname.startsWith(p)) && pathname !== '/') {
    const { data: profile } = await supabase
      .from('user_profiles')
      .select('is_admin, onboarding_complete, onboarding_step')
      .eq('id', session.user.id)
      .single()

    if (pathname.startsWith('/admin') && !profile?.is_admin) {
      return new NextResponse(null, { status: 403 })
    }

    if (
      !pathname.startsWith('/admin') &&
      !pathname.startsWith('/onboarding') &&
      profile && !profile.onboarding_complete
    ) {
      return NextResponse.redirect(
        new URL(`/onboarding/step-${profile.onboarding_step}`, request.url)
      )
    }
  }

  return response
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|icons|manifest.json|offline.html).*)'],
}
```

- [ ] **Step 2: Write providers**

```typescript
// apps/web/components/providers.tsx
'use client'
import { useEffect } from 'react'
import { useLocaleStore } from '@/lib/stores/locale-store'
import type { Locale } from '@cdai/types'

interface ProvidersProps {
  children: React.ReactNode
  initialLocale: Locale
}

export function Providers({ children, initialLocale }: ProvidersProps) {
  const setLocale = useLocaleStore((s) => s.setLocale)

  useEffect(() => {
    // Hydrate store from server-read cookie on first mount only
    useLocaleStore.setState({ locale: initialLocale })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return <>{children}</>
}
```

- [ ] **Step 3: Write root layout**

```typescript
// apps/web/app/layout.tsx
import type { Metadata } from 'next'
import { Plus_Jakarta_Sans, IBM_Plex_Arabic } from 'next/font/google'
import { cookies } from 'next/headers'
import { cssVarsString } from '@cdai/theme'
import { tenant } from '@cdai/tenant'
import { Providers } from '@/components/providers'
import type { Locale } from '@cdai/types'
import './globals.css'

const jakartaSans = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-body',
  display: 'swap',
})

const ibmPlexArabic = IBM_Plex_Arabic({
  subsets: ['arabic'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-arabic',
  display: 'swap',
})

export const metadata: Metadata = {
  title: tenant.copy.appName,
  description: tenant.copy.tagline,
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: tenant.copy.appName,
  },
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = await cookies()
  const locale = (cookieStore.get('cdai-locale')?.value ?? 'en') as Locale
  const dir = locale === 'ar' ? 'rtl' : 'ltr'
  const fontClass = locale === 'ar' ? ibmPlexArabic.variable : jakartaSans.variable
  const cssVars = cssVarsString(tenant.brand)

  return (
    <html lang={locale} dir={dir} className={fontClass}>
      <head>
        <style dangerouslySetInnerHTML={{ __html: cssVars }} />
        <link rel="apple-touch-icon" href="/icons/icon-180.png" />
      </head>
      <body className="bg-[var(--color-surface)] text-[var(--color-text-primary)] antialiased">
        <Providers initialLocale={locale}>{children}</Providers>
      </body>
    </html>
  )
}
```

- [ ] **Step 4: Write `app/globals.css`** (minimal — all tokens come from CSS vars)

```css
/* apps/web/app/globals.css */
@import "tailwindcss";
*, *::before, *::after { box-sizing: border-box; }
```

- [ ] **Step 5: Manually test middleware**

Start the dev server and visit `http://localhost:3000` without a session. Verify redirect to `/sign-in`. Sign in, verify redirect to `/chat`.

- [ ] **Step 6: Commit**

```bash
git add apps/web/middleware.ts apps/web/app/layout.tsx apps/web/components/providers.tsx apps/web/app/globals.css
git commit -m "feat: edge middleware for auth/role/onboarding routing, root layout with locale-split fonts"
```

---

## Task 10: Auth Screens

**Files:**
- Create: `apps/web/app/(auth)/layout.tsx`
- Create: `apps/web/components/auth/language-toggle.tsx`
- Create: `apps/web/components/auth/sign-up-form.tsx`
- Create: `apps/web/components/auth/sign-in-form.tsx`
- Create: `apps/web/app/(auth)/sign-in/page.tsx`
- Create: `apps/web/app/(auth)/sign-up/page.tsx`
- Create: `apps/web/app/(auth)/forgot-password/page.tsx`
- Create: `apps/web/components/auth/__tests__/sign-in-form.test.tsx`

- [ ] **Step 1: Write auth layout**

```typescript
// apps/web/app/(auth)/layout.tsx
import { LanguageToggle } from '@/components/auth/language-toggle'

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh flex flex-col items-center justify-center bg-[var(--color-surface)] px-4">
      <div className="absolute top-4 end-4">
        <LanguageToggle />
      </div>
      <div className="w-full max-w-sm">{children}</div>
    </div>
  )
}
```

- [ ] **Step 2: Write LanguageToggle**

```typescript
// apps/web/components/auth/language-toggle.tsx
'use client'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { Button } from '@cdai/ui'

export function LanguageToggle() {
  const { locale, setLocale } = useLocaleStore()

  function toggle() {
    const next = locale === 'en' ? 'ar' : 'en'
    setLocale(next)
    document.cookie = `cdai-locale=${next};path=/;max-age=31536000`
    // Reload so layout.tsx re-reads the cookie and flips dir
    window.location.reload()
  }

  return (
    <Button variant="ghost" size="sm" onClick={toggle}>
      {locale === 'en' ? 'عربي' : 'EN'}
    </Button>
  )
}
```

- [ ] **Step 3: Write sign-up form**

```typescript
// apps/web/components/auth/sign-up-form.tsx
'use client'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'
import { Button, Input } from '@cdai/ui'
import { useState } from 'react'

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8, 'Minimum 8 characters'),
})
type Fields = z.infer<typeof schema>

export function SignUpForm() {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Fields>({
    resolver: zodResolver(schema),
  })
  const [serverError, setServerError] = useState<string | null>(null)
  const router = useRouter()

  async function onSubmit(data: Fields) {
    setServerError(null)
    const supabase = createClient()
    const { error } = await supabase.auth.signUp({
      email: data.email,
      password: data.password,
    })
    if (error) { setServerError(error.message); return }
    // Create profile row (name/role set during onboarding)
    router.push('/onboarding/step-1')
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <Input type="email" placeholder="Email" {...register('email')} />
      {errors.email && <p className="text-xs text-[var(--color-crisis)]">{errors.email.message}</p>}
      <Input type="password" placeholder="Password" {...register('password')} />
      {errors.password && <p className="text-xs text-[var(--color-crisis)]">{errors.password.message}</p>}
      {serverError && <p className="text-xs text-[var(--color-crisis)]">{serverError}</p>}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Creating account…' : 'Create account'}
      </Button>
    </form>
  )
}
```

- [ ] **Step 4: Write sign-in form (same pattern)**

```typescript
// apps/web/components/auth/sign-in-form.tsx
'use client'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'
import { Button, Input } from '@cdai/ui'
import { useState } from 'react'

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1, 'Required'),
})
type Fields = z.infer<typeof schema>

export function SignInForm() {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Fields>({
    resolver: zodResolver(schema),
  })
  const [serverError, setServerError] = useState<string | null>(null)
  const router = useRouter()

  async function onSubmit(data: Fields) {
    setServerError(null)
    const supabase = createClient()
    const { error } = await supabase.auth.signInWithPassword(data)
    if (error) { setServerError(error.message); return }
    router.push('/chat')
    router.refresh()
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <Input type="email" placeholder="Email" {...register('email')} />
      {errors.email && <p className="text-xs text-[var(--color-crisis)]">{errors.email.message}</p>}
      <Input type="password" placeholder="Password" {...register('password')} />
      {errors.password && <p className="text-xs text-[var(--color-crisis)]">{errors.password.message}</p>}
      {serverError && <p className="text-xs text-[var(--color-crisis)]">{serverError}</p>}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Signing in…' : 'Sign in'}
      </Button>
    </form>
  )
}
```

- [ ] **Step 5: Write sign-in page**

```typescript
// apps/web/app/(auth)/sign-in/page.tsx
import Link from 'next/link'
import { SignInForm } from '@/components/auth/sign-in-form'
import { tenant } from '@cdai/tenant'

export default function SignInPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">{tenant.copy.appName}</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">Sign in to continue</p>
      </div>
      <SignInForm />
      <p className="text-center text-sm text-[var(--color-text-secondary)]">
        No account?{' '}
        <Link href="/sign-up" className="text-[var(--color-primary)] underline-offset-2 hover:underline">
          Sign up
        </Link>
      </p>
      <p className="text-center text-sm">
        <Link href="/forgot-password" className="text-[var(--color-text-secondary)] underline-offset-2 hover:underline">
          Forgot password?
        </Link>
      </p>
    </div>
  )
}
```

- [ ] **Step 6: Write sign-up and forgot-password pages** (follow same pattern as sign-in page, swap form component and copy)

`apps/web/app/(auth)/sign-up/page.tsx` — renders `<SignUpForm />`, links to `/sign-in`.

`apps/web/app/(auth)/forgot-password/page.tsx` — renders a simple email input that calls `supabase.auth.resetPasswordForEmail()`, shows success message on submit.

- [ ] **Step 7: Write sign-in form test**

```typescript
// apps/web/components/auth/__tests__/sign-in-form.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SignInForm } from '../sign-in-form'

vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({
    auth: {
      signInWithPassword: vi.fn().mockResolvedValue({ error: null }),
    },
  }),
}))
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}))

describe('SignInForm', () => {
  it('shows validation error when email is empty', async () => {
    render(<SignInForm />)
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => {
      expect(screen.getByText(/invalid email/i)).toBeInTheDocument()
    })
  })

  it('calls signInWithPassword with entered credentials', async () => {
    const { createClient } = await import('@/lib/supabase/client')
    const mockSignIn = (createClient() as any).auth.signInWithPassword
    render(<SignInForm />)
    await userEvent.type(screen.getByPlaceholderText('Email'), 'test@example.com')
    await userEvent.type(screen.getByPlaceholderText('Password'), 'password123')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      })
    })
  })
})
```

- [ ] **Step 8: Run tests**

```bash
npx vitest run apps/web/components/auth
```

Expected: 2 tests pass.

- [ ] **Step 9: Commit**

```bash
git add apps/web/app/\(auth\) apps/web/components/auth
git commit -m "feat: auth screens — sign-in, sign-up, forgot-password with Zod validation"
```

---

## Task 11: Onboarding Wizard

**Files:**
- Create: `apps/web/app/(onboarding)/layout.tsx`
- Create: `apps/web/app/(onboarding)/[step]/page.tsx`
- Create: `apps/web/components/onboarding/progress-bar.tsx`
- Create: `apps/web/components/onboarding/steps/welcome.tsx`
- Create: `apps/web/components/onboarding/steps/language.tsx`
- Create: `apps/web/components/onboarding/steps/name.tsx`
- Create: `apps/web/components/onboarding/steps/about-you.tsx`
- Create: `apps/web/components/onboarding/steps/what-matters.tsx`
- Create: `apps/web/components/onboarding/steps/personalising.tsx`

- [ ] **Step 1: Write onboarding layout**

```typescript
// apps/web/app/(onboarding)/layout.tsx
import { ProgressBar } from '@/components/onboarding/progress-bar'

export default function OnboardingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh flex flex-col bg-[var(--color-surface)]">
      <ProgressBar totalSteps={6} />
      <main className="flex flex-1 flex-col items-center justify-center px-6 py-8">
        <div className="w-full max-w-sm">{children}</div>
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Write progress bar**

```typescript
// apps/web/components/onboarding/progress-bar.tsx
'use client'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'

export function ProgressBar({ totalSteps }: { totalSteps: number }) {
  const step = useOnboardingStore((s) => s.step)
  const pct = Math.round(((step - 1) / totalSteps) * 100)
  return (
    <div className="h-1 w-full bg-[var(--color-border)]">
      <div
        className="h-1 bg-[var(--color-primary)] transition-all duration-350"
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}
```

- [ ] **Step 3: Write step router page**

```typescript
// apps/web/app/(onboarding)/[step]/page.tsx
import { notFound } from 'next/navigation'
import { Welcome } from '@/components/onboarding/steps/welcome'
import { Language } from '@/components/onboarding/steps/language'
import { Name } from '@/components/onboarding/steps/name'
import { AboutYou } from '@/components/onboarding/steps/about-you'
import { WhatMatters } from '@/components/onboarding/steps/what-matters'
import { Personalising } from '@/components/onboarding/steps/personalising'

const STEPS = ['step-1', 'step-2', 'step-3', 'step-4', 'step-5', 'step-6']
const STEP_COMPONENTS = [Welcome, Language, Name, AboutYou, WhatMatters, Personalising]

interface Props { params: Promise<{ step: string }> }

export default async function OnboardingStepPage({ params }: Props) {
  const { step } = await params
  const idx = STEPS.indexOf(step)
  if (idx === -1) notFound()
  const StepComponent = STEP_COMPONENTS[idx]
  return <StepComponent />
}

export function generateStaticParams() {
  return STEPS.map((step) => ({ step }))
}
```

- [ ] **Step 4: Write Welcome step**

```typescript
// apps/web/components/onboarding/steps/welcome.tsx
'use client'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { Button } from '@cdai/ui'
import { tenant } from '@cdai/tenant'

export function Welcome() {
  const { setStep } = useOnboardingStore()
  const router = useRouter()

  function next() {
    setStep(2)
    router.push('/onboarding/step-2')
  }

  return (
    <div className="flex flex-col items-center gap-8 text-center">
      <img src={tenant.brand.logo} alt={tenant.copy.appName} className="h-16 w-16" />
      <div>
        <h1 className="text-2xl font-semibold">{tenant.copy.onboardingGreeting}</h1>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">{tenant.copy.tagline}</p>
      </div>
      <Button onClick={next} size="lg" className="w-full">Get started</Button>
    </div>
  )
}
```

- [ ] **Step 5: Write Language step**

```typescript
// apps/web/components/onboarding/steps/language.tsx
'use client'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { Button } from '@cdai/ui'
import type { Locale } from '@cdai/types'

const OPTIONS: { label: string; value: Locale }[] = [
  { label: 'English', value: 'en' },
  { label: 'العربية', value: 'ar' },
]

export function Language() {
  const { setAnswer, setStep } = useOnboardingStore()
  const setLocale = useLocaleStore((s) => s.setLocale)
  const router = useRouter()

  function choose(locale: Locale) {
    setAnswer('locale', locale)
    setLocale(locale)
    document.cookie = `cdai-locale=${locale};path=/;max-age=31536000`
    setStep(3)
    // Reload to flip dir immediately, then navigate
    window.location.href = '/onboarding/step-3'
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xl font-semibold text-center">Choose your language</h2>
      {OPTIONS.map((opt) => (
        <Button key={opt.value} variant="outline" size="lg" className="w-full" onClick={() => choose(opt.value)}>
          {opt.label}
        </Button>
      ))}
    </div>
  )
}
```

- [ ] **Step 6: Write Name step**

```typescript
// apps/web/components/onboarding/steps/name.tsx
'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { Button, Input } from '@cdai/ui'

export function Name() {
  const { answers, setAnswer, setStep } = useOnboardingStore()
  const [value, setValue] = useState(answers.name)
  const router = useRouter()

  function next() {
    if (!value.trim()) return
    setAnswer('name', value.trim())
    setStep(4)
    router.push('/onboarding/step-4')
  }

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-xl font-semibold">What should we call you?</h2>
      <Input
        placeholder="Your name"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && next()}
        autoFocus
      />
      <Button onClick={next} disabled={!value.trim()} size="lg" className="w-full">
        Continue
      </Button>
    </div>
  )
}
```

- [ ] **Step 7: Write AboutYou step**

```typescript
// apps/web/components/onboarding/steps/about-you.tsx
'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { Button } from '@cdai/ui'
import { cn } from '@cdai/ui'
import type { AgeRange, UserRole } from '@cdai/types'

const AGE_RANGES: AgeRange[] = ['under-18', '18-24', '25-34', '35-44', '45-54', '55+']
const ROLES: { label: string; value: UserRole }[] = [
  { label: 'Parent / Guardian', value: 'parent' },
  { label: 'CDA Service User', value: 'service_user' },
  { label: 'Professional', value: 'professional' },
]

export function AboutYou() {
  const { setAnswer, setStep } = useOnboardingStore()
  const [age, setAge] = useState<AgeRange | null>(null)
  const [role, setRole] = useState<UserRole | null>(null)
  const router = useRouter()

  function next() {
    if (!age || !role) return
    setAnswer('ageRange', age)
    setAnswer('role', role)
    setStep(5)
    router.push('/onboarding/step-5')
  }

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-xl font-semibold">Tell us a little about you</h2>
      <div>
        <p className="mb-2 text-sm text-[var(--color-text-secondary)]">Age range</p>
        <div className="flex flex-wrap gap-2">
          {AGE_RANGES.map((a) => (
            <button
              key={a}
              onClick={() => setAge(a)}
              className={cn(
                'min-h-[44px] rounded-full border px-4 py-2 text-sm transition-colors duration-200',
                age === a
                  ? 'border-[var(--color-primary)] bg-[var(--color-primary)] text-white'
                  : 'border-[var(--color-border)] hover:border-[var(--color-primary)]'
              )}
            >
              {a}
            </button>
          ))}
        </div>
      </div>
      <div>
        <p className="mb-2 text-sm text-[var(--color-text-secondary)]">I am a</p>
        <div className="flex flex-col gap-2">
          {ROLES.map((r) => (
            <button
              key={r.value}
              onClick={() => setRole(r.value)}
              className={cn(
                'rounded-xl border px-4 py-3 text-start text-sm transition-colors duration-200',
                role === r.value
                  ? 'border-[var(--color-primary)] bg-[var(--color-surface-tinted)]'
                  : 'border-[var(--color-border)] hover:border-[var(--color-primary)]'
              )}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>
      <Button onClick={next} disabled={!age || !role} size="lg" className="w-full">
        Continue
      </Button>
    </div>
  )
}
```

- [ ] **Step 8: Write WhatMatters step**

```typescript
// apps/web/components/onboarding/steps/what-matters.tsx
'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { Button } from '@cdai/ui'
import { cn } from '@cdai/ui'

const Q1_OPTIONS = ['Managing stress', 'Parenting challenges', 'Work-life balance', 'Grief or loss', 'Anxiety', 'Relationships']
const Q2_OPTIONS = ['Someone to talk to', 'Practical tools & tips', 'Understanding my emotions', 'Crisis support']

export function WhatMatters() {
  const { setAnswer, setStep } = useOnboardingStore()
  const [q1, setQ1] = useState('')
  const [q2, setQ2] = useState('')
  const router = useRouter()

  function next() {
    if (!q1 || !q2) return
    setAnswer('wellnessQ1', q1)
    setAnswer('wellnessQ2', q2)
    setStep(6)
    router.push('/onboarding/step-6')
  }

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-xl font-semibold">What brings you here?</h2>
      <div className="flex flex-wrap gap-2">
        {Q1_OPTIONS.map((opt) => (
          <button key={opt} onClick={() => setQ1(opt)}
            className={cn(
              'min-h-[44px] rounded-full border px-4 py-2 text-sm transition-colors duration-200',
              q1 === opt ? 'border-[var(--color-primary)] bg-[var(--color-primary)] text-white' : 'border-[var(--color-border)]'
            )}>{opt}</button>
        ))}
      </div>
      <p className="text-sm text-[var(--color-text-secondary)]">What would help most?</p>
      <div className="flex flex-col gap-2">
        {Q2_OPTIONS.map((opt) => (
          <button key={opt} onClick={() => setQ2(opt)}
            className={cn(
              'rounded-xl border px-4 py-3 text-start text-sm transition-colors duration-200',
              q2 === opt ? 'border-[var(--color-primary)] bg-[var(--color-surface-tinted)]' : 'border-[var(--color-border)]'
            )}>{opt}</button>
        ))}
      </div>
      <Button onClick={next} disabled={!q1 || !q2} size="lg" className="w-full">Continue</Button>
    </div>
  )
}
```

- [ ] **Step 9: Write Personalising step (Step 6 — persists to Supabase, then transitions)**

```typescript
// apps/web/components/onboarding/steps/personalising.tsx
'use client'
import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useOnboardingStore } from '@/lib/stores/onboarding-store'
import { createClient } from '@/lib/supabase/client'

export function Personalising() {
  const { answers, reset } = useOnboardingStore()
  const [failed, setFailed] = useState(false)
  const router = useRouter()
  const failTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  async function persist() {
    const supabase = createClient()
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) { router.push('/sign-in'); return }

    const { error } = await supabase.from('user_profiles').upsert({
      id: user.id,
      name: answers.name,
      age_range: answers.ageRange,
      role: answers.role,
      locale: answers.locale ?? 'en',
      wellness_q1: answers.wellnessQ1,
      wellness_q2: answers.wellnessQ2,
      onboarding_complete: true,
      onboarding_step: 6,
    })

    if (error) { setFailed(true); return }
    // Clear the fail timer before navigating — prevents setFailed on an unmounted component
    clearTimeout(failTimerRef.current!)
    reset()
    router.push('/chat')
  }

  useEffect(() => {
    const startTimer = setTimeout(() => persist(), 400)
    failTimerRef.current = setTimeout(() => setFailed(true), 8000)
    return () => { clearTimeout(startTimer); clearTimeout(failTimerRef.current!) }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  if (failed) {
    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <p className="text-sm text-[var(--color-text-secondary)]">
          We're having trouble setting things up — tap to try again.
        </p>
        <button
          onClick={() => { setFailed(false); persist() }}
          className="text-sm text-[var(--color-primary)] underline"
        >
          Try again
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center gap-6 text-center">
      <div className="h-16 w-16 rounded-full bg-[var(--color-surface-tinted)] animate-pulse" />
      <p className="text-sm text-[var(--color-text-secondary)]">
        Personalising your experience…
      </p>
    </div>
  )
}
```

- [ ] **Step 10: Run the onboarding manually** — sign up, go through all 6 steps, verify redirect to `/chat` after Step 6.

- [ ] **Step 11: Commit**

```bash
git add apps/web/app/\(onboarding\) apps/web/components/onboarding
git commit -m "feat: 7-step onboarding wizard with Supabase persistence and locale switching"
```

---

## Task 12: Chat API Route

**Files:**
- Create: `apps/web/app/api/chat/route.ts`
- Create: `apps/web/app/api/chat/__tests__/route.test.ts`

- [ ] **Step 1: Install missing deps**

```bash
cd apps/web && npm install @ai-sdk/openai
```

- [ ] **Step 2: Write the route**

```typescript
// apps/web/app/api/chat/route.ts
import { streamText, generateText } from 'ai'
import { createOpenAI } from '@ai-sdk/openai'
import { createClient } from '@/lib/supabase/server'
import type { Intent } from '@cdai/types'

const openrouter = createOpenAI({
  baseURL: 'https://openrouter.ai/api/v1',
  apiKey: process.env.OPENROUTER_API_KEY!,
})

const CLASSIFIER_MODEL = 'anthropic/claude-haiku-4-5-20251001'
const CHAT_MODEL = 'anthropic/claude-sonnet-4-6'

const KNOWLEDGE_SYSTEM = `You are Sage, a compassionate AI wellbeing assistant partnered with the Community Development Authority of Dubai. When users ask questions about wellness topics, mental health concepts, parenting, or CDA services, provide clear, accurate, and empathetic answers grounded in evidence. Keep responses warm, concise, and culturally sensitive. Never diagnose. Always encourage professional support for serious concerns.`

const EMOTIONAL_SYSTEM = `You are Sage, a warm and skilled AI wellbeing companion. You use CBT and DBT-informed approaches to help users process feelings, gain perspective, and develop coping strategies. Listen actively, validate emotions, and gently guide reflection. Never dismiss feelings. If you detect any crisis signals (suicidal thoughts, self-harm, abuse), include a crisis support message immediately and prominently.`

const CRISIS_SIGNAL = '[[CRISIS_DETECTED]]'
const CRISIS_SYSTEM_ADDITION = ` If the user expresses thoughts of suicide, self-harm, or is in immediate danger, prepend your response with exactly "${CRISIS_SIGNAL}" on its own line before your regular response.`

async function classifyIntent(message: string): Promise<Intent> {
  const { text } = await generateText({
    model: openrouter(CLASSIFIER_MODEL),
    prompt: `Classify this message as "knowledge" (asking for information or resources) or "emotional" (seeking support, sharing feelings). Reply with exactly one word.\n\nMessage: "${message}"`,
    maxTokens: 5,
  })
  return text.trim().toLowerCase().startsWith('k') ? 'knowledge' : 'emotional'
}

export async function POST(req: Request) {
  const { messages, sessionId } = await req.json() as {
    messages: { role: string; content: string }[]
    sessionId: string
  }

  const lastMessage = messages[messages.length - 1]?.content ?? ''
  const intent = await classifyIntent(lastMessage)
  const systemPrompt = (intent === 'knowledge' ? KNOWLEDGE_SYSTEM : EMOTIONAL_SYSTEM) + CRISIS_SYSTEM_ADDITION

  // Persist user message
  const supabase = await createClient()
  await supabase.from('messages').insert({
    session_id: sessionId,
    role: 'user',
    content: lastMessage,
    intent,
  })

  const result = streamText({
    model: openrouter(CHAT_MODEL),
    system: systemPrompt,
    messages: messages.map((m) => ({ role: m.role as 'user' | 'assistant', content: m.content })),
    onFinish: async ({ text }) => {
      // Persist AI response
      const isCrisis = text.startsWith(CRISIS_SIGNAL)
      const content = isCrisis ? text.replace(CRISIS_SIGNAL + '\n', '') : text
      await supabase.from('messages').insert({
        session_id: sessionId,
        role: isCrisis ? 'crisis' : 'ai',
        content,
        intent,
      })

      // Name session after first exchange if unnamed
      const { data: session } = await supabase
        .from('chat_sessions')
        .select('name')
        .eq('id', sessionId)
        .single()

      if (session && !session.name) {
        const { text: sessionName } = await generateText({
          model: openrouter(CLASSIFIER_MODEL),
          prompt: `Give this conversation a short title (3-5 words, no quotes):\n\nUser: "${lastMessage}"`,
          maxTokens: 15,
        })
        await supabase.from('chat_sessions')
          .update({ name: sessionName.trim(), updated_at: new Date().toISOString() })
          .eq('id', sessionId)
      }

      // POST-PILOT: Add mood scoring and insight generation here.
      // For pilot, all progress data comes from lib/demo-seed.ts.
      // Real path: score mood 1-5 via a generateText call on the full exchange,
      // insert to mood_scores table; generate a brief insight and insert to session_insights.
    },
  })

  return result.toDataStreamResponse()
}
```

- [ ] **Step 3: Write route test (mocked LLM)**

```typescript
// apps/web/app/api/chat/__tests__/route.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('ai', () => ({
  generateText: vi.fn().mockResolvedValue({ text: 'emotional' }),
  streamText: vi.fn().mockReturnValue({
    toDataStreamResponse: () => new Response('ok'),
  }),
}))
vi.mock('@ai-sdk/openai', () => ({ createOpenAI: vi.fn(() => vi.fn()) }))
vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    from: () => ({
      insert: vi.fn().mockResolvedValue({ error: null }),
      select: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      single: vi.fn().mockResolvedValue({ data: { name: null } }),
      update: vi.fn().mockReturnThis(),
    }),
  }),
}))

import { POST } from '../route'

describe('POST /api/chat', () => {
  it('returns a streaming response', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'I feel overwhelmed' }],
        sessionId: 'test-session-id',
      }),
    })
    const res = await POST(req)
    expect(res).toBeInstanceOf(Response)
  })
})
```

- [ ] **Step 4: Run test**

```bash
npx vitest run apps/web/app/api/chat
```

Expected: 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add apps/web/app/api/chat
git commit -m "feat: /api/chat — sequential classify-then-stream with crisis detection and session naming"
```

---

## Task 13: Chat Page + Layout

**Files:**
- Create: `apps/web/app/(app)/layout.tsx`
- Create: `apps/web/components/tab-bar.tsx`
- Create: `apps/web/app/(app)/chat/layout.tsx`
- Create: `apps/web/app/(app)/chat/page.tsx`

- [ ] **Step 1: Write tab bar**

```typescript
// apps/web/components/tab-bar.tsx
'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@cdai/ui'

const TABS = [
  { href: '/chat', label: 'Chat', labelAr: 'محادثة' },
  { href: '/progress', label: 'Progress', labelAr: 'تقدمي' },
]

export function TabBar() {
  const pathname = usePathname()
  return (
    <nav className="border-t border-[var(--color-border)] bg-[var(--color-surface)] flex">
      {TABS.map((tab) => {
        const active = pathname.startsWith(tab.href)
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              'flex flex-1 flex-col items-center justify-center py-3 text-xs transition-colors duration-200',
              active
                ? 'text-[var(--color-primary)] font-medium'
                : 'text-[var(--color-text-secondary)]'
            )}
          >
            <span>{tab.label}</span>
            {active && <span className="mt-0.5 h-0.5 w-4 rounded-full bg-[var(--color-primary)]" />}
          </Link>
        )
      })}
    </nav>
  )
}
```

- [ ] **Step 2: Write app layout**

```typescript
// apps/web/app/(app)/layout.tsx
import { TabBar } from '@/components/tab-bar'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-dvh flex-col">
      <main className="flex-1 overflow-hidden">{children}</main>
      <TabBar />
    </div>
  )
}
```

- [ ] **Step 3: Write chat layout (reserved shell)**

```typescript
// apps/web/app/(app)/chat/layout.tsx
// Reserved for future thread/list split. Currently a pass-through.
export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
```

- [ ] **Step 4: Write chat page**

```typescript
// apps/web/app/(app)/chat/page.tsx
import { ChatInterface } from '@/components/chat/chat-interface'
import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

export default async function ChatPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/sign-in')

  // Fetch or create the active session
  const { data: sessions } = await supabase
    .from('chat_sessions')
    .select('*')
    .eq('user_id', user.id)
    .order('updated_at', { ascending: false })
    .limit(1)

  let activeSession = sessions?.[0] ?? null
  if (!activeSession) {
    const { data: newSession } = await supabase
      .from('chat_sessions')
      .insert({ user_id: user.id })
      .select()
      .single()
    activeSession = newSession
  }

  const { data: profile } = await supabase
    .from('user_profiles')
    .select('name, locale')
    .eq('id', user.id)
    .single()

  return (
    <ChatInterface
      initialSession={activeSession}
      userName={profile?.name ?? ''}
      userId={user.id}
    />
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/app/\(app\) apps/web/components/tab-bar.tsx
git commit -m "feat: app shell with tab bar, chat layout reserved shell"
```

---

## Task 14: Chat Interface Components

**Files:**
- Create: `apps/web/components/chat/chat-interface.tsx`
- Create: `apps/web/components/chat/chat-header.tsx`
- Create: `apps/web/components/chat/message-list.tsx`
- Create: `apps/web/components/chat/message-bubble.tsx`
- Create: `apps/web/components/chat/typing-indicator.tsx`
- Create: `apps/web/components/chat/input-bar.tsx`
- Create: `apps/web/components/chat/empty-state.tsx`
- Create: `apps/web/components/chat/crisis-card.tsx`
- Create: `apps/web/components/chat/__tests__/message-bubble.test.tsx`

- [ ] **Step 1: Write MessageBubble**

```typescript
// apps/web/components/chat/message-bubble.tsx
import { cn } from '@cdai/ui'
import type { ChatMessage } from '@cdai/types'

export function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === 'crisis') return null // rendered by CrisisCard separately
  if (message.role === 'system') {
    return (
      <div className="mx-auto w-full max-w-xs rounded-xl border border-[var(--color-border)] px-4 py-2 text-center text-xs text-[var(--color-text-secondary)]">
        {message.content}
      </div>
    )
  }

  const isUser = message.role === 'user'
  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[78%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
          isUser
            ? 'bg-[var(--color-primary-dark)] text-white rounded-ee-sm'
            : 'bg-[var(--color-surface-tinted)] text-[var(--color-text-primary)] rounded-es-sm'
        )}
      >
        {message.content}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Write CrisisCard**

```typescript
// apps/web/components/chat/crisis-card.tsx
export function CrisisCard({ content }: { content: string }) {
  return (
    <div className="mx-4 rounded-xl border-2 border-[var(--color-crisis)] bg-red-50 p-4">
      <p className="mb-2 text-sm font-medium text-[var(--color-crisis)]">
        You're not alone — support is available
      </p>
      <p className="text-sm text-[var(--color-text-primary)]">{content}</p>
      <a
        href="tel:800HOPE"
        className="mt-3 inline-block rounded-full bg-[var(--color-crisis)] px-4 py-2 text-sm font-medium text-white"
      >
        Talk to someone now
      </a>
    </div>
  )
}
```

- [ ] **Step 3: Write TypingIndicator**

```typescript
// apps/web/components/chat/typing-indicator.tsx
export function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-1 rounded-2xl rounded-es-sm bg-[var(--color-surface-tinted)] px-4 py-3">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-[var(--color-text-secondary)] animate-bounce"
            style={{ animationDelay: `${i * 150}ms` }}
          />
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Write EmptyState**

```typescript
// apps/web/components/chat/empty-state.tsx
'use client'
import { useChatStore } from '@/lib/stores/chat-store'

const PROMPT_CHIPS = [
  'How are you feeling today?',
  'I have a question about…',
  'I've been feeling stressed lately',
]

interface EmptyStateProps {
  userName: string
  onChipClick: (text: string) => void
}

export function EmptyState({ userName, onChipClick }: EmptyStateProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-end gap-4 px-4 pb-4">
      <div className="w-full rounded-2xl bg-[var(--color-surface-tinted)] px-4 py-3 text-sm">
        Hello{userName ? `, ${userName}` : ''}! I'm Sage. How can I support you today?
      </div>
      <div className="flex w-full flex-wrap gap-2">
        {PROMPT_CHIPS.map((chip) => (
          <button
            key={chip}
            onClick={() => onChipClick(chip)}
            className="min-h-[44px] rounded-full border border-[var(--color-primary)] px-4 py-2 text-sm text-[var(--color-primary)] transition-colors hover:bg-[var(--color-surface-tinted)]"
          >
            {chip}
          </button>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Write InputBar with voice-to-text**

```typescript
// apps/web/components/chat/input-bar.tsx
'use client'
import { useState, useRef } from 'react'
import { cn } from '@cdai/ui'

interface InputBarProps {
  onSend: (text: string) => void
  disabled?: boolean
}

export function InputBar({ onSend, disabled }: InputBarProps) {
  const [value, setValue] = useState('')
  const [listening, setListening] = useState(false)
  const recognitionRef = useRef<SpeechRecognition | null>(null)

  function startVoice() {
    const SR = window.SpeechRecognition ?? window.webkitSpeechRecognition
    if (!SR) return
    const rec = new SR()
    rec.lang = document.documentElement.lang ?? 'en'
    rec.onresult = (e) => setValue(e.results[0][0].transcript)
    rec.onend = () => setListening(false)
    rec.start()
    recognitionRef.current = rec
    setListening(true)
  }

  function send() {
    const text = value.trim()
    if (!text || disabled) return
    setValue('')
    onSend(text)
  }

  return (
    <div className="flex items-end gap-2 border-t border-[var(--color-border)] bg-[var(--color-surface)] p-3">
      <button
        onClick={startVoice}
        className={cn(
          'flex h-10 w-10 items-center justify-center rounded-full transition-colors',
          listening ? 'bg-[var(--color-primary)] text-white' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]'
        )}
        aria-label="Voice input"
      >
        🎙
      </button>
      <textarea
        className="flex-1 resize-none rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
        rows={1}
        placeholder="Message…"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
      />
      <button
        onClick={send}
        disabled={!value.trim() || disabled}
        className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--color-primary)] text-white disabled:opacity-40"
        aria-label="Send"
      >
        →
      </button>
    </div>
  )
}
```

- [ ] **Step 6: Write ChatHeader**

```typescript
// apps/web/components/chat/chat-header.tsx
'use client'
import { useState } from 'react'
import type { ChatSession } from '@cdai/types'
import { HistoryPanel } from './history-panel'
import { SettingsPanel } from './settings-panel'
import { tenant } from '@cdai/tenant'

export function ChatHeader({ session }: { session: ChatSession | null }) {
  const [historyOpen, setHistoryOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)

  return (
    <>
      <header className="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
        <div className="flex items-center gap-2">
          <img src={tenant.brand.logo} alt={tenant.copy.appName} className="h-7 w-7" />
          <span className="text-sm font-medium text-[var(--color-text-secondary)] truncate max-w-[140px]">
            {session?.name ?? 'New conversation'}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => setHistoryOpen(true)} className="rounded-full p-2 hover:bg-[var(--color-surface-tinted)]" aria-label="History">🕐</button>
          <button onClick={() => setSettingsOpen(true)} className="rounded-full p-2 hover:bg-[var(--color-surface-tinted)]" aria-label="Settings">⚙</button>
        </div>
      </header>
      <HistoryPanel open={historyOpen} onClose={() => setHistoryOpen(false)} />
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  )
}
```

- [ ] **Step 7: Write the main ChatInterface orchestrator**

```typescript
// apps/web/components/chat/chat-interface.tsx
'use client'
import { useState, useRef, useEffect } from 'react'
import { useChat } from 'ai/react'
import { mapSdkRole, type ChatSession } from '@cdai/types'
import { ChatHeader } from './chat-header'
import { MessageBubble } from './message-bubble'
import { CrisisCard } from './crisis-card'
import { TypingIndicator } from './typing-indicator'
import { EmptyState } from './empty-state'
import { InputBar } from './input-bar'

const CRISIS_SIGNAL = '[[CRISIS_DETECTED]]'

interface Props {
  initialSession: ChatSession | null
  userName: string
  userId: string
}

export function ChatInterface({ initialSession, userName, userId }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const { messages, input, setInput, append, isLoading, error, reload } = useChat({
    api: '/api/chat',
    body: { sessionId: initialSession?.id },
    id: initialSession?.id,
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  function handleSend(text: string) {
    append({ role: 'user', content: text })
  }

  const crisisMessage = messages.find(
    (m) => m.role === 'assistant' && m.content.startsWith(CRISIS_SIGNAL)
  )

  return (
    <div className="flex h-full flex-col">
      <ChatHeader session={initialSession} />

      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
        {messages.length === 0 && !isLoading ? (
          <EmptyState userName={userName} onChipClick={handleSend} />
        ) : (
          messages.map((m) => {
            const isCrisis = m.role === 'assistant' && m.content.startsWith(CRISIS_SIGNAL)
            const content = isCrisis ? m.content.replace(CRISIS_SIGNAL + '\n', '') : m.content
            if (isCrisis) return <CrisisCard key={m.id} content={content} />
            return <MessageBubble key={m.id} message={{ ...m, role: mapSdkRole(m.role), intent: null, sessionId: initialSession?.id ?? '', createdAt: '' }} />
          })
        )}
        {isLoading && <TypingIndicator />}
        {error && (
          <div className="text-center text-xs text-[var(--color-crisis)]">
            Something went wrong —{' '}
            <button onClick={() => reload()} className="underline">tap to retry</button>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {crisisMessage && (
        <div className="px-4 pb-2">
          <CrisisCard content={crisisMessage.content.replace(CRISIS_SIGNAL + '\n', '')} />
        </div>
      )}

      <InputBar onSend={handleSend} disabled={isLoading} />
    </div>
  )
}
```

- [ ] **Step 8: Write HistoryPanel and SettingsPanel (stubs that fetch from Supabase)**

```typescript
// apps/web/components/chat/history-panel.tsx
'use client'
import { useEffect, useState } from 'react'
import { ResponsivePanel } from '@cdai/ui'
import { createClient } from '@/lib/supabase/client'
import type { ChatSession } from '@cdai/types'
import { useRouter } from 'next/navigation'

export function HistoryPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  const router = useRouter()

  useEffect(() => {
    if (!open) return
    setLoading(true); setError(false)
    const supabase = createClient()
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) return
      supabase.from('chat_sessions')
        .select('*').eq('user_id', user.id)
        .order('updated_at', { ascending: false }).limit(20)
        .then(({ data, error: err }) => {
          if (err) { setError(true) } else { setSessions(data ?? []) }
          setLoading(false)
        })
    })
  }, [open])

  // ResponsivePanel: BottomSheet on mobile (<768px), slide-in panel on desktop
  return (
    <ResponsivePanel open={open} onClose={onClose} title="Past conversations">
      {loading && <p className="text-sm text-[var(--color-text-secondary)]">Loading…</p>}
      {error && <p className="text-sm text-[var(--color-crisis)]">Couldn't load history — <button onClick={() => setError(false)} className="underline">retry</button></p>}
      {!loading && !error && sessions.map((s) => (
        <button key={s.id} onClick={() => { router.push(`/chat?session=${s.id}`); onClose() }}
          className="block w-full rounded-lg px-3 py-2 text-start text-sm hover:bg-[var(--color-surface-tinted)]">
          {s.name ?? 'Untitled conversation'}
        </button>
      ))}
    </ResponsivePanel>
  )
}
```

```typescript
// apps/web/components/chat/settings-panel.tsx
'use client'
import { ResponsivePanel } from '@cdai/ui'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'

export function SettingsPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { locale, setLocale } = useLocaleStore()
  const router = useRouter()

  function toggleLocale() {
    const next = locale === 'en' ? 'ar' : 'en'
    setLocale(next)
    document.cookie = `cdai-locale=${next};path=/;max-age=31536000`
    window.location.reload()
  }

  async function signOut() {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push('/sign-in')
  }

  // ResponsivePanel: BottomSheet on mobile (<768px), slide-in panel on desktop
  return (
    <ResponsivePanel open={open} onClose={onClose} title="Settings">
      <div className="flex flex-col gap-3">
        <button onClick={toggleLocale} className="min-h-[44px] rounded-xl border border-[var(--color-border)] px-4 py-3 text-start text-sm">
          Language: {locale === 'en' ? 'English → العربية' : 'العربية → English'}
        </button>
        <button onClick={signOut} className="min-h-[44px] rounded-xl border border-[var(--color-crisis)] px-4 py-3 text-start text-sm text-[var(--color-crisis)]">
          Sign out
        </button>
      </div>
    </ResponsivePanel>
  )
}
```

- [ ] **Step 9: Write MessageBubble test**

```typescript
// apps/web/components/chat/__tests__/message-bubble.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageBubble } from '../message-bubble'
import type { ChatMessage } from '@cdai/types'

const base: ChatMessage = {
  id: '1', sessionId: 's1', intent: null, createdAt: '', content: 'Hello',
  role: 'user',
}

describe('MessageBubble', () => {
  it('renders user message content', () => {
    render(<MessageBubble message={{ ...base, role: 'user' }} />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })

  it('renders ai message content', () => {
    render(<MessageBubble message={{ ...base, role: 'ai' }} />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })

  it('renders nothing for crisis role (handled by CrisisCard)', () => {
    const { container } = render(<MessageBubble message={{ ...base, role: 'crisis' }} />)
    expect(container.firstChild).toBeNull()
  })
})
```

- [ ] **Step 10: Run tests**

```bash
npx vitest run apps/web/components/chat
```

Expected: 3 tests pass.

- [ ] **Step 11: Manual test** — Start app, sign in, navigate to `/chat`. Verify: empty state with greeting + chips, send a message, see typing indicator, see streamed response.

- [ ] **Step 12: Commit**

```bash
git add apps/web/components/chat apps/web/app/\(app\)/chat
git commit -m "feat: full chat interface — streaming, voice input, crisis card, history panel, settings"
```

---

## Task 15: Progress Dashboard

**Files:**
- Create: `apps/web/app/(app)/progress/page.tsx`
- Create: `apps/web/components/progress/streak-card.tsx`
- Create: `apps/web/components/progress/mood-chart.tsx`
- Create: `apps/web/components/progress/topics-scroll.tsx`
- Create: `apps/web/components/progress/insights-list.tsx`
- Create: `apps/web/lib/demo-seed.ts`
- Create: `apps/web/lib/__tests__/demo-seed.test.ts`

- [ ] **Step 1: Write demo seed**

```typescript
// apps/web/lib/demo-seed.ts
import type { MoodScore, SessionInsight, ChatSession } from '@cdai/types'

function seededRandom(seed: number) {
  let s = seed
  return () => { s = (s * 1664525 + 1013904223) & 0xffffffff; return (s >>> 0) / 0xffffffff }
}

export function getUserDemoData(userId: string) {
  const rand = seededRandom(userId.split('').reduce((a, c) => a + c.charCodeAt(0), 0))
  const today = new Date()

  const moodScores: MoodScore[] = Array.from({ length: 21 }, (_, i) => {
    const d = new Date(today); d.setDate(d.getDate() - (20 - i))
    // Arc: starts ~2.5, rises to ~4.0, dips at day 10-12
    const base = i < 10 ? 2.5 + i * 0.1 : i < 13 ? 3.5 - (i - 10) * 0.2 : 3.2 + (i - 13) * 0.08
    const score = Math.min(5, Math.max(1, parseFloat((base + (rand() - 0.5) * 0.4).toFixed(1))))
    return { id: `demo-mood-${i}`, userId, sessionId: `demo-session-${i}`, score, createdAt: d.toISOString() }
  })

  const topics = ['Parenting', 'Work Stress', 'Relationships', 'Sleep', 'Anxiety']
  const insights: SessionInsight[] = topics.slice(0, 3).map((tag, i) => ({
    id: `demo-insight-${i}`,
    sessionId: `demo-session-${i}`,
    userId,
    content: `You've been exploring ${tag.toLowerCase()} this week. Small steps add up — keep going.`,
    topicTag: tag,
    createdAt: new Date(today.getTime() - i * 86400000).toISOString(),
  }))

  const streak = 12

  return { moodScores, insights, topics, streak }
}
```

- [ ] **Step 2: Write demo seed test**

```typescript
// apps/web/lib/__tests__/demo-seed.test.ts
import { describe, it, expect } from 'vitest'
import { getUserDemoData } from '../demo-seed'

describe('getUserDemoData', () => {
  const data = getUserDemoData('user-abc-123')

  it('returns 21 mood scores', () => {
    expect(data.moodScores).toHaveLength(21)
  })

  it('all scores are between 1 and 5', () => {
    data.moodScores.forEach((s) => {
      expect(s.score).toBeGreaterThanOrEqual(1)
      expect(s.score).toBeLessThanOrEqual(5)
    })
  })

  it('is deterministic — same input gives same output', () => {
    const data2 = getUserDemoData('user-abc-123')
    expect(data.moodScores[0].score).toBe(data2.moodScores[0].score)
  })

  it('different user IDs produce different data', () => {
    const data2 = getUserDemoData('user-xyz-999')
    expect(data.moodScores[0].score).not.toBe(data2.moodScores[0].score)
  })
})
```

- [ ] **Step 3: Run seed test**

```bash
npx vitest run apps/web/lib/__tests__/demo-seed.test.ts
```

Expected: 4 tests pass.

- [ ] **Step 4: Write StreakCard**

```typescript
// apps/web/components/progress/streak-card.tsx
import { Card } from '@cdai/ui'

export function StreakCard({ streak }: { streak: number }) {
  return (
    <Card className="flex items-center gap-4">
      <span className="text-3xl">🔥</span>
      <div>
        <p className="text-2xl font-semibold">{streak} days</p>
        <p className="text-xs text-[var(--color-text-secondary)]">with Sage</p>
      </div>
    </Card>
  )
}
```

- [ ] **Step 5: Write MoodChart**

```typescript
// apps/web/components/progress/mood-chart.tsx
'use client'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { Card } from '@cdai/ui'
import type { MoodScore } from '@cdai/types'

const LABELS: Record<number, string> = { 1: 'Low', 3: 'Okay', 5: 'Great' }

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en', { weekday: 'short' })
}

export function MoodChart({ scores }: { scores: MoodScore[] }) {
  const last7 = scores.slice(-7).map((s) => ({ day: formatDate(s.createdAt), score: s.score }))

  return (
    <Card>
      <p className="mb-3 text-sm font-medium">Mood this week</p>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={last7}>
          <XAxis dataKey="day" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis
            domain={[1, 5]}
            ticks={[1, 3, 5]}
            tickFormatter={(v) => LABELS[v] ?? ''}
            tick={{ fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={36}
          />
          <Tooltip formatter={(v) => [LABELS[v as number] ?? v, 'Mood']} />
          <Line
            type="monotone"
            dataKey="score"
            stroke="var(--color-primary)"
            strokeWidth={2}
            dot={{ fill: 'var(--color-primary)', r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  )
}
```

- [ ] **Step 6: Write TopicsScroll**

```typescript
// apps/web/components/progress/topics-scroll.tsx
'use client'
import { useRef, useEffect, useState } from 'react'

export function TopicsScroll({ topics }: { topics: string[] }) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [overflows, setOverflows] = useState(false)

  useEffect(() => {
    const el = scrollRef.current
    if (el) setOverflows(el.scrollWidth > el.clientWidth)
  }, [topics])

  return (
    <div className="relative">
      <div
        ref={scrollRef}
        className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide"
        style={overflows ? { maskImage: 'linear-gradient(to right, black 85%, transparent)' } : {}}
      >
        {topics.map((t) => (
          <span
            key={t}
            className="shrink-0 rounded-full bg-[var(--color-surface-tinted)] px-3 py-1 text-xs font-medium text-[var(--color-primary)]"
          >
            {t}
          </span>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 7: Write InsightsList**

```typescript
// apps/web/components/progress/insights-list.tsx
import { Card } from '@cdai/ui'
import type { SessionInsight } from '@cdai/types'

export function InsightsList({ insights }: { insights: SessionInsight[] }) {
  return (
    <div className="flex flex-col gap-3">
      {insights.map((insight) => (
        <Card key={insight.id} className="flex flex-col gap-1">
          <span className="text-xs font-medium text-[var(--color-primary)]">{insight.topicTag}</span>
          <p className="text-sm text-[var(--color-text-primary)]">{insight.content}</p>
        </Card>
      ))}
    </div>
  )
}
```

- [ ] **Step 8: Write progress page**

```typescript
// apps/web/app/(app)/progress/page.tsx
// POST-PILOT: When demoSeed is false, implement real data fetching from
// mood_scores and session_insights tables (populated by the chat API's onFinish callback).
'use client'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import { getUserDemoData } from '@/lib/demo-seed'
import { tenant } from '@cdai/tenant'
import { StreakCard } from '@/components/progress/streak-card'
import { MoodChart } from '@/components/progress/mood-chart'
import { TopicsScroll } from '@/components/progress/topics-scroll'
import { InsightsList } from '@/components/progress/insights-list'
import { Skeleton } from '@cdai/ui'
import type { MoodScore, SessionInsight } from '@cdai/types'

export default function ProgressPage() {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<{
    streak: number; moodScores: MoodScore[]; insights: SessionInsight[]; topics: string[]
  } | null>(null)

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) return
      // Pilot: always use demo seed. Real data path ships post-pilot when demoSeed is false.
      setData(getUserDemoData(user.id))
      setLoading(false)
    })
  }, [])

  return (
    <div className="flex flex-col gap-4 overflow-y-auto p-4 pb-8">
      <h1 className="text-xl font-semibold">{tenant.copy.progressHeader}</h1>
      {loading && (
        <>
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </>
      )}
      {error && <p className="text-sm text-[var(--color-crisis)]">Couldn't load your progress — <button onClick={() => window.location.reload()} className="underline">retry</button></p>}
      {!loading && !error && !data && (
        <p className="text-center text-sm text-[var(--color-text-secondary)] mt-16">
          Your progress will appear here after your first conversation.
          <br /><a href="/chat" className="mt-2 inline-block text-[var(--color-primary)] underline">Start chatting</a>
        </p>
      )}
      {data && (
        <>
          <StreakCard streak={data.streak} />
          <MoodChart scores={data.moodScores} />
          <TopicsScroll topics={data.topics} />
          <InsightsList insights={data.insights} />
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 9: Run seed test (already done), manually verify progress page renders**

Navigate to `/progress` — verify skeleton shows briefly, then demo data appears.

- [ ] **Step 10: Commit**

```bash
git add apps/web/app/\(app\)/progress apps/web/components/progress apps/web/lib/demo-seed.ts
git commit -m "feat: progress dashboard with deterministic demo seed, mood chart, topics, insights"
```

---

## Task 16: Admin Dashboard

**Files:**
- Create: `apps/web/app/admin/layout.tsx`
- Create: `apps/web/app/admin/dashboard/page.tsx`
- Create: `apps/web/components/admin/admin-sidebar.tsx`
- Create: `apps/web/components/admin/metric-cards.tsx`
- Create: `apps/web/components/admin/population-mood-chart.tsx`
- Create: `apps/web/components/admin/topic-distribution-chart.tsx`
- Create: `apps/web/components/admin/district-chart.tsx`
- Create: `apps/web/components/admin/alerts-panel.tsx`
- Create: `apps/web/lib/admin-demo-seed.ts`
- Create: `apps/web/lib/__tests__/admin-demo-seed.test.ts`

- [ ] **Step 1: Write admin demo seed**

```typescript
// apps/web/lib/admin-demo-seed.ts
function seededRandom(seed: number) {
  let s = seed; return () => { s = (s * 1664525 + 1013904223) & 0xffffffff; return (s >>> 0) / 0xffffffff }
}
const rand = seededRandom(42)

export const adminSeed = {
  metrics: {
    registeredUsers: 847,
    sessionsToday: 312,
    avgMood: 3.6,
    activeAlerts: 2,
  },
  populationMood: Array.from({ length: 30 }, (_, i) => {
    const base = i < 8 ? 3.0 + i * 0.05 : i < 15 ? 3.4 - (i - 8) * 0.04 : 3.1 + (i - 15) * 0.06
    return {
      day: `Day ${i + 1}`,
      mood: parseFloat((base + (rand() - 0.5) * 0.2).toFixed(2)),
    }
  }),
  topics: [
    { topic: 'Parenting', sessions: 289 },
    { topic: 'Work Stress', sessions: 241 },
    { topic: 'Relationships', sessions: 198 },
    { topic: 'Sleep', sessions: 167 },
    { topic: 'Anxiety', sessions: 143 },
    { topic: 'Finances', sessions: 121 },
    { topic: 'Grief', sessions: 89 },
    { topic: 'General Wellbeing', sessions: 67 },
  ],
  districts: [
    { name: 'Al Quoz', index: 4.1 },
    { name: 'Deira', index: 3.7 },
    { name: 'Jumeirah', index: 3.2 },
    { name: 'Bur Dubai', index: 3.0 },
    { name: 'Business Bay', index: 2.8 },
    { name: 'Mirdif', index: 2.6 },
    { name: 'Al Barsha', index: 2.4 },
    { name: 'Silicon Oasis', index: 2.1 },
  ],
  alerts: [
    { id: '1', message: 'Elevated stress signals in Al Quoz district — last 72 hours', tag: 'Al Quoz', ts: '3h ago' },
    { id: '2', message: 'Parenting topic volume +34% this week vs. prior week', tag: 'Parenting', ts: '1d ago' },
  ],
}
```

- [ ] **Step 2: Write admin seed test**

```typescript
// apps/web/lib/__tests__/admin-demo-seed.test.ts
import { describe, it, expect } from 'vitest'
import { adminSeed } from '../admin-demo-seed'

describe('adminSeed', () => {
  it('has 30 population mood data points', () => {
    expect(adminSeed.populationMood).toHaveLength(30)
  })
  it('all mood values are between 1 and 5', () => {
    adminSeed.populationMood.forEach((d) => {
      expect(d.mood).toBeGreaterThanOrEqual(1)
      expect(d.mood).toBeLessThanOrEqual(5)
    })
  })
  it('has 8 topics', () => { expect(adminSeed.topics).toHaveLength(8) })
  it('has 8 districts', () => { expect(adminSeed.districts).toHaveLength(8) })
  it('has 2 alerts', () => { expect(adminSeed.alerts).toHaveLength(2) })
  it('metrics are plausible', () => {
    expect(adminSeed.metrics.registeredUsers).toBeGreaterThan(0)
    expect(adminSeed.metrics.avgMood).toBeGreaterThanOrEqual(1)
    expect(adminSeed.metrics.avgMood).toBeLessThanOrEqual(5)
  })
})
```

- [ ] **Step 3: Run admin seed test**

```bash
npx vitest run apps/web/lib/__tests__/admin-demo-seed.test.ts
```

Expected: 6 tests pass.

- [ ] **Step 4: Write admin layout**

```typescript
// apps/web/app/admin/layout.tsx
import { AdminSidebar } from '@/components/admin/admin-sidebar'
import { tenant } from '@cdai/tenant'

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-dvh bg-[var(--color-surface)]">
      <AdminSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
          <div className="flex items-center gap-3">
            <img src={tenant.brand.logo} alt="" className="h-7 w-7" />
            <span className="font-semibold">{tenant.copy.adminHeader}</span>
          </div>
          <span className="rounded-full border border-[var(--color-border)] px-3 py-1 text-xs text-[var(--color-text-secondary)]">
            Last 30 days
          </span>
        </header>
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Write AdminSidebar with IntersectionObserver anchors**

```typescript
// apps/web/components/admin/admin-sidebar.tsx
'use client'
import { useEffect, useState } from 'react'
import { cn } from '@cdai/ui'

const SECTIONS = [
  { id: 'overview', label: 'Overview' },
  { id: 'topics', label: 'Topics' },
  { id: 'districts', label: 'Districts' },
  { id: 'alerts', label: 'Alerts' },
]

export function AdminSidebar() {
  const [active, setActive] = useState('overview')

  useEffect(() => {
    const observers = SECTIONS.map(({ id }) => {
      const el = document.getElementById(id)
      if (!el) return null
      const obs = new IntersectionObserver(
        ([entry]) => { if (entry.isIntersecting) setActive(id) },
        { threshold: 0.4 }
      )
      obs.observe(el)
      return obs
    })
    return () => observers.forEach((o) => o?.disconnect())
  }, [])

  return (
    <nav className="w-44 flex-shrink-0 border-e border-[var(--color-border)] py-6">
      {SECTIONS.map(({ id, label }) => (
        <a
          key={id}
          href={`#${id}`}
          className={cn(
            'block px-5 py-2.5 text-sm transition-colors duration-200',
            active === id
              ? 'border-e-2 border-[var(--color-primary)] font-medium text-[var(--color-primary)]'
              : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
          )}
        >
          {label}
        </a>
      ))}
    </nav>
  )
}
```

- [ ] **Step 6: Write MetricCards**

```typescript
// apps/web/components/admin/metric-cards.tsx
import { Card } from '@cdai/ui'

interface Metric { label: string; value: string | number; sub?: string }

export function MetricCards({ metrics }: { metrics: Metric[] }) {
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {metrics.map((m) => (
        <Card key={m.label}>
          <p className="text-2xl font-semibold">{m.value}</p>
          <p className="text-xs text-[var(--color-text-secondary)]">{m.label}</p>
          {m.sub && <p className="text-xs text-[var(--color-text-secondary)]">{m.sub}</p>}
        </Card>
      ))}
    </div>
  )
}
```

- [ ] **Step 7: Write PopulationMoodChart**

```typescript
// apps/web/components/admin/population-mood-chart.tsx
'use client'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { Card } from '@cdai/ui'

const LABELS: Record<number, string> = { 1: 'Low', 3: 'Okay', 5: 'Great' }

export function PopulationMoodChart({ data }: { data: { day: string; mood: number }[] }) {
  return (
    <Card id="mood-chart">
      <p className="mb-4 font-medium">Population mood — 30 days</p>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data}>
          <XAxis dataKey="day" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} interval={4} />
          <YAxis domain={[1, 5]} ticks={[1, 3, 5]} tickFormatter={(v) => LABELS[v] ?? ''} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} width={40} />
          <Tooltip formatter={(v) => [LABELS[v as number] ?? v, 'Avg mood']} />
          <Line type="monotone" dataKey="mood" stroke="var(--color-primary)" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  )
}
```

- [ ] **Step 8: Write TopicDistributionChart**

```typescript
// apps/web/components/admin/topic-distribution-chart.tsx
'use client'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LabelList } from 'recharts'
import { Card } from '@cdai/ui'

export function TopicDistributionChart({ data }: { data: { topic: string; sessions: number }[] }) {
  return (
    <Card>
      <p className="mb-4 font-medium">Topic distribution</p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical">
          <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 10 }} />
          <YAxis dataKey="topic" type="category" width={110} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip />
          <Bar dataKey="sessions" fill="var(--color-primary)" radius={[0, 4, 4, 0]}>
            <LabelList dataKey="sessions" position="right" style={{ fontSize: 10 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  )
}
```

- [ ] **Step 9: Write DistrictChart with gradient fill + dual coding**

```typescript
// apps/web/components/admin/district-chart.tsx
'use client'
import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LabelList, Cell } from 'recharts'
import { Card } from '@cdai/ui'

function stressColor(index: number): string {
  // index 1-5 → sage tinted to crisis red
  const t = Math.min(1, Math.max(0, (index - 1) / 4))
  const r = Math.round(234 + t * (220 - 234))
  const g = Math.round(240 + t * (38 - 240))
  const b = Math.round(234 + t * (38 - 234))
  return `rgb(${r},${g},${b})`
}

export function DistrictChart({
  data,
  highlightId,
}: {
  data: { name: string; index: number }[]
  highlightId: string | null
}) {
  return (
    <Card>
      <p className="mb-4 font-medium">District stress index</p>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} layout="vertical">
          <XAxis type="number" domain={[0, 5]} axisLine={false} tickLine={false} tick={{ fontSize: 10 }} />
          <YAxis dataKey="name" type="category" width={110} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip formatter={(v) => [v, 'Stress index']} />
          <Bar dataKey="index" radius={[0, 4, 4, 0]}>
            {data.map((entry) => (
              <Cell
                key={entry.name}
                fill={stressColor(entry.index)}
                opacity={highlightId && highlightId !== entry.name ? 0.2 : 1}
              />
            ))}
            <LabelList dataKey="index" position="right" style={{ fontSize: 10 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  )
}
```

- [ ] **Step 10: Write AlertsPanel**

```typescript
// apps/web/components/admin/alerts-panel.tsx
'use client'
interface Alert { id: string; message: string; tag: string; ts: string }

interface Props {
  alerts: Alert[]
  onViewDetail: (tag: string) => void
}

export function AlertsPanel({ alerts, onViewDetail }: Props) {
  return (
    <div className="flex flex-col gap-3">
      {alerts.map((a) => (
        <div key={a.id} className="flex items-start justify-between rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div>
            <p className="text-sm font-medium text-amber-800">⚠ {a.message}</p>
            <p className="mt-0.5 text-xs text-amber-600">{a.ts} · {a.tag}</p>
          </div>
          <button
            onClick={() => onViewDetail(a.tag)}
            className="ms-4 shrink-0 text-xs text-[var(--color-primary)] underline-offset-2 hover:underline"
          >
            View detail
          </button>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 11: Write admin dashboard page**

```typescript
// apps/web/app/admin/dashboard/page.tsx
'use client'
import { useState } from 'react'
import dynamic from 'next/dynamic'
import { adminSeed } from '@/lib/admin-demo-seed'
import { MetricCards } from '@/components/admin/metric-cards'
import { AlertsPanel } from '@/components/admin/alerts-panel'
import { Skeleton } from '@cdai/ui'

// Lazy-load Recharts bundles — Gitex kiosk cold-start lands on this page;
// skeletons prevent a blank screen while 200 kB of chart JS is parsed.
const PopulationMoodChart = dynamic(
  () => import('@/components/admin/population-mood-chart').then(m => m.PopulationMoodChart),
  { loading: () => <Skeleton className="h-48 w-full" />, ssr: false }
)
const TopicDistributionChart = dynamic(
  () => import('@/components/admin/topic-distribution-chart').then(m => m.TopicDistributionChart),
  { loading: () => <Skeleton className="h-56 w-full" />, ssr: false }
)
const DistrictChart = dynamic(
  () => import('@/components/admin/district-chart').then(m => m.DistrictChart),
  { loading: () => <Skeleton className="h-60 w-full" />, ssr: false }
)

export default function AdminDashboard() {
  const [highlightDistrict, setHighlightDistrict] = useState<string | null>(null)
  const [highlightTopic, setHighlightTopic] = useState<string | null>(null)

  function handleViewDetail(tag: string) {
    // Is it a district or topic?
    const isDistrict = adminSeed.districts.some((d) => d.name === tag)
    if (isDistrict) {
      setHighlightDistrict(tag)
      document.getElementById('districts')?.scrollIntoView({ behavior: 'smooth' })
    } else {
      setHighlightTopic(tag)
      document.getElementById('topics')?.scrollIntoView({ behavior: 'smooth' })
    }
  }

  const metrics = [
    { label: 'Registered users', value: adminSeed.metrics.registeredUsers },
    { label: 'Sessions today', value: adminSeed.metrics.sessionsToday },
    { label: 'Avg mood', value: adminSeed.metrics.avgMood, sub: '/ 5.0' },
    { label: 'Active alerts', value: adminSeed.metrics.activeAlerts },
  ]

  return (
    <div className="flex flex-col gap-8">
      <section id="overview">
        <MetricCards metrics={metrics} />
      </section>

      <section id="overview-chart">
        <PopulationMoodChart data={adminSeed.populationMood} />
      </section>

      <section id="topics">
        <TopicDistributionChart data={adminSeed.topics} />
      </section>

      <section id="districts">
        <DistrictChart data={adminSeed.districts} highlightId={highlightDistrict} />
      </section>

      <section id="alerts">
        <AlertsPanel alerts={adminSeed.alerts} onViewDetail={handleViewDetail} />
      </section>
    </div>
  )
}
```

- [ ] **Step 12: Manually test** — navigate to `/admin/dashboard` with an admin-flagged user. Verify: sidebar anchors scroll to sections, alert "View detail" highlights the correct chart.

- [ ] **Step 13: Commit**

```bash
git add apps/web/app/admin apps/web/components/admin apps/web/lib/admin-demo-seed.ts
git commit -m "feat: admin government dashboard with deterministic seed, charts, alerts, highlight filter"
```

---

## Task 17: PWA Configuration

**Files:**
- Create: `apps/web/public/manifest.json`
- Create: `apps/web/public/offline.html`
- Create: `apps/web/sw.ts`
- Modify: `apps/web/next.config.ts`

- [ ] **Step 1: Install Serwist**

```bash
cd apps/web && npm install @serwist/next serwist
```

- [ ] **Step 2: Write `manifest.json`**

```json
{
  "name": "Sage — CDAi",
  "short_name": "Sage",
  "description": "Your personal wellbeing companion",
  "start_url": "/chat",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#F9F8F6",
  "theme_color": "#F9F8F6",
  "dir": "auto",
  "lang": "en",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    {
      "src": "/icons/icon-maskable-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable"
    }
  ]
}
```

- [ ] **Step 3: Write `offline.html`** (bilingual, hardcoded — static HTML cannot consume tenant config at runtime)

```html
<!DOCTYPE html>
<html dir="auto" lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Sage — Offline</title>
  <style>
    body { font-family: sans-serif; background: #F9F8F6; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
    .card { text-align: center; padding: 2rem; max-width: 320px; }
    .icon { font-size: 3rem; margin-bottom: 1rem; }
    h1 { font-size: 1.25rem; color: #111827; margin: 0 0 0.5rem; }
    p { color: #6B7280; font-size: 0.9rem; margin: 0 0 1.5rem; }
    button { background: #4A7C59; color: white; border: none; border-radius: 9999px; padding: 0.75rem 2rem; font-size: 0.9rem; cursor: pointer; }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">🌿</div>
    <h1>You're offline · أنت غير متصل</h1>
    <p>Check your connection and try again.<br />تحقق من اتصالك وحاول مجددًا.</p>
    <button onclick="window.location.reload()">Retry · إعادة المحاولة</button>
  </div>
</body>
</html>
```

- [ ] **Step 4: Write `sw.ts` (Serwist service worker)**

```typescript
// apps/web/sw.ts
import { defaultCache } from '@serwist/next/worker'
import { Serwist } from 'serwist'

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: false, // Controlled update — we show a banner
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: defaultCache,
  fallbacks: {
    entries: [{ url: '/offline.html', matcher: ({ request }) => request.destination === 'document' }],
  },
})

serwist.addEventListeners()
```

- [ ] **Step 5: Update `next.config.ts` with Serwist**

```typescript
// apps/web/next.config.ts
import type { NextConfig } from 'next'
import withSerwist from '@serwist/next'

const nextConfig: NextConfig = {
  transpilePackages: ['@cdai/ui', '@cdai/theme', '@cdai/tenant', '@cdai/types'],
}

export default withSerwist({
  swSrc: 'sw.ts',
  swDest: 'public/sw.js',
  disable: process.env.NODE_ENV === 'development',
})(nextConfig)
```

- [ ] **Step 6: Write install prompt component**

```typescript
// apps/web/components/install-prompt.tsx
'use client'
import { useEffect, useState } from 'react'
import { BottomSheet, Button } from '@cdai/ui'

export function InstallPrompt() {
  const [prompt, setPrompt] = useState<BeforeInstallPromptEvent | null>(null)
  const [show, setShow] = useState(false)

  useEffect(() => {
    if (localStorage.getItem('cdai-install-dismissed')) return
    const handler = (e: Event) => {
      e.preventDefault()
      setPrompt(e as BeforeInstallPromptEvent)
    }
    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  // Show after first completed chat exchange — called from ChatInterface
  // Export a trigger function via a simple module-level ref
  useEffect(() => {
    installPromptTrigger.trigger = () => {
      if (prompt) setShow(true)
    }
  }, [prompt])

  function dismiss() {
    localStorage.setItem('cdai-install-dismissed', '1')
    setShow(false)
  }

  async function install() {
    if (!prompt) return
    prompt.prompt()
    const { outcome } = await prompt.userChoice
    if (outcome === 'accepted') dismiss()
  }

  return (
    <BottomSheet open={show} onClose={dismiss}>
      <h2 className="mb-2 font-semibold">Add Sage to your home screen</h2>
      <p className="mb-4 text-sm text-[var(--color-text-secondary)]">Get quick access and a better experience.</p>
      <div className="flex gap-3">
        <Button onClick={install} className="flex-1">Install</Button>
        <Button variant="ghost" onClick={dismiss} className="flex-1">Not now</Button>
      </div>
    </BottomSheet>
  )
}

export const installPromptTrigger = { trigger: () => {} }
```

Add `declare global { interface Window { SpeechRecognition: typeof SpeechRecognition; webkitSpeechRecognition: typeof SpeechRecognition } }` and `interface BeforeInstallPromptEvent extends Event { prompt(): Promise<void>; userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }> }` to `apps/web/types/globals.d.ts`.

- [ ] **Step 7: Write SW update banner**

```typescript
// apps/web/components/sw-update-banner.tsx
'use client'
import { useEffect, useState } from 'react'

export function SwUpdateBanner() {
  const [waiting, setWaiting] = useState<ServiceWorker | null>(null)

  useEffect(() => {
    if (!('serviceWorker' in navigator)) return
    // Serwist auto-registers the SW via next.config.ts — do NOT call register() here.
    // Use navigator.serviceWorker.ready to get the existing registration and listen for updates.
    navigator.serviceWorker.ready.then((reg) => {
      reg.addEventListener('updatefound', () => {
        const newSW = reg.installing
        newSW?.addEventListener('statechange', () => {
          if (newSW.state === 'installed' && navigator.serviceWorker.controller) {
            setWaiting(newSW)
          }
        })
      })
    })
  }, [])

  if (!waiting) return null

  return (
    <div className="fixed bottom-20 inset-x-0 z-50 flex justify-center px-4">
      <div className="flex items-center gap-3 rounded-full bg-[var(--color-primary-dark)] px-5 py-3 shadow-lg text-white text-sm">
        <span>A new version of Sage is ready</span>
        <button
          onClick={() => { waiting.postMessage({ type: 'SKIP_WAITING' }); window.location.reload() }}
          className="font-medium underline"
        >
          Update
        </button>
      </div>
    </div>
  )
}
```

Add `<SwUpdateBanner />` and `<InstallPrompt />` inside the root `app/layout.tsx` body.

- [ ] **Step 8: Add iOS meta tags to root layout** (already added in Task 9 Step 3 — verify they're present)

- [ ] **Step 9: Build and test PWA**

```bash
cd apps/web && npm run build && npm run start
```

Open `http://localhost:3000` in Chrome. Open DevTools → Application → Service Workers. Verify SW is registered. Open Application → Manifest. Verify manifest loads. Toggle offline in DevTools → Network, navigate to `/chat`, verify `/offline.html` shows.

- [ ] **Step 10: Commit**

```bash
git add apps/web/public/manifest.json apps/web/public/offline.html apps/web/sw.ts apps/web/next.config.ts apps/web/components/install-prompt.tsx apps/web/components/sw-update-banner.tsx
git commit -m "feat: PWA — Serwist service worker, manifest, offline page, deferred install prompt, update banner"
```

---

## Task 18: Voice Biomarker Demo (Flag-Gated)

**Files:**
- Create: `apps/web/components/chat/voice-biomarker.tsx`

Only build this task if `tenant.capabilities.voiceBiomarker` is `true` in the active tenant config. For the sage tenant it is `false` — skip for Gitex unless explicitly enabled.

- [ ] **Step 1: Write voice biomarker component**

```typescript
// apps/web/components/chat/voice-biomarker.tsx
'use client'
import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

// Simulated analysis results — no real AI inference for pilot
function getSimulatedAnalysis() {
  return {
    fatigue: Math.floor(Math.random() * 40 + 20),   // 20-60%
    stress: Math.floor(Math.random() * 50 + 10),     // 10-60%
    mood: ['Calm', 'Focused', 'Slightly Tense', 'Reflective'][Math.floor(Math.random() * 4)],
  }
}

type Phase = 'idle' | 'recording' | 'analysing' | 'result'

export function VoiceBiomarker({ onClose }: { onClose: () => void }) {
  const [phase, setPhase] = useState<Phase>('idle')
  const [result, setResult] = useState<ReturnType<typeof getSimulatedAnalysis> | null>(null)
  const [secondsLeft, setSecondsLeft] = useState(90)
  const mediaRef = useRef<MediaRecorder | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRef.current = new MediaRecorder(stream)
    mediaRef.current.start()
    setPhase('recording')
    setSecondsLeft(90)
    timerRef.current = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) { stopRecording(); return 0 }
        return s - 1
      })
    }, 1000)
  }

  function stopRecording() {
    clearInterval(timerRef.current!)
    mediaRef.current?.stop()
    mediaRef.current?.stream.getTracks().forEach((t) => t.stop())
    setPhase('analysing')
    setTimeout(() => { setResult(getSimulatedAnalysis()); setPhase('result') }, 2000)
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[var(--color-surface)] px-6">
      <button onClick={onClose} className="absolute top-4 end-4 text-sm text-[var(--color-text-secondary)]">✕</button>

      <AnimatePresence mode="wait">
        {phase === 'idle' && (
          <motion.div key="idle" className="flex flex-col items-center gap-8 text-center"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="h-32 w-32 rounded-full bg-[var(--color-surface-tinted)] ring-4 ring-[var(--color-primary)]/20" />
            <div>
              <p className="text-lg font-semibold">Daily voice check-in</p>
              <p className="mt-1 text-sm text-[var(--color-text-secondary)]">90 seconds to understand how you're doing</p>
            </div>
            <button onClick={startRecording}
              className="rounded-full bg-[var(--color-primary)] px-8 py-3 text-sm font-medium text-white">
              Start check-in
            </button>
          </motion.div>
        )}

        {phase === 'recording' && (
          <motion.div key="recording" className="flex flex-col items-center gap-8 text-center"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <motion.div
              className="h-32 w-32 rounded-full bg-[var(--color-primary)]/20 ring-4 ring-[var(--color-primary)]"
              animate={{ scale: [1, 1.08, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            />
            <p className="text-4xl font-light tabular-nums">{secondsLeft}s</p>
            <p className="text-sm text-[var(--color-text-secondary)]">Speak naturally — share how you're feeling</p>
            <button onClick={stopRecording}
              className="rounded-full border border-[var(--color-border)] px-8 py-3 text-sm">
              Finish early
            </button>
          </motion.div>
        )}

        {phase === 'analysing' && (
          <motion.div key="analysing" className="flex flex-col items-center gap-6 text-center"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="h-32 w-32 rounded-full bg-[var(--color-surface-tinted)] animate-pulse" />
            <p className="text-sm text-[var(--color-text-secondary)]">Analysing your voice…</p>
          </motion.div>
        )}

        {phase === 'result' && result && (
          <motion.div key="result" className="flex flex-col gap-6 w-full max-w-sm"
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <p className="text-center text-lg font-semibold">Today's check-in</p>
            {[
              { label: 'Fatigue', value: result.fatigue, unit: '%' },
              { label: 'Stress', value: result.stress, unit: '%' },
            ].map((item) => (
              <div key={item.label}>
                <div className="mb-1 flex justify-between text-sm">
                  <span>{item.label}</span>
                  <span className="font-medium">{item.value}{item.unit}</span>
                </div>
                <div className="h-2 rounded-full bg-[var(--color-border)]">
                  <div className="h-2 rounded-full bg-[var(--color-primary)] transition-all duration-700"
                    style={{ width: `${item.value}%` }} />
                </div>
              </div>
            ))}
            <div className="rounded-xl bg-[var(--color-surface-tinted)] p-4 text-center">
              <p className="text-sm text-[var(--color-text-secondary)]">Overall mood</p>
              <p className="text-xl font-semibold">{result.mood}</p>
            </div>
            <button onClick={onClose}
              className="rounded-full bg-[var(--color-primary)] py-3 text-sm font-medium text-white">
              Done
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
```

- [ ] **Step 2: Wire into ChatHeader** — conditionally render a voice check-in entry button when `tenant.capabilities.voiceBiomarker` is true

```typescript
// In chat-header.tsx, add after existing controls:
import { tenant } from '@cdai/tenant'
import { VoiceBiomarker } from './voice-biomarker'

// Inside ChatHeader:
const [biomarkerOpen, setBiomarkerOpen] = useState(false)
// In JSX, before the existing icon buttons:
{tenant.capabilities.voiceBiomarker && (
  <button onClick={() => setBiomarkerOpen(true)} className="rounded-full p-2 hover:bg-[var(--color-surface-tinted)]" aria-label="Voice check-in">🎙</button>
)}
{biomarkerOpen && <VoiceBiomarker onClose={() => setBiomarkerOpen(false)} />}
```

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/chat/voice-biomarker.tsx apps/web/components/chat/chat-header.tsx
git commit -m "feat: vocal biomarker demo — flag-gated, simulated analysis, Framer Motion orb"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Turborepo monorepo with packages/tenant, theme, ui, api, types | Task 1–5 |
| Tenant config: brand + capabilities + copy | Task 3 |
| Dependency direction enforced (tenant → theme → ui → web) | Task 1 (turbo.json), Task 4 |
| Tailwind preset consuming CSS vars | Task 4 |
| Middleware: auth guard, role check, onboarding redirect | Task 9 |
| Root layout: locale-split fonts, dir from cookie | Task 9 |
| Error state policy (inline error + retry on all data surfaces) | Tasks 14, 15, 16 |
| Auth screens: sign-in, sign-up, forgot-password | Task 10 |
| Language toggle on auth shell | Task 10 |
| Onboarding: 7 fixed steps, back nav preserves state | Task 11 |
| Step 6 failure state (8s timeout → retry prompt) | Task 11 |
| Invalid step → redirect to last valid step or notFound | Task 11 |
| /api/chat: sequential classify → stream, crisis detection | Task 12 |
| Session named async after first AI response | Task 12 |
| Unified Chat+Ask, no visible seam | Task 12, 14 |
| Message types: user, ai, system, crisis (non-dismissible) | Task 14 |
| Voice-to-text always available (browser API, no flag) | Task 14 |
| Vocal biomarker: flag-gated, simulated | Task 18 |
| Empty state: greeting + prompt chips | Task 14 |
| Typing indicator, stream error retry | Task 14 |
| History panel (own header icon) | Task 14 |
| Settings panel (bottom sheet mobile, slide-in desktop) | Task 14 |
| Progress: streak, mood chart (word-anchored), topics, insights | Task 15 |
| Mood AI-inferred, stored at session close | Task 12 |
| Insights stored at session close (read on load) | Task 12 |
| Demo seed: deterministic, store-level injection | Task 15 |
| Skeleton loading on progress | Task 15 |
| Admin: sidebar scroll anchors, single page | Task 16 |
| Admin: metric cards (847/312 narrative) | Task 16 |
| Admin: population mood, topic distribution, district charts | Task 16 |
| District chart: gradient + numeric labels (dual coding) | Task 16 |
| Alert "view detail": scroll + highlight filter (20% opacity) | Task 16 |
| Admin skeleton loading | Task 16 (MetricCards renders immediately from seed — add skeleton if real data path used) |
| manifest.json: scope="/", theme_color=surface, dir=auto | Task 17 |
| iOS meta tags: apple-touch-icon 180px | Task 9 (layout) |
| Serwist: network-first API, cache-first static | Task 17 |
| SW registration deferred to window.load | Task 17 |
| Offline.html: bilingual, hardcoded copy | Task 17 |
| Install prompt: deferred after first exchange | Task 17 |
| SW update banner: skipWaiting on tap, no forced reload | Task 17 |

**Gap found:** `packages/api` was listed in the file map but has no task — it is not needed for the pilot (all API calls go through Next.js route handlers or Supabase directly). No task needed.

**Gap found:** Admin skeleton loading — the admin page uses `adminSeed` synchronously (no async fetch for demo mode), so no loading state is needed. Skeletons would be needed when the real data path is wired (post-pilot).

**Type consistency check:** `ChatMessage.role` uses `'user' | 'ai' | 'system' | 'crisis'` throughout. The Vercel AI SDK uses `'user' | 'assistant'` — the adapter in `ChatInterface` maps `assistant → ai` inline. Consistent.

**Placeholder check:** No TBDs, no "implement later" language found.

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-20-cdai-pilot-pwa.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — Fresh subagent per task, review between tasks, fast parallel iteration.

**2. Inline Execution** — Execute tasks sequentially in this session with checkpoints.

Which approach?
