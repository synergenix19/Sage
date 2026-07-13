// ─── CRISIS CONTACTS — single frontend source ───────────────────────────────
// Mirrors the backend source `sage_poc.config.CRISIS_RESOURCES` (H4, PR #288). Every crisis surface
// (crisis card, persistent "Get help now" affordance, onboarding) reads from HERE — no re-embedded
// literals. Change in ONE place per stack; never inline. The cross-stack parity test
// (sage-poc/tests/test_crisis_config_cross_stack.py) asserts this array == backend CRISIS_RESOURCES.
//
// ✅ VALUE STATUS — DOC COMPOSITION (H4 value flip). These VALUES now mirror the backend's adopted
// directory (sage_poc.config.CRISIS_RESOURCES): National Mental Support Line 800-HOPE (800-4673),
// 8am-8pm daily (NOT 24/7); 999; Abu Dhabi 800-SAKINA (800-725462) 24/7; DHA 800 111 24/7; Sharjah
// youth 800 51115 9am-5pm; nearest ER. This SUPERSEDES the pre-flip MoHAP 800 46342 / 24/7 set (the
// GL-1 reversal: 46342-vs-4673 resolved in favour of 4673 by the 2026-07-10 dial-test + clinician
// sign-off). The National line is 8am-8pm, so it must NEVER be shown as a lone or 24/7 number: the
// lead-logic below always keeps 999 + a 24/7 line inline (top-3 safety invariant).
// COORDINATED DEPLOY: this flip makes the frontend show 4673 — it must ship AFTER PR #301 (the
// multi-resource card) and WITH backend PR #288 (the mirrored config), never alone. The cross-stack
// parity test (sage-poc) keeps both sides entry-for-entry honest. Change values in ONE place per
// stack (this array + backend config); never inline.

export type CrisisScope = 'national' | 'emergency' | (string & {})

export interface CrisisResource {
  /** English label — MUST equal the backend resource `name` (cross-stack parity). */
  labelEn: string
  /** Arabic label — frontend-only (backend carries a single English `name`). */
  labelAr: string
  /** Displayed number, exactly as dialled visually (e.g. "800 46342"). */
  number: string
  /** RFC 3966 tel: URI. Spaces/hyphens are equivalent; derived from `number`. */
  tel: string
  /** "24/7" or a daily window like "8am-8pm". Drives hours-aware lead-logic. */
  hours: string
  /** Lead-logic bucket. "emergency" (999) always present; "national" leads by day. */
  scope: CrisisScope
}

// Static fallback, ORDERED to mirror backend CRISIS_RESOURCES exactly (same entries, same order).
// When the server sends an ordered list (Phase 2, X-Sage-Crisis-State payload) the client uses that;
// until then it runs `selectCrisisResources` over this array. Rendered fully client-side for the
// persistent affordance so a slow/down backend never leaves a user without numbers.
export const CRISIS_RESOURCES: readonly CrisisResource[] = [
  {
    labelEn: 'National Mental Support Line',
    labelAr: 'خط الدعم النفسي الوطني',
    number: '800-HOPE (800-4673)',
    tel: 'tel:800-4673', // vanity number 800-HOPE dials 800-4673
    hours: '8am–8pm daily',
    scope: 'national',
  },
  {
    labelEn: 'Emergency Services',
    labelAr: 'خدمات الطوارئ',
    number: '999',
    tel: 'tel:999',
    hours: '24/7',
    scope: 'emergency',
  },
  {
    labelEn: 'Abu Dhabi 24/7 crisis line',
    labelAr: 'خط سكينة للأزمات – أبوظبي',
    number: '800-SAKINA (800-725462)',
    tel: 'tel:800-725462', // vanity number 800-SAKINA dials 800-725462
    hours: '24/7',
    scope: 'regional',
  },
  {
    labelEn: 'Dubai Health Authority helpline',
    labelAr: 'خط هيئة الصحة بدبي للمساعدة',
    number: '800 111',
    tel: 'tel:800-111',
    hours: '24/7',
    scope: 'regional',
  },
  {
    labelEn: 'Sharjah Child & Youth Mental Health Helpline',
    labelAr: 'خط الشارقة للصحة النفسية للأطفال واليافعين',
    number: '800 51115',
    tel: 'tel:800-51115',
    hours: '9am–5pm Mon–Fri',
    scope: 'youth',
  },
  {
    labelEn: 'Nearest hospital emergency department',
    labelAr: 'أقرب قسم طوارئ في المستشفى',
    number: '999 / nearest ER',
    tel: 'tel:999',
    hours: 'immediate danger or outside helpline hours',
    scope: 'emergency',
  },
] as const

// ─── Hours-aware lead-logic — mirrors backend `select_crisis_resources` ───────
// The backend holds the authoritative clock and (Phase 2) sends the ordered list. Until that
// contract lands, the client reproduces the SAME algorithm over the static array so the ordering is
// identical. A parse failure treats a line as always-available (never hides a resource).

