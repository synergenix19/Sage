// ─── CRISIS CONTACTS — single frontend source of truth ──────────────────────
// Mirrors the backend canonical source `sage_poc.config.CRISIS_CONFIG`. Every crisis-copy
// surface in the app (crisis card, onboarding) reads from HERE — no re-embedded literals.
// The number/label/hours are PO-approved (2026-07-08): 800 46342, MoHAP, 24/7.
// Cross-stack invariant: `number` MUST equal the backend `CRISIS_CONFIG["number"]`
// (enforced by tests both sides). Change in ONE place per stack; never inline.
export const CRISIS_CONFIG = {
  number: '800 46342',
  tel: 'tel:800-46342', // RFC 3966: hyphens/spaces equivalent
  labelEn: 'MoHAP Counselling Line',
  labelAr: 'خط وزارة الصحة للدعم النفسي',
  hours: '24/7',
  emergency: '999',
  emergencyTel: 'tel:999',
} as const
