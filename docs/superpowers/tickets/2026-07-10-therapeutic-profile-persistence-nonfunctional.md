# Ticket: Therapeutic-profile persistence layer is non-functional end-to-end — SCOPE decision required

**Filed:** 2026-07-10 · **Status:** RULING RECORDED 2026-07-13 (internal-testing posture: keep in-session, do NOT build cross-session, DPO parked, config frozen) — pending Vee sign-off; see `../governance/2026-07-13-memory-scope-internal-testing-decision.md` · **Type:** SCOPE DECISION (do NOT auto-fix) · **Verified against:** master `a0721c0` (read-path files byte-identical across `f78101e`…`a0721c0`) · **Links:** `2026-07-10-techniques-used-phantom-read.md` (the one defect-class member), `2026-07-10-guard-clinical-flag-persistence-config.md` (the guardrail), `project_poc_scope_boundary`, `project_unified_memory_layer`, findings #3/#4/#5 (retention/erasure/RLS, still open)

## Headline (one systemic finding, not a scattered bug list)
The cross-session therapeutic-profile ("digital twin") persistence layer **does not function end-to-end.** Four fields are the same failure wearing four hats — each is either *written-but-not-read* or *read-but-not-written*:

| Field | Written? | Read into anything the model/logic uses? | Hat |
|---|---|---|---|
| `observations` | Yes (record_observation tool; wipe fixed in PR #290) | **No** — zero readers anywhere in `src`; never injected into any prompt | written-not-read |
| `mood_trajectory` | Yes (extract-profile upsert) | **No** — zero readers; never injected | written-not-read |
| `techniques_used` | **No** — no writer, not in SELECT | Yes (`skill_executor.py:556`) | read-not-written |
| `persisted_clinical_flags` | Effectively no (only writer gated to `[]` by all-false config) | Seeded in safety_check but always `[]`; dedicated `get_persisted_clinical_flags` has no caller | neither |

**The codebase already knows this.** `tests/test_continuation_recall.py` asserts `cross_session_residual_rate == 1.0  # EXPECTED-MISS, measured not hidden` — the team's own recall harness measures the twin as a 100% miss.

**What actually moves model output** (proven by live-LLM full-path tests, `test_a4_gate_full_path.py`): the **within-session conversation window (last 8 turns)** plus **honest-absence governance** (L0 memory clause + absent-memory sentinel). No test anywhere asserts a *present* cross-session summary or profile field changes the response.

## The decision that matters (product, not engineering)
**Is cross-session continuity in POC scope at all?** Evidence says no:
- `project_poc_scope_boundary`: POC = AI-layer validation (8-node graph, crisis, skills, RAG, Khaleeji). Cross-session continuity is not listed.
- The Intelligence Evaluation observed the POC "appears to be single-session."
- POC track is a Railway/Supabase/Vercel demo of the graph + crisis + skills + rendering.

**If cross-session is Full-Build (the likely ruling), the dead reads are NOT defects — they are premature scaffolding, and the correct action INVERTS:**
- **Do NOT** wire up the dead reads (that builds a Full-Build feature into the POC).
- **DO** stop *writing* the sensitive fields you are not using. Today the POC holds the worst of both worlds: it accumulates crisis-adjacent clinical data (observations, flags) on **non-sovereign** infra (Supabase `aws-ap-south-1`), carrying the full retention/erasure liability (findings #3/#4/#5, still open), for **zero therapeutic benefit** (expected miss). Storing-but-not-using is pure downside.

**If cross-session IS in POC scope**, then this becomes a build ticket (injection path + a present-side eval proving the model conditions on it) — but that is a deliberate scope expansion to be decided, not a bug backlog to grind through.

## Do NOT resolve this by "helpfully" wiring up the gaps
The four dead fields look like bugs to a fresh pass and invite exactly the wrong fix (build the Full-Build feature into the POC). This ticket exists so that does not happen. Hold until the scope ruling. The only member of this set with an independent within-session consequence — `techniques_used` — is split out as its own defect ticket precisely so it can be handled without touching cross-session.

## Note
PR #290 (`observations` wipe fix) is correct on its own terms (stops silent clinical-data loss, restores auditability) and is independent of this ruling. But it does make the accumulate-but-never-use posture *live* rather than masked — which is exactly why the scope ruling now matters.
