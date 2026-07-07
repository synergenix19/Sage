# `mi_readiness_ruler` — deprecate / keep / rescope: decision request (2026-07-07)

**Decision owners (joint):** clinical lead + product. **One question, one signature.** This is a resurfaced orphan finding, now with operational evidence attached.

## 1. The question
Should `mi_readiness_ruler` (SK-009, a Motivational-Interviewing readiness/ambivalence ruler) be **deprecated**, **kept (with justification)**, or **rescoped** — given the BOT BEHAVIOUR spec (our source of truth for which skills to offer) does not reference it, and it is now empirically entangling skill routing?

## 2. Spec-absence (the original finding, re-cited)
The content-inventory §2 reverse check already flagged this: *"Inventory skills the spec's 35 categories do not appear to reference: `mi_readiness_ruler` (SK-009, motivational-interviewing readiness) — no readiness/ambivalence category in the spec … Worth a clinician glance — a spec that silently drops an implemented skill is itself a finding."* (`docs/superpowers/governance/2026-07-04-bot-behaviour-content-inventory.md:70`). It was routed to the clinical lead via PR #114 as a deliberate-omission-vs-oversight question and **has not been answered.** This request re-raises it with evidence.

## 3. New evidence — routing entanglement at the threshold margin
`mi_readiness_ruler` sits in the fragile 0.45–0.48 semantic band (threshold 0.4593) and is **doubly tangled** there:
- **It fails to catch its own phrases** (owns 2 of the ~11 trunk routing failures):
  - "I have really mixed feelings about getting help, I don't know where I stand" → mis-routes
  - "Part of me wants to get better and part of me doesn't see the point" → routes to `self_compassion_break` (0.475)
- **It steals another skill's phrase:** "I need to get clear on my emotional state before we do anything else" → routes to `mi_readiness_ruler` (0.484), stealing it from `mood_check_in` (a spec-valid skill).

Full list + scores: `docs/superpowers/governance/2026-07-07-routing-baseline-11-failures.md`.

## 4. The consequence (why this is now blocking)
The incoming `mindfulness_meditation` skill (spec-required) lands in exactly this semantic neighborhood ("sitting with feelings", "observing thoughts"). Registering it requires recalibrating the shared `SEMANTIC_THRESHOLD` against this already-fragile band. **This orphan occupies the collision zone, so the deprecation answer is a prerequisite input to stabilizing the routing baseline before MM can be registered.**

## 5. The honest counterweight
**MI readiness work is a legitimate, evidence-based technique.** Its absence from the spec may be the **spec's gap**, not the skill's obsolescence. "Deprecate" is not the assumed answer — the clinician decides whether the spec should gain a readiness/ambivalence category (keep + spec-amend), the skill should be narrowed (rescope), or it should be retired (deprecate). Engineering's role here is only to surface the spec-absence + the routing cost.

## 6. Decision + mechanics — ✅ EXECUTED 2026-07-07 (DEPRECATE)
- [x] **Deprecate** — removed `mi_readiness_ruler` from `SKILL_REGISTRY` + its clinical cluster + its offer description. **Mechanic:** the JSON is **retained** on disk (reversibility + it serves as executor test fixtures), with a documented exemption in `test_corpus_integrity.py::DEPRECATED_RETAINED` so the no-orphan-JSON invariant still holds explicitly. Reversible = drop it from that exemption set + re-add to `SKILL_REGISTRY`. Freed slot taken by `mindfulness_meditation`; routing verified (0 new failures, calibration gap 0.0526 clean, `SEMANTIC_THRESHOLD` unchanged).
- [ ] Keep + justify · [ ] Rescope — not chosen.

| Role | Decision | Rationale | Name | Date |
|---|---|---|---|---|
| Product | **Deprecate** | product half of the call, made to unblock MM registration | Rohan (PO) | 2026-07-07 |
| Clinical lead | **Deprecate (via spec)** | NOT a wet signature — the clinical half is the spec's own silence: BOT BEHAVIOUR has no readiness/ambivalence category, i.e. the clinician's own document. This one-pager is routed to the clinical lead as a **notification with a confirm-or-object window**, not a blocking ask. If the clinician objects, deprecation is reverted (git-reversible). | notification (confirm-or-object) | 2026-07-07 |

## Secondary observation (NOT part of this ask)
`interpersonal_effectiveness` is **spec-covered-by-another-skill** (function lives in `assertive_communication` / "Boundary Setting"), i.e. a **redundancy** question, not an orphan — and it carries the **E7 `coaching_confrontation` guard**, so touching it has safety entanglement. Deliberately excluded from this single-question ask; raise separately if worth pursuing.
