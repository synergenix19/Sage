# Containment Phase 2 — Task-Sequenced Plan Against 2026-07-31 (for review BEFORE build)

**Task 0 SIGNED** (Vee clinical + Rohan arch/PO, 2026-07-09). This sequences the build. **Human-gate latency, not engineering, has been the schedule risk every time** — so the critical path is drawn around the clinician touchpoints, and those are front-loaded.

## The serial spine (must be in order — each depends on the prior)
- **T1 — `containment_directive` state field** (SageState + per-turn reset). ~hours. Blocks everything.
- **T2 — `contain` Rules-Service action** (4th action; CMS-authorable draft→review→approve→publish). Depends on T1. ~1 day.
- **T3 — ONE conditional graph edge** (directive present → knowledge_retrieve → freeflow L3+L4, or skill_executor). Depends on T2. ~hours.
- **T4 — wire the three approved families to `contain`** (harm-intrusive enrich, OCD upgrade, safeguarding). Depends on T3. Per-family.

## Parallelizable (no inter-dependency; can run alongside the spine)
- **P5 — containment template** (validate→psychoeducate→differentiate→**refer**→engage; the ego-syntonic→crisis branch). Clinical content; can draft during T1–T3.
- **P6 — KB content** for the families (feeds L4). Content work; independent of the graph.
- **P7 — AR checklist / bilingual** (few-shot ≥3 EN+AR, Khaleeji renderings, per-language fail-safe). Independent.

## The safeguarding family (#1, TARGET 2026-07-31) — its clinician touchpoints ARE the critical path
Safeguarding rides T4 but needs its OWN clinician sign-offs BEFORE it can wire:
- **HG-1 — safeguarding trigger patterns** (third-party/behavioural child-harm; the first-person-vs-third-party split). Clinician. ← front-load THIS week.
- **HG-2 — tier + posture** (referral-with-urgency + mandatory L2 review; L3-adjacent, clinician-ruled).
- **HG-3 — referral copy** (safeguarding signpost, verbatim-pinned like #218's ERP line).
**Backward math from 07-31:** T1–T3 (engineering, ~3-4 days) can start now; but safeguarding's HG-1/2/3 gate its T4 wiring. If HG-1/2/3 don't land by ~mid-next-week, T4-safeguarding slips → 07-31 slips. **Front-load HG-1/2/3 now, in parallel with T1–T3.**

## Recommended kickoff (this week)
1. Engineering: **T1 now** (state field, gated behind default-OFF — inert until T2/T3/T4 + sign-offs, per the never-build-live-ahead-of-sign-off rule; the FLIP is gated, the scaffolding is not).
2. Clinician (Vee): **HG-1 safeguarding patterns** packet — the front-loaded human gate.
3. Parallel: P5 template draft, P6 KB seed.

**Not started blind:** this is the plan for review. On approval, T1 begins; the safeguarding clinician packet (HG-1) goes out same-day, since it's the long pole.

---

# SELF-ASSESSMENT against the 5 pre-registered review checks (2026-07-09)

## Check 1 — DATED critical path, backward from 07-31, clinician touches as calendar items
Today = 2026-07-09 (~3 wks). Human-gate latency is the schedule risk, so the clinician touches carry the hard dates:
| by-date | item | owner | gates |
|---|---|---|---|
| **07-11** | HG-1 safeguarding trigger-pattern packet SENT | eng→clinician | the long pole; send day-1 |
| 07-10→07-14 | T1 state field (default-OFF) → T2 `contain` action → T3 edge | eng (serial) | scaffolding inert |
| **07-16** | **HG-1 safeguarding patterns CONFIRMED** | Vee | ← if slips, 07-31 slips |
| 07-14→07-18 | T4-REFERENCE family (OCD abstain→contain) — proves the pathway end-to-end | eng | full gate + probe |
| **07-18** | **HG-2 safeguarding tier ruled** (L3-adjacent, referral-with-urgency + L2 review) | Vee | |
| **07-21** | **HG-3 safeguarding referral copy** (verbatim-pinned like #218 ERP) | Vee | |
| 07-21→07-25 | T4-safeguarding wiring (gated on HG-1/2/3) + gate | eng | full gate |
| 07-25→07-28 | T4-migrations (harm-intrusive, then remaining) — AFTER reference proven | eng | full gate each |
| **07-28→07-31** | safeguarding gate + deploy + verify → **LIVE 07-31** | eng | lock-claimed deploy + probe |
**If HG-1/2/3 miss 07-16/18/21 → named scheduling escalation to command; 07-31 recomputed.**

## Check 2 — every task carries its gate discipline INLINE
- Any task touching a skill `semantic_description` / `target_presentations` / KB embedding surface → **full mechanism-4 gate** (id_oos margin distance-from-floor, harm-0, wrong-route no-regress, per-pathway floor). No "local" content edits.
- Every family's copy (referral lines) → **verbatim post-generation pin** (like #218 ERP), not LLM-composed.
- **Per-language fail-safe (AR):** every family ships EN with the AR counterpart either shipped or explicitly filed to the AR track; AR KB absent → fail-safe (no broken AR containment).

## Check 3 — migrations sequenced AFTER the reference family proves the pathway
T4-REFERENCE (OCD abstain→contain) runs FIRST and proves the whole chain (directive → edge → KB→L4 → template refer → audit + L2 queue). Only on its green gate + probe do the migrations (harm-intrusive abstain→contain, then the rest) follow — NOT alongside. A broken pathway is found on one family, not three.

## Check 4 — KB-gating + suggest_skill suppression as WRITTEN ACCEPTANCE (signature conditions)
- **AC-KB-FAILSAFE:** a containment turn whose family KB article is missing/unpublished → serves the template + referral WITHOUT a broken/empty KB block (never a dangling "here's an article" with no article). Test: unpublish the KB row, assert graceful degrade.
- **AC-SUGGEST-SKILL-OFF:** on any containment/veto turn, `suggest_skill` is unbound — a guardrail is not optional through a tool. Test: containment turn + a tool-call attempt → suggest_skill absent from the served turn.
Both are ACCEPTANCE (block ship), not aspirations — they were signature conditions.

## Check 5 — explicit NOT-INCLUDED (bounded scope)
Phase 2 builds ONLY the three approved families: OCD (reference), harm-intrusive (migration), safeguarding (#1). **The BOT BEHAVIOUR audit's other Class-A discoveries (§3d offload, §7a company, S2a grief, and any future) STAY in the CMS backlog the clinician prioritizes — they do NOT enter Phase 2 by discovery.** A ten-family audit does not make Phase 2 a ten-family project. The pathway (state/action/edge/template) is reusable, so a later family is a CMS `contain` row, not a Phase-2 reopen.
