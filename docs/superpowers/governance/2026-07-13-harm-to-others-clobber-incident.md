# Incident: #219 harm-to-others backstop clobbered + never live in prod (2026-07-13)

**Disposition: RESOLVED.** Prod re-armed + probe-verified (Entry 8). Root-cause hygiene fix handed to Lane-1 (below). Not a user-exposure incident — redundancy held throughout — but a signed deterministic safety control that was absent from production for ~3.75 days.

## 1. Prod behavior first (the probe that led)
Live-prod `/chat` probe, before any code archaeology:
- **Before re-arm** (prod `ede2c52`): "I'm planning to hurt him when he gets home" → reaches `crisis_response`, but via `safety_check → intent_route` with `X-Sage-Crisis-Flags: []`. The **LLM intent classifier** caught it; the deterministic Node-1 backstop did not. SI control fired the deterministic layer normally.
- **After re-arm** (prod `cfd6d58`): same phrase → `X-Sage-Crisis-Flags: ["harm_to_others_explicit"]`, path `safety_check → crisis_response`. Deterministic backstop armed. FP control "could strangle him" → deterministic backstop correctly held (`[]`).

**So no user was ever unprotected for this phrase (the LLM layer is redundant cover), but the approved deterministic guarantee was absent.**

## 2. Root cause (archaeology, after the probe)
- SK-EN-HTO-001 (Group A explicit-intent backstop) was clinician-approved (Vee, approval-queue item 2) and **activated** via #244 / `aef9499` on 2026-07-09 **20:28**.
- **#218** (`f2b86d3`, OCD ERP referral — an unrelated Node-8 change) **silently reverted it** at **21:08**: `active true→false`, `version 1.0.0→0.1.0`, `authored_by sage_clinics→PENDING`. Cause: the #218 branch was cut *before* the activation; its stale `crisis_keywords.json` overwrote the approved one on merge. A **stale-base merge clobber** of a safety file the PR never intended to touch.
- **The alarm was disarmed:** `test_harm_to_others_node1_backstop` asserted `active is True` but was **excluded from the `unit-gate` CANDIDATES list**, so it failed invisibly — the control that would have blocked the clobber was itself unwired.

## 3. The window (quantified)
`active:true` was **never deployed to production.** Reverted 40 min after merge; the next prod deploy (`d27987f`, 23:08) already carried the revert; every prod SHA since (`d27987f`, `93114c9`, `ede2c52`) ran `active:false`. **Dormant in prod from approval (2026-07-09 20:28) to re-arm (2026-07-13 13:58) — ~3d 17½h.** This re-arm (`cfd6d58`, Entry 8) is the first time the rule has served `active:true` in production.

## 4. Fix (done)
- **Restored** SK-EN-HTO-001 to its approved `b41a03d` state (patterns/modifiers/action were untouched by the clobber; only the 4 metadata fields). Signature cited; **regression fix, no new sign-off** (new standing convention in ARCHITECTURE_BOUNDARIES).
- **Armed the alarm** — test added to `unit-gate` CANDIDATES (5/5 incl. FP-asymmetry).
- **Pinned it** — `harm_to_others_backstop_rule` + `safety_rule_activation_map` in `signed_clinical_fields.json`; any active-flip on any safety rule now fails CI. Had this existed, #218 would have been blocked at merge.
- **Deployed + probe-verified** (Entry 8).

## 5. Lane-1: the merge-hygiene root cause (the half that's yours)
The manifest now catches the **symptom** (an active-flip fails CI). The **cause** — a PR reverting a safety file it never meant to touch, because its branch predated a safety change — is merge discipline. Two options; the first is cheaper and structural:
- **RECOMMENDED — `CODEOWNERS` on `src/sage_poc/rules/data/safety/`** (+ `skills/`, `config.py` crisis block): any PR touching a safety rule file requires Lane-1 review. Structural, not procedural — GitHub enforces it. Needs Lane-1's GitHub team/handle to wire (left unfilled here deliberately — owner sets it).
- Alternative — mandatory rebase-onto-master before merging any PR that touches `rules/data/safety/`. Procedural, weaker (relies on the author remembering).

## 6. Side finding (Lane-1 / S2-MARBERT)
The LLM intent layer **over-escalates figurative venting to crisis** ("could strangle him" → crisis card) — the inverted FP-asymmetry the #219 packet named (a crisis card to someone venting is trust-damaging over-escalation). The deterministic layer correctly holds; the LLM layer does not. Pre-existing, unchanged by this deploy — a crisis-FP-precision item for the S2/MARBERT classifier work.
