import type { Source } from '@cdai/types'

// ─── COPY REGISTRY — source-card affordance labels ──────────────────────────
// Lightweight copy registry (per the source-card-labels spec, Condition 2): one
// sign-off line per string set. No approval-less hardcoded UI copy.
//
// EN — SIGNED OFF: clinical ruling 2026-07-07 (Rohan Sarda, clinical lead). Register
//   MSA-leaning (ratified-pending-native-review): a heading over resource cards is UI
//   chrome, same class as button/settings copy. "Further reading", never "Sources"
//   (citation register) or "Recommended" (implies clinical endorsement).
// AR — PENDING native Emirati + real-RTL review (Condition 1, HARD GATE). Do NOT ship a
//   guessed Arabic string. Values stay null until reviewed; the component renders NO visible
//   heading for a null (cards render as today for AR users), so EN ships value without
//   fabricating Arabic. Enter reviewed values here with a sign-off line (reviewer + date).
// ────────────────────────────────────────────────────────────────────────────

type LabelKey = 'reading' | 'watch' | 'mixed'

const LABELS: Record<'en' | 'ar', Record<LabelKey, string | null>> = {
  en: { reading: 'Further reading', watch: 'Watch', mixed: 'Learn more' },
  ar: { reading: null, watch: null, mixed: null }, // placeholders — pending native review
}

/** Deterministic label key from the ACTUAL card types — cannot mislabel (the whole point). */
export function sourceLabelKey(sources: Source[]): LabelKey {
  const hasVideo = sources.some((s) => s.type === 'video')
  const hasArticle = sources.some((s) => s.type === 'article')
  if (hasVideo && hasArticle) return 'mixed'
  return hasVideo ? 'watch' : 'reading'
}

/** Resolved visible heading, or null when no reviewed copy exists for the locale. */
export function sourceLabel(sources: Source[], locale: 'en' | 'ar'): string | null {
  if (!sources || sources.length === 0) return null
  const key = sourceLabelKey(sources)
  return (LABELS[locale] ?? LABELS.en)[key] ?? null
}

/** Human-readable source domain for attribution (e.g. "nimh.nih.gov"), or '' if unparseable.
 *  Gives each card a meaningful source line (what ChatGPT/Abby show) from data we already have. */
export function sourceDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}
