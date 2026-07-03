# v7.1 Amendment Record — Crisis Tiering (2026-07-03)

**Status:** spec artifact riding `feat/crisis-tiering` (Absolute Rule 1: spec + code merge together).
**Clinical sign-off:** G1–G5 + G8 signed 2026-07-03 (see `governance/2026-07-03-crisis-tiering-clinical-signoff.md`).

## §5.1 — OR-fusion, amended
**v7 (superseded):** *"OR-fusion: S1 OR S3 catching → `crisis_response`, regardless of crisis_state."* Binary {safe ↔ crisis}.

**v7.1:** detection is unchanged (S1 OR S3 still fire on every signal), but the fired-signal set is mapped to a **tier** that grades the RESPONSE:
- **T2 (acute):** any S1 keyword flag (all languages); OR an S3 semantic hit in `ar`/`az`. → `crisis_response` (RED). This is the non-negotiable safety floor.
- **T1 (warm):** an S3 semantic hit **alone** (no keyword corroboration) in `en`. → normal graph with `supportive_posture` (validate, gently explore, offer-not-force). NOT `crisis_response`.
- **none:** no signal.

The boundary is data: `rules/data/safety/tier_routing.json` (3 rules, clinician-editable). `safety_check` reads the resolved tier; it hardcodes no boundary. Gated by `SAGE_CRISIS_TIERING` (default **OFF** → behaviour identical to v7 / master).

## §5.6.1 — "Dialect mirroring rules" wording, clarified
The v7 spec row read *"Dialect mirroring rules,"* which was ambiguous; the implementation (CU-DM-001 = **"Khaleeji register calibration"**) and the signed L0 v2.2.0 (register-matching scoped to **tone/formality**, not sub-dialect) mean **fixed Khaleeji** is the baseline. §5.6.1 is corrected to read "Khaleeji register calibration (fixed register; tone/formality matched, not user sub-dialect)." Any move to MSA/hybrid is a future amendment (G6), not a bug.

## Crisis-recall — TWO DISTINCT GATES (do not conflate) — binding
Refinement #2 defines the tiering metric, but it must not be read as ratifying the current recall level. There are **two separate gates**:

**Gate 1 — Absolute pilot KPI (pre-existing, NOT part of tiering).**
The ≥95% crisis-recall KPI. Production is **~37% (S1-lexicon 86/232 on CRADLE EN; AR unmeasured — no CRADLE AR corpus)** — a **known, documented, already-escalated P0** ([[project_safety_detection_baseline]]) that already makes the pilot fail-closed NO-GO (gate `fedd99f`). Its fix is **S2/MARBERT (#18)**, not this workstream. Tiering neither creates nor closes this gap.

**Gate 2 — Tiering NON-INFERIORITY (this workstream's actual gate).**
> Under v7.1, a true-SI case must resolve to **T2**. Turning the flag ON must move **ZERO** currently-T2-routed true-SI case to T1. The merge gate is **Δrecall ≥ 0 vs the flag-OFF baseline**, i.e. **non-inferiority** — NOT "≥ baseline ratifies 37%," and NOT "must reach 95%."

The safety-critical subtlety: a true-SI case that fires **`s3_semantic` alone in English** (S1 missed it, S3 caught it) is routed to crisis **today** but to **T1 under tiering** — a recall regression on exactly the hardest, un-keywordable cases. The whole tiering premise rests on the claim (CRADLE sweep: "S3 adds 0 recall above S1 in EN") that **no such case exists**. The blocking regression (`test_crisis_tiering_recall`) exists precisely to **prove that set is empty** before the flag can ever flip; if it is non-empty, tiering is unsafe as designed and stops.

**⚠️ ESCALATION (2026-07-03):** G3 was signed as "no change may reduce recall." That is non-inferiority (Gate 2) and is satisfiable — but it was signed against an assumed ≥95% floor that **does not exist** in production. Before any `safety_check.py` edit, the clinical lead must confirm G3 = **non-inferiority vs flag-off**, decoupled from the absolute ≥95% pilot KPI (Gate 1). The committed baseline (`tests/fixtures/recall_baseline_2026-07-03.json`) must state its metric definition, corpus names + case counts, and per-language figures (with AR marked UNMEASURED), never a bare number.

## Language gate + fail-closed routing (closure 2026-07-03)
- **Conservative language gate.** The T1 (warm) route fires ONLY on confident English: `lang=='en'` AND not code-switched AND not Arabizi-suspect (`tier_routing.json` `require_confident_lang`). Language ID is weakest for Arabizi/code-switch, and a true-SI message mis-classified as English would otherwise drop to T1.
- **AR/AZ-invariance is CONDITIONAL on this gate.** Tiering leaves Arabic/Arabizi routing unchanged *only because* any message that is not confidently English resolves to T2. The `s3_ar_az` rule plus the `s3_failclosed` catch-all guarantee it.
- **Fail-closed default.** Any fired semantic signal that is not confidently-English (low-confidence EN, code-switch, Arabizi, or an unmapped language) routes **T2** via `s3_failclosed`. Only a turn with **no** fired signal reaches `default_tier: "none"`. A fired crisis signal never falls through to safe.
- Interim Arabizi heuristic (`_is_arabizi_suspect`): letter-digit substitutions (3/5/7/2/6/9 adjacent to Latin letters). Full Arabizi language-ID is the pending arabizi project; this is the fail-closed interim.

## Two obligations that ride to the clinician packet
- **Flag-flip ≠ pilot unlock.** Turning `SAGE_CRISIS_TIERING` ON does not change the pilot gate: the pilot stays NO-GO on the absolute ≥95% recall KPI (Gate 1) until S2/MARBERT clears it. Tiering shipping and pilot go-live are separate events.
- **S2/MARBERT re-run obligation.** When S2 lands (raising detection recall), the non-inferiority regression MUST be re-run — S2 may change which cases are s1/s3-solo, so the "no true-SI case is s3-solo-EN" proof is not permanent; it is re-established on every detector change.
- **Residual-risk framing preserved.** The clinician approved G3 with the residual-risk statement in the sign-off packet; that text is carried forward verbatim (do not silently drop it when the packet is regenerated).

## Scope guards (unchanged from §H)
Detection sensitivity untouched; T2 floor absolute; flag OFF until G8 clears + the recall regression is green + the staging tester-battery replay is attached to the clinician packet.
