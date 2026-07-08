// ─── CRISIS CONTACTS — single frontend source ───────────────────────────────
// Mirrors the backend source `sage_poc.config.CRISIS_CONFIG`. Every crisis surface (crisis card,
// onboarding) reads from HERE — no re-embedded literals. Change in ONE place per stack; never inline.
// ⚠️ VALUE STATUS — approval-of-USE, not verification. The PO directed (2026-07-08) keeping and
// centralising the currently-served number 800 46342 / hours 24/7. CORRECTNESS is UNRESOLVED: the
// G8 question — is 800 46342 a transcription error for 800 4673 (LifeLine Arabia / 800-HOPE), the
// number the authoritative directories list? — needs a DIAL-TEST, which owns the verdict. Not
// "final". When it settles, change this dict AND the backend config (one edit each).
export const CRISIS_CONFIG = {
  number: '800 46342',
  tel: 'tel:800-46342', // RFC 3966: hyphens/spaces equivalent
  labelEn: 'MoHAP Counselling Line',
  labelAr: 'خط وزارة الصحة للدعم النفسي',
  hours: '24/7',
  emergency: '999',
  emergencyTel: 'tel:999',
} as const
