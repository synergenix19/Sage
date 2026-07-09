# v7.1 Amendment Record — Crisis Tiering (2026-07-03)

**Status:** spec artifact riding `feat/crisis-tiering` (Absolute Rule 1: spec + code merge together).
**Clinical sign-off:** G1–G5 + G8 signed 2026-07-03 (see `governance/2026-07-03-crisis-tiering-clinical-signoff.md`).

## §5.1 — OR-fusion, amended
**v7 (superseded):** *"OR-fusion: S1 OR S3 catching → `crisis_response`, regardless of crisis_state."* Binary {safe ↔ crisis}.

**v7.1:** detection is unchanged (S1 OR S3 still fire on every signal), but the fired-signal set is mapped to a **tier** that grades the RESPONSE:
- **T2 (acute):** any S1 keyword flag (all languages); OR an S3 semantic hit in `ar`/`az`. → `crisis_response` (RED). This is the non-negotiable safety floor.
- **T1 (warm):** an S3 semantic hit **alone** (no keyword corroboration) in `en`. → normal graph with `supportive_posture` (validate, gently explore, offer-not-force). NOT `crisis_response`.
- **none:** no signal.

The boundary is data: `rules/data/tier_routing/tier_routing.json` (3 rules, clinician-editable). `safety_check` reads the resolved tier; it hardcodes no boundary. Gated by `SAGE_CRISIS_TIERING` (default **OFF** → behaviour identical to v7 / master).

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

## is_safe ruling + reader-disposition table (2026-07-03) — DO NOT "simplify"
**Ruling:** `is_safe` keeps its meaning — the truthful deterministic detector aggregate ("did any Layer-1 signal fire"). It is **never** falsified for routing (that would erase detection from the audit trail / PDPL record). Under `SAGE_CRISIS_TIERING=ON`, **routing authority moves to `crisis_tier`** (T2→crisis_response, T1→normal graph + `supportive_posture`, none→normal); `is_safe` stays exactly what the detectors said. Flag OFF: routing reads `is_safe` on the untouched code path (what makes B provable).

Every reader of `is_safe`/`crisis_flags` outside the router, dispositioned for the T1 case (flag ON; `is_safe=False`, `crisis_flags=["s3_semantic"]`, `crisis_tier="T1"`):

