# Clinical Containment Pathway — Deviation Design Spec (for 3 signatures)

> **Absolute Rule 1 architecture deviation.** This spec amends the v7 graph edges, `SageState` schema, and Rules Service action vocabulary. It is the artifact for the three sign-offs below. No Phase-2 implementation (plan Tasks 1-9) begins until all three are recorded. Most content here is **assembly of decisions already on the record** (2026-07-08 clinician approval + PO rulings); this document collects them so the signatories sign one coherent design.

## 1. The gap (why this is a new destination class, not a fix)
Today a turn ends in one of four places: route-to-skill, abstain-to-Node-3, crisis, freeflow. There is no first-class outcome for a **clinically-significant, non-crisis disclosure that must not get a self-help skill and deserves better than bare clarification**. The clinical flags already name this territory but nothing about the served response changes. **Containment is the response-side half the flag system has been missing.** It matches the BOT BEHAVIOUR spec, which already prescribes exactly this for OCD/intrusive content (pinned spec `56fde86`: "route to professional referral… separate from the crisis guard"). The postpartum→worry_time routing was a **documented spec deviation**, now closed at Phase 1 by the deterministic veto.

## 2. Design (six points)
1. **State:** `containment_directive = {family, flag_level, kb_topics, containment_skill_id?, rule_id}`, set only by deterministic rules, reset per turn (like `path`/`skill_select_abstained`), fully audited.
2. **Rules Service:** a fourth action `contain(family, flag_level, kb_topics, skill_id?)` — CMS-authorable via draft→review→approve→publish. Supersedes bare `abstain` for families that have it.
3. **Graph:** ONE conditional edge, no new node. Directive present → `knowledge_retrieve` (seeded `kb_topics`) → `freeflow_respond` (L3+L4 enriched), or `skill_executor` if a containment skill exists.
4. **Prompt layers:** retrieved KB article → existing **L4** (~300w via Node 6); containment few-shot/tone/step → **L3** skill-context (template-owned). NO new layer; per-layer budget asserted, total ≤ ~1,100w.
5. **Escalation template:** `validate → psychoeducate → differentiate → risk-check → REFER → engage` (professional-referral signpost REQUIRED per spec; risk-check woven in naturally, not led with). Reusable skeleton; per-family differentiation + branches are clinical content.
6. **Audit + queue:** Node 8 logs `family, rule_id, kb_ids, flag_level`; `flag_level` writes the 24h **L2 clinician review-queue** entry (asserted, not just an audit row).

## 3. Decisions already ruled (assembly)
- **Crisis supremacy:** containment is evaluated AFTER Node 1's crisis short-circuit; never competes with it (pinned spec `56fde86`, universal crisis override).
- **EGO-SYNTONIC / PSYCHOSIS deterministic branch (clinician-added, safety-critical):** absence of distress about the harm thought, ego-syntonic framing, or command-hallucination language → **crisis-path, NOT containment**. Maternal psychosis is a medical emergency; ego-dystonic distress ("it scares me") is the REASSURING marker. Sage screens + escalates, never adjudicates (no-autonomous-clearance).
- **Escalation → v7 tier vocabulary:** risk-positive → **L3 safety protocol** (`crisis_response`); continued containment → **L2 flag**. Clinician signs in their own taxonomy.
- **Family split:** first-person ego-dystonic intrusion → containment/referral; third-party or behavioural-indication report → **safeguarding family**.
- **Guardrail integrity:** on a containment/veto turn, `suggest_skill` is unbound — a guardrail is not optional through a tool.
- **Bilingual/cultural mandatory:** AR+EN few-shot ≥3, `cultural_overrides`, Khaleeji rendering of clinical terms clinician-ruled, per-language KB fail-safe (AR falls back if AR content not ready), never-assume-by-name/language/location.
- **Detection roadmap:** the deterministic keyword veto is a **permanent Tier-1 guardrail**; a semantic S2-MARBERT classifier (Gap #65) is ADDED later as a second layer (defense in depth), not a replacement.

## 4. Bounded build scope (do NOT let the audit unbound it)
Phase 2's build scope is **only the already-approved families**: (1) harm-intrusive **enrichment** (Phase-1 veto's destination abstain→contain), (2) OCD-compulsion **upgrade** (abstain→contain), (3) **safeguarding family — #1 priority, TARGET 2026-07-31** (posture: referral-with-urgency + mandatory L2 review, distinct from suicide-crisis; tier L3-adjacent, clinician-ruled). The BOT BEHAVIOUR audit will discover more Class-A candidates; those go to the CMS backlog the clinician prioritizes on their clock — **they do NOT enter Phase 2's scope by discovery.** A bounded architecture change stays bounded.

## 5. Sign-offs (record here before any implementation)
- [x] **Arch-doc owner** — SIGNED: Rohan (PO/arch-doc owner) 2026-07-09. — the graph-edge / state-schema / Rules-Service-vocabulary amendment. Signature + date:
- [x] **Clinical lead** — SIGNED: Vee (clinical lead) 2026-07-09. — containment AS a destination class; the template steps + ego-syntonic branch + family split + safeguarding posture + Khaleeji renderings. (Harm-intrusive lexicon + phasing already approved 2026-07-08.) Signature + date:
- [x] **PO** — SIGNED: Rohan (PO) 2026-07-09. — Absolute Rule 1 acceptance; the bounded-scope discipline (§4); the 2026-07-31 safeguarding target. Signature + date:


## ✅ TASK 0 FULLY SIGNED 2026-07-09 — Vee (clinical lead) + Rohan (arch-doc owner + PO). Containment Phase 2 (Tasks 1-7 + the safeguarding family, target 2026-07-31) is UNBLOCKED to build.
