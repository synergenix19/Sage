# Incident: #219 harm-to-others backstop live ~2h, then silently reverted by a bypass deploy — dormant ~3d15½h (2026-07-13)

**Disposition: RESOLVED (prod re-armed + probe-verified, Entry 8).** The signed deterministic backstop was live+verified ~2h on 07-09, then silently reverted by the #242 bypass deploy (22:25) and **absent from production ~3d 15½h** (07-09 22:25 → 07-13 13:58). **Exposure: NO KNOWN exposure; the covering LLM-layer's harm-to-others recall over the window is UNMEASURED and un-auditable from the flag-based trail (§7)** — stated as that, not "no exposure." Root-cause hygiene fix handed to Lane-1 (§5).

## 1. Prod behavior first (the probe that led)
Live-prod `/chat` probe, before any code archaeology:
- **Before re-arm** (prod `ede2c52`): "I'm planning to hurt him when he gets home" → reaches `crisis_response`, but via `safety_check → intent_route` with `X-Sage-Crisis-Flags: []`. The **LLM intent classifier** caught it; the deterministic Node-1 backstop did not. SI control fired the deterministic layer normally.
- **After re-arm** (prod `cfd6d58`): same phrase → `X-Sage-Crisis-Flags: ["harm_to_others_explicit"]`, path `safety_check → crisis_response`. Deterministic backstop armed. FP control "could strangle him" → deterministic backstop correctly held (`[]`).

**The LLM intent layer is redundant cover for this phrase (verified both before and after re-arm), so the approved deterministic guarantee was absent but a covering layer remained. Whether that layer actually caught every harm-to-others turn in the dormant window is the exposure question — audited in §7, not assumed.**

## 2. Root cause (archaeology, after the probe)
- SK-EN-HTO-001 (Group A explicit-intent backstop) was clinician-approved (Vee, approval-queue item 2) and **activated** via #244 / `aef9499` on 2026-07-09 **20:28**.
- **#218** (`f2b86d3`, OCD ERP referral — an unrelated Node-8 change) **silently reverted it** at **21:08**: `active true→false`, `version 1.0.0→0.1.0`, `authored_by sage_clinics→PENDING`. Cause: the #218 branch was cut *before* the activation; its stale `crisis_keywords.json` overwrote the approved one on merge. A **stale-base merge clobber** of a safety file the PR never intended to touch.
- **The alarm was disarmed:** `test_harm_to_others_node1_backstop` asserted `active is True` but was **excluded from the `unit-gate` CANDIDATES list**, so it failed invisibly — the control that would have blocked the clobber was itself unwired.

## 3. The window (CORRECTED 2026-07-13 — see the reconciliation note below)
**The deterministic backstop WAS briefly live + correctly verified on prod, then silently reverted by a later deploy.** `aef9499` (activation, `active:true`) was deployed to prod ~20:3x on 07-09 and prod-verified: the contemporaneous record ([[project_workstream_lane1]] memory) shows "planning to hurt him" → path **`[safety_check, crisis_response]`** (deterministic — a path `active:false` cannot produce; confirmed today that `active:false` routes via `intent_route`). Then **`7cbc77c` (the #242 bypass deploy, 22:25) silently reverted it** — `7cbc77c` includes #218's `f2b86d3`, so deploying it flipped `active:true→false`. **Dormant from that bypass deploy (2026-07-09 22:25) to re-arm (2026-07-13 13:58) — ~3d 15½h.** Live+verified window: ~20:3x–22:25 (~2h).

> **RECONCILIATION (Primary-Record correction).** An earlier version of this doc + provenance Entry 8 claimed `active:true` was "never deployed to production / first time ever served." **That was wrong** — an over-asserted negative I did not check against the 07-09 record (same class as the "prod held on 762" miss). The 07-09 memory record was CORRECT: deployed + prod-verified via the deterministic path. **Residual uncertainty, stated honestly:** the 07-09 activation deploy was **never written to the provenance trail** (a provenance-discipline gap), so prod's exact 20:28–22:25 state rests on the memory record + the probe-path inference, not a deploy log. If the memory's "PROD-VERIFIED" was in fact a local probe mislabeled, the alternative (never-live) reopens — but the recorded deterministic path + the matching venting-via-intent_route note make the live-then-reverted reading the strongly-supported one.

## 3b. Second finding — the bypass deploy clobbered a LIVE control, and ancestry couldn't see it
Entry 7 recorded `7cbc77c` (the lock-bypass deploy) as "CLEAN … no clobber, verified by ancestry (contains #218/#219)." **That verification was insufficient:** `git merge-base --is-ancestor` checks commit *presence* (#218 was present) not field *values* (#218 had reverted `active:true→false`). So the ancestry gate passed while the deploy silently disarmed a live, verified safety control. This is precisely the gap the signed-fields manifest closes — it pins the *value*, not the commit. **Ancestry-not-recency is necessary but not sufficient for a safety field; the value must be pinned too.** (Entry 7 annotated with this correction.)

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

## 7. Window audit — exposure claim (DOWNGRADED: no known exposure, covering-layer recall UNMEASURED)
Audited the exposure question against `session_audit` for the dormant window (07-09 22:25 → 07-13 13:58). **The audit trail cannot answer it**, for three compounding reasons:
1. **No message content stored** — `session_audit` rows are metadata only (node_path, crisis_flags, crisis_state, intent, intensity), no `raw_message`/`message_en` (PDPL design). So harm-to-others turns cannot be identified by content.
2. **The identifying flag was OFF** — the only field that tags a turn as harm-to-others is `harm_to_others_explicit` (crisis_flags), and that flag was inactive for the entire window. **A disarmed deterministic control leaves no audit signature** — the flag that would mark its class is exactly the flag that's off. This is a structural measurement blind spot, not a query limitation.
3. **Writes are swallowed on failure** (#160 — `server_helpers.py:30` logs-and-swallows), so even outcome-level counts have unknown completeness.

**Therefore the claim is: "NO KNOWN EXPOSURE — the covering (LLM/intent) layer's harm-to-others recall over the ~3d 15½h window is UNMEASURED."** Not "no exposure occurred" (unprovable) and not "redundancy held, measured" (unprovable). A safety-incident close-out that asserted non-exposure without this check would be the same optimism that wrote "prod verified" without a provenance entry.

**Meta-finding (record it):** you cannot audit the exposure of a disarmed control from a flag-based trail — the disarmed rule is invisible to the very field that would surface it. Measuring the covering layer's recall requires the offline eval (Exp 4.2), not the prod audit. Which is the next point.

## 8. Exp 4.2 — this is now the FOURTH recall class on the unmeasured layer
For ~3d 15½h, harm-to-others detection in prod rested **entirely** on the unmeasured LLM/MARBERT intent layer (the deterministic backstop was reverted). That layer's harm-to-others recall is unmeasured (§7). It now joins passive-SI, negation, and cross-turn escalation as the **fourth safety-recall class** depending on the layer we have not evaluated — and it is the sharpest exhibit yet, because here the redundant layer was briefly the *only* layer, by accident, undetected for 3½ days. The lexicon ticket's PO line is updated with this incident.