| Reader | Disposition (flag ON, T1) |
|--------|---------------------------|
| `graph.py:152` router — monitoring branch | **Unchanged.** T1 tiering does NOT apply in monitoring; any signal in monitoring re-escalates → crisis (conservative, correct). |
| `graph.py:155` router — non-monitoring | **The edit.** flag ON ∧ `crisis_tier=="T1"` → `"safe"` (+ `supportive_posture`); else unchanged. |
| `graph.py:94-96` `_notify_crisis_review` (inside `crisis_response`) | **Unaffected** — crisis-path only; a T1 turn never reaches `crisis_response`. |
| `output_gate.py:301/356/694` clinician-review severity + safety_level + queue write (`if crisis_flags`) | **Changed under flag.** Because T2 bypasses output_gate, these branches are dead flag-OFF; flag-ON a T1 turn would wrongly file a **high-severity "crisis"** review every turn. Disposition: the review path keys on `crisis_tier != "T1"` (i.e. T1 is NOT a crisis-review), so T1 is governed instead by G1b (`t1_count==2` → one `flag_for_review(severity=low)`). |
| `output_gate.py:514` opener-rewrite suppression (`not crisis_flags`) | **Unchanged, recorded.** T1 → `crisis_flags` non-empty → opener rewrite suppressed (reply passed through unchanged). Conservative and acceptable for a warm turn. |
| `post_crisis_classifier.py:18`, `safety_check.py:210` | Comments, not readers — no action. |
| **`server.py` `/chat` handler (the HTTP entrypoint)** | **MISSED in the original enumeration (bug #1, 2026-07-04).** It read `is_safe` directly to emit `[[CRISIS_DETECTED]]`, so a T1 warm turn (`is_safe=False`) wrongly rendered the RED card. **Enumeration scope was too narrow — package-only (`src/sage_poc/`), so the repo-root entrypoint was never inspected.** Dispositioned: tiering ON → card iff `crisis_tier=="T2"`; T1/none → warm; flag OFF → legacy `not is_safe`. Any future `is_safe` reader search MUST include the entrypoint and any repo-root module. |

No reader silently changes behavior; each is a line here. A future change to `is_safe` handling must update this table.

## Check B — definition (deterministic surfaces only)
Freeflow output is LLM-generated and non-deterministic even on master, so a literal byte-identical corpus replay proves nothing. **B = with the flag OFF, byte-identical on all DETERMINISTIC surfaces:** routing decisions (`gate_path` / node path per corpus case), canned/crisis/monitoring copy, audit rows (minus timestamps), and state writes. Provable by driving the safety corpus through the graph with **generation stubbed** — no model run.

## Flag governance — `CRISIS_TIERING_ENABLED`
Follows the established codebase convention of `D5_ACUITY_GATE_ENABLED` / `SKILL_OFFER_COOLDOWN_ENABLED`: GATED and merge-dark-then-flip. **UPDATE 2026-07-03 (PR #90): the code DEFAULT was flipped to ON** (product-owner directive executing signed item A), because a Railway env-injection bug prevented the configured `SAGE_CRISIS_TIERING=true` from reaching containers. The env var is now a **pure KILL-SWITCH** (`=false` → v7/master byte-identical, instant rollback with no crisis-path redeploy). **Steady state: every deploy (staging + prod) carries tiering ON;** the kill-switch is the sole reversal lever. **Anchor-fixture semantics shift:** the proof-1 anchor "flag-OFF == master" is now reachable ONLY by setting the kill-switch `=false` — assertion unchanged, invocation is no longer the default. Precondition (met): migration 006 present in every target env (prod + staging, 2026-07-03).

**STRICT FAIL-SAFE PARSE (2026-07-03, PR #91).** Root cause of the injection symptom: the bug delivered an **empty string** to the container, and the old `== "true"` parse read `""` as "not true" → silently disabled the crisis path (a state nobody signed). Parse inverted so **only a literal `"false"` disables**; unset / empty / whitespace / garbage → the signed default (ON), with a WARNING for unexpected values: `CRISIS_TIERING_ENABLED = not (raw is not None and raw.strip().lower() == "false")`. This is a **deliberate, recorded** tightening of kill-switch semantics on a crisis-path flag (disabling now requires intent) — within the executed item-A authorization (moves toward the signed steady state), not a silent change. Plus a **boot-observable log** (`server.py` lifespan: `CRISIS_TIERING_ENABLED=… raw_env=…`, repr distinguishes None/""/"true") so runtime flag state is a log read, not an inference. Tests: None→ON, ""→ON, garbage→ON+warn, "false"→OFF, "FALSE "→OFF.

> ⚠️ **TWO NAMES — set the RIGHT one.** The **environment variable is `SAGE_CRISIS_TIERING`** (`config.py`: `CRISIS_TIERING_ENABLED = os.getenv("SAGE_CRISIS_TIERING","true").lower()=="true"`). `CRISIS_TIERING_ENABLED` is the *derived Python boolean*, **not an env var** — setting `CRISIS_TIERING_ENABLED` in Railway does nothing. Since the default is now ON, the only reason to set the env var is the **kill-switch**: set **`SAGE_CRISIS_TIERING=false`** (lowercase; `.lower()`-compared) to disable. This dual naming is exactly how a future engineer sets the wrong variable and concludes "nothing changed, so it's safe."

**Two flip-gate lists (G8 re-sequenced 2026-07-03 — see sign-off packet risk acceptance):**
- **INTERNAL flip** (internal test cohort only) requires: G1–G4 signed (done) · A–H audit clean · per-case fail-closed regression green · deterministic B replay green · tester-battery replay diffs in the packet · **migration 006 applied + verified in the target env** (else flag-ON silently drops the PDPL-required `crisis_tier`/`tier_rule_id` audit fields). **G8 is NOT on this list.**
- **EXTERNAL exposure** (pilot, clinician-external testers, CDA demo — anything beyond the internal cohort) additionally requires: **G8 cleared** = dial-test of `800 4673` + W7 commit-2 (value/label/hours swap) + L0 fast-track re-sign + the 5 skill-JSON edits. This is a hard release gate.

## S3 FP recalibration (signed W1 scope) — DISPOSITION: DEFERRED
Signed W1 included "add the confirmed FP phrases to the S3 FP calibration set + re-run `calibrate_s3_threshold.py`." **Deferred — superseded in urgency by tiering.** Proof 2 measured **S3 firing on 0/232 true-SI EN cases** at threshold 0.8059: on English, S3 currently contributes **zero recall and ~100% of the false-RED harm**, and tiering now absorbs exactly those FPs into T1. Recalibration is therefore no longer safety-urgent; revisit when **S2/MARBERT** lands and S3's role is re-decided (the recall-floor re-run obligation already fires then). **⚠️ COUPLING (do not decouple):** the deferred recalibration is now coupled to the plan/means detection finding ([[2026-07-03-arabizi-si-detection-finding]]). Because S3 carries no severity information, **any future S3 threshold *lowering* on EN requires FIRST either (a) S1 (`si_explicit`) coverage of the plan/means class, or (b) a severity-aware T2 rule** — otherwise "improving recall" routes a stated-plan+means phrase straight into the T1 warm hole. A future engineer must not lower the EN threshold to chase recall without one of those two prerequisites. Enforced by `test_plan_means_phrase_never_resolves_T1_drift_guard` (hard assert). **Clinician-packet sentence:** *"S3 fired on 0 of 232 true-SI English cases — the strongest empirical evidence that grading English S3-solo signals to a warm tier removes false alarms without losing any detected crisis."*

## Scope guards (unchanged from §H)
Detection sensitivity untouched; T2 floor absolute; flag OFF until G8 clears + the recall regression is green + the staging tester-battery replay is attached to the clinician packet.

## Bug #2 post-mortem (2026-07-04) — SageState dropped crisis_tier; audit-trail corrections

**Root cause.** `crisis_tier`/`tier_rule_id`/`supportive_posture`/`t1_count` were computed by `safety_check` but **never declared as channels in `SageState`**. LangGraph silently drops any key a node returns that is not a declared channel, so the reducer discarded them: `_route_after_safety` and the audit read `crisis_tier=None` → every tiering turn fell through to `crisis_response`. Confirmed by deep `/health/version` on prod: `config_flag_in_module=true`, `resolve_s3_en=('T1','s3_solo_en')` — the node computed T1, the graph state carried NULL. Fixed by declaring the four channels; guarded by a compiled-graph reducer test (RED without the fix).

**FAIL-CLOSED (clinically important).** With `crisis_tier=None`, `_route_after_safety` fell through to `crisis_response` — every affected turn rendered the **old RED crisis card**, never a missed crisis or silence. The bug cost the **UX improvement (warm T1), not safety**. The architecture's fail-closed posture held even while the feature was broken.

**Why five green proof-sets coexisted with flag-OFF deployed behaviour.** Every test read `safety_check`'s **return dict** (pre-reducer) or **mocked** the graph; none drove `graph.compile().ainvoke` (post-reducer) or crossed the **HTTP entrypoint** (`server.py`, which additionally read `is_safe` not `crisis_tier` — bug #1). The verification pyramid stopped at the graph-node boundary.

**Audit-trail corrections (honesty):**
- **Check G ("specs match code") was WRONG.** The `sagestate_schema_delta` doc declared these `SageState` fields while the code omitted them — exactly the spec/code divergence Absolute Rule 1 exists to prevent. The check compared intent-to-intent, not doc-to-code. Now reconciled (code declares them).
- **Check F's staging verification did not cross the reducer.** It wrote `session_audit` rows by calling `_build_session_audit_row` with a hand-built state containing `crisis_tier` — validating the audit *builder*, not the graph *propagation*. It proved migration 006 columns accept the write, not that a real turn produces the tier.

**Two permanent guards now in place** (this class cannot recur silently on the crisis path):
1. `test_sagestate_declares_tier_channels` + `test_langgraph_propagates_crisis_tier_through_reducer` (compiled-graph reducer).
2. Real-graph HTTP E2E (`test_chat_T1_real_graph_hopeless_warm_no_card`, `test_chat_T2_real_graph_card_and_tier_header`) + `verify_tiering_recall.py` now drives the compiled graph (post-reducer) as its permanent mode.

**The onion, fully peeled (each layer eliminated with evidence, each leaving a permanent instrument):** env injection → deploy cutover / stale build cache → module provenance (uv-sync-before-COPY) → **state channel drop**. Instruments: strict-parse kill-switch, boot log, `/health/version` (+sage_poc_path/config/resolver/PYTHONPATH), reducer + HTTP E2E guards.