function hoursWindow(hours: string): [number, number] | null {
  if (!hours || hours.includes('24/7')) return null
  const m = hours.toLowerCase().match(/(\d{1,2})\s*(am|pm)\s*[-–]\s*(\d{1,2})\s*(am|pm)/)
  if (!m) return null
  const to24 = (h: string, ap: string) => (Number(h) % 12) + (ap === 'pm' ? 12 : 0)
  return [to24(m[1], m[2]), to24(m[3], m[4])]
}

function isOutOfHours(hours: string, hour: number): boolean {
  const win = hoursWindow(hours)
  if (win === null) return false
  const [start, end] = win
  return !(start <= hour && hour < end)
}

/** True if a resource answers around the clock (24/7 or unparseable → treated as always-open). */
export function is247(resource: CrisisResource): boolean {
  return hoursWindow(resource.hours) === null
}

/**
 * Ordered crisis-card resources — mirror of backend `select_crisis_resources`.
 * immediateDanger → emergency (999) leads. Otherwise the national line leads IF open, else a 24/7
 * alternative leads (never lead with a closed line). The result ALWAYS contains a 24/7 option (999
 * is 24/7). `now` is injectable for deterministic tests; defaults to the local clock (Phase 2 moves
 * ordering server-side to remove client clock drift).
 */
export function selectCrisisResources(opts?: {
  resources?: readonly CrisisResource[]
  immediateDanger?: boolean
  now?: Date
}): CrisisResource[] {
  const resources = [...(opts?.resources ?? CRISIS_RESOURCES)]
  const immediateDanger = opts?.immediateDanger ?? false
  const hour = (opts?.now ?? new Date()).getHours()

  const isOpen = (r: CrisisResource) => !isOutOfHours(r.hours, hour)
  const emergency = resources.filter((r) => r.scope === 'emergency')
  const national = resources.filter((r) => r.scope === 'national')
  const others = resources.filter((r) => r.scope !== 'emergency' && r.scope !== 'national')

  const ordered: CrisisResource[] = []
  if (immediateDanger) ordered.push(...emergency)
  const openNational = national.filter(isOpen)
  if (openNational.length) ordered.push(...openNational)
  else ordered.push(...[...others, ...national].filter(is247)) // national closed → 24/7 alt leads
  for (const r of [...national, ...others, ...emergency]) if (!ordered.includes(r)) ordered.push(r)
  // always-pair guarantee: at least one 24/7 line must be present (999 is 24/7).
  if (emergency.length && !ordered.some((r) => is247(r) || r.scope === 'emergency')) {
    ordered.push(...emergency)
  }
  return ordered
}

/**
 * The inline "top N" resources for the card (default 3) + expander shows the rest.
 * HARD SAFETY RULE (spec Open-Q1): the emergency line (999) AND a 24/7 line are ALWAYS within the
 * returned set, regardless of lead-logic — the expander must never hide the only line that answers
 * at 3am. Lead-logic order is otherwise preserved.
 */
export function leadingResources(ordered: CrisisResource[], count = 3): CrisisResource[] {
  const emergency = ordered.find((r) => r.scope === 'emergency')
  // Prefer a DISTINCT 24/7 support line; 999 itself is 24/7 and covers the requirement if none.
  const support247 = ordered.find((r) => is247(r) && r.scope !== 'emergency')

  const mustInclude = new Set<CrisisResource>()
  if (emergency) mustInclude.add(emergency)
  if (support247) mustInclude.add(support247)

  const anchors = ordered.filter((r) => mustInclude.has(r))
  const rest = ordered.filter((r) => !mustInclude.has(r))
  const slotsForRest = Math.max(0, count - anchors.length)
  const chosen = new Set<CrisisResource>([...anchors, ...rest.slice(0, slotsForRest)])
  return ordered.filter((r) => chosen.has(r)).slice(0, count)
}

// ─── Back-compat derived object ──────────────────────────────────────────────
// CRISIS_CONFIG stays the flat object existing consumers (onboarding welcome step) import. DERIVED
// from the primary national + emergency entries — mirrors the backend's own CRISIS_CONFIG shim.
const _national = CRISIS_RESOURCES.find((r) => r.scope === 'national') ?? CRISIS_RESOURCES[0]
const _emergency =
  CRISIS_RESOURCES.find((r) => r.scope === 'emergency') ?? CRISIS_RESOURCES[CRISIS_RESOURCES.length - 1]

export const CRISIS_CONFIG = {
  number: _national.number,
  tel: _national.tel,
  labelEn: _national.labelEn,
  labelAr: _national.labelAr,
  hours: _national.hours,
  emergency: _emergency.number,
  emergencyTel: _emergency.tel,
} as const
