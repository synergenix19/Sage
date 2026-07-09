# Clinician Approval Queue (2026-07-09) — rendered content + recommendations, one-touch approve/edit/reject

Each item shows the **rendered wording/patterns** (not just the question), so one approval covers the faithfulness rule. Recommendations are engineering-clinical reads vs best practice + spec (spec_version_sha=56fde86); the ruling is the clinician's.

## 1. §6b/§6c rehome → `interpersonal_effectiveness` (DEARMAN) — RECOMMEND APPROVE
**Why:** spec §6b step-4 *"walks through DEARMAN one letter at a time"*; DEARMAN is `interpersonal_effectiveness`'s core DBT technique (assertive_communication is DESC). So this is the spec-primary skill — fixing a fit error, with the different-neighborhood (margin) benefit as a bonus. The clause is **scoped to §6b/§6c prep**, not the whole boundary/relationship territory.
**Rendered clause (prepended to interpersonal_effectiveness.semantic_description):**
> *"Interpersonal effectiveness DEARMAN skill for preparing a specific difficult, tough, or hard conversation, setting a boundary you need to raise, or wording, drafting, or rehearsing what to say or send before that conversation."*
→ **approve / edit wording / reject** (on approve: full signed gate per mechanism 4 — verify id_oos margin + §6b/§6c recall + no new leak before ship).

## 2. #219 harm-to-others deterministic backstop — RECOMMEND APPROVE Group A now, rule Group B
**Why:** Layer 2 found harm-to-others escalates only via the LLM classifier (`crisis_tier=none`, no deterministic net) — a paraphrase it misses has no backstop, unlike SI. A deterministic guardrail (like the harm-intrusive + OCD vetoes) → crisis/escalation path. Also upstream of the safeguarding family (third-party harm overlaps), so shipping it first means safeguarding lands on a fail-safe surface. **Caution: harm-to-others carries far more figurative usage than harm-intrusive ("I could kill him" = often venting), so the FP direction is harder — hence the two groups.**
**Group A — explicit intent (recommend APPROVE, near-zero figurative):** `want to hurt him/her/them/someone`, `going to hurt him/her/them`, `feel like hurting someone`, `planning to hurt`, `want to make them pay`.
**Group B — anger-adjacent (recommend HOLD for your ruling, figurative-heavy):** `so angry I could hurt`, `could kill him/her`, `want to hurt them so bad`, `might do something I regret`.
→ **approve Group A / add-or-move Group B items / reject.** (Seed fixtures = Layer 2's transcripts; on approval I build the deterministic veto exactly like harm-intrusive + full gate.)

## 3. #218 OCD referral line — RECOMMEND APPROVE (content only)
**Why:** the OCD veto fires but the served copy lacks the spec §1d professional-referral signpost. Pure content edit to the vetoed-OCD Node-3 response; no architecture.
**Rendered copy:**
> *"It sounds like these thoughts are really distressing and hard to sit with. Thoughts like these often respond well to support from a mental health professional who works with OCD, they use specific approaches that can genuinely help. I'm here to keep talking in the meantime if that would help."*
→ **approve / edit / reject.**

## 4. Containment Task 0 — clinical-lead signature (see chase note below)
The containment-as-destination + ego-syntonic branch + template steps (`2026-08-... clinical-containment-pathway-design.md`, PR #200). Already-ruled decisions assembled. → **sign / edit / reject.** This is the oldest open gate and blocks the dated safeguarding family (below).
