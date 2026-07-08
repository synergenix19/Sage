// ─── CRISIS CONTACTS — single frontend source ───────────────────────────────
// Mirrors the backend source `sage_poc.config.CRISIS_CONFIG`. Every crisis surface (crisis card,
// onboarding) reads from HERE — no re-embedded literals. Change in ONE place per stack; never inline.
// ✅ VALUE STATUS — number VERIFIED FINAL (PO, 2026-07-08: "I have verified this number"). 800 46342
// is confirmed correct; the G8 transcription question (46342 vs 800 4673 / LifeLine / 800-HOPE) is
// RESOLVED by verification. hours 24/7 is PO-directed. If the number ever changes, change this dict
// AND the backend config (one edit each) — the tests both sides keep every surface consistent.
export const CRISIS_CONFIG = {
  number: '800 46342',
  tel: 'tel:800-46342', // RFC 3966: hyphens/spaces equivalent
  labelEn: 'MoHAP Counselling Line',
  labelAr: 'خط وزارة الصحة للدعم النفسي',
  hours: '24/7',
  emergency: '999',
  emergencyTel: 'tel:999',
} as const
