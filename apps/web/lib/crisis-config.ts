// ─── CRISIS CONTACTS — single frontend source ───────────────────────────────
// Mirrors the backend source `sage_poc.config.CRISIS_RESOURCES` (H4, PR #288). Every crisis surface
// (crisis card, persistent "Get help now" affordance, onboarding) reads from HERE — no re-embedded
// literals. Change in ONE place per stack; never inline. The cross-stack parity test
// (sage-poc/tests/test_crisis_config_cross_stack.py) asserts this array == backend CRISIS_RESOURCES.
//
// ✅ VALUE STATUS — VERIFIED FINAL (PO, 2026-07-08: "I have verified this number" + "24/7 is also
// verified"). MoHAP 800 46342 / 24/7 is confirmed correct (the G8 46342-vs-4673 transcription
// question is RESOLVED by verification). These are the CURRENT values. This is the Phase-1
// (structure-only) reshape: the card is multi-resource-CAPABLE but the VALUES are unchanged. The
// coupled value flip (both stacks → the doc's 5-entry composition) is a separate clinician-gated
// step (reverses GL-1; needs verify + sign-off + crisis-freeze lift). Do NOT change values here
// without that ruling AND the mirrored backend edit — the cross-stack test keeps both sides honest.

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
    labelEn: 'MoHAP Counselling Line',
    labelAr: 'خط وزارة الصحة للدعم النفسي',
    number: '800 46342',
    tel: 'tel:800-46342', // RFC 3966: hyphens/spaces equivalent
    hours: '24/7',
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
