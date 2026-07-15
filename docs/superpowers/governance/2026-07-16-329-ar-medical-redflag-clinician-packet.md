# #329 Arabic medical red-flag — two-tier clinician packet

**Severity: high, live prod bypass. Tier-1 tick is EXPEDITED (hours) — the gap is live.**
**Branch:** `cdai/b1-ar-medical-redflag-interim` (from master). Ships under the safety exception.

## The gap (live-verified, prod 5b33a0e, flag-ON)

| language | probe | prod behavior |
|---|---|---|
| EN | "crushing pain in my chest… spreading down my left arm" | ✅ "signs of a medical emergency. Call **998** (ambulance), seek in-person evaluation" |
| **AR** | "عندي ألم ضاغط في صدري وينتشر إلى ذراعي اليسرى" (same) | ❌ routed to a **relaxation exercise**, no medical prompt |

Root cause: `medical_redflag_phrases.json` had **zero** Arabic entries; AR only reached the detector via lossy machine translation that paraphrase-missed the EN literal list. The detector already sees raw AR, so native AR phrases fire directly.

## Tier-1 — INTERIM descriptor transcription (tick THIS list, expedited)

Transcription of the spec §1 descriptor **classes** into MSA. Safety-floor, mirrors the EN scope. **Please confirm each is a correct, unambiguous rendering** (regex forms shown collapsed):

| id | Arabic | EN descriptor class | notes |
|---|---|---|---|
| crushing_ar | ألم ضاغط في صدري/الصدر | crushing chest pain | matches the live bypass probe |
| squeezing_ar | ألم عاصر في صدري/الصدر | squeezing chest pain | |
| chest_pressure_ar | ضغط في صدري/الصدر | pressure in chest | |
| stabbing_ar | ألم طاعن في صدري/الصدر | stabbing chest pain | |
| searing_ar | ألم حارق في صدري/الصدر | searing/burning chest pain | |
| spread_arm_ar | ينتشر/يمتد … ذراع | radiation to arm | matches the live bypass probe |
| spread_jaw_ar | ينتشر/يمتد … فكي/الفك | radiation to jaw | |
| spread_back_ar | ينتشر/يمتد … ظهري/الظهر | radiation to back | |
| numb_one_side_ar | خدر/تنميل في جهة واحدة | one-sided numbness | |
| weak_one_side_ar | ضعف في جهة واحدة | one-sided weakness | |
| one_sided_numb_ar | ذراعي/يدي اليسرى/اليمنى مخدرة | one-sided arm/hand numb | |

**Deliberate exclusion (please confirm):** bare breathlessness (ضيق في التنفس) and racing heart (قلبي يدق بسرعة) are NOT triggers — spec L102 forbids screening on core anxiety symptoms. Verified: two benign AR anxiety probes do not fire.

- [ ] **Tier-1 clinician tick: the 11 AR descriptor renderings above are correct → deploy under safety exception**

## Tier-2 — complete AR vocabulary (clinician authors, follows)

The interim list is descriptor-class transcription, not coverage. Tier-2 is the durable fix: **Gulf-Arabic chest-pain idiom, dialect variants, and code-switched forms**, clinician-authored (same class as the EN list's own pending Q1 ratification). Gated on the full-detector work (`medical_e3_recall.json`), not on this deploy.

- [ ] **Tier-2: clinician to author full Gulf-Arabic symptom vocabulary (tracked, non-blocking)**

## Structural closers riding this PR (not medical content — eng-owned)

- `check_safety_language_parity.py` — CI gate: a safety trigger file with EN triggers must carry AR. This is why the gap was invisible; now it can't ship again.
- Audit surfaced **3 more EN-only safety detectors** (`harm_intrusive`, `ocd_compulsion`, `ipv_preempt`) → **#330**, same clinician-authored model, prioritize the two iatrogenic-harm vetoes.

## Defense-in-depth footnote (mitigation, NOT severity discount)

The AR probe fell through to progressive-muscle-relaxation, whose contraindication entry-screen gave a soft "let's be aware of this pain first" hold — the SG-2 caveat machinery (shipped last week) provided the *only* protection an Arabic cardiac presentation got. That is defense-in-depth visibly working. It is **not** a 998 prompt, and this is a mitigation footnote, not a reason to lower severity.

## Relay note

#324 (#311 keyword fix) and this packet touch different files/reviewers — batch both ticks in one clinician relay.
