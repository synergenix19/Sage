# Schema Proposal: `emotions_disclosed` — Session-Scoped Operational State Field

**Proposal type:** SageState operational-state addition  
**Rule 1 deviation class:** Operational-state addition — not a seventh therapeutic component; §6 unchanged  
**PDPL reviewer required:** Yes (data-minimization boundary, retention trigger)  
**Clinical reviewer required:** Yes (emotion-term lexicon scope, suppression semantics)  
**Status:** BLOCKED — §5 clinical decision is a prerequisite; do not route to Rule 1 until §5 resolves  
**Author:** sage_clinics  
**Date:** 2026-05-31  

---

## BLOCKING PREREQUISITE — §5 must resolve before this proposal routes

The schema shape (§2) is downstream of the §5 clinical decision, not parallel to it. The two possible outcomes produce different implementations:

| §5 outcome | Schema shape | PDPL surface |
|-----------|-------------|-------------|
| **Permanent within-thread suppression** | `list[str]` accumulated across turns, checkpointed in Supabase | Retained for thread lifetime; full PDPL review required |
| **Immediate-following-turn only** | No persisted field — read Node 1's per-turn matches in composer directly, never checkpoint | No new personal data retained; PDPL surface collapses |

A flat accumulating `list[str]` can only express "is this emotion in the named set?" — permanent semantics. It carries no turn index, so it cannot express immediate-turn-only suppression. Building and checkpointing the field before the clinical answer is confirmed bakes the permanent answer into the schema while §5 still calls it open. Resolve §5 first; update §2 to match the outcome.

**§5 clinical question (route to clinical team):**

> Is the suppression rule for `emotions_disclosed`:
> (A) **Permanent within-thread** — once a user names an emotion, the model never re-probes it for the remainder of that conversation; or
> (B) **Immediate-following-turn only** — the model does not re-probe in the turn immediately after the emotion is named, but may return to it therapeutically in later turns (e.g., inviting elaboration, deepening)?
>
> Clinical note: option A prevents a type of redundant questioning but may over-suppress therapeutic deepening in long sessions (e.g., "sad" named in turn 3 can block elaboration in turn 15). Option B is harder to enforce deterministically — it implies per-turn transient state rather than a persisted field. The distinction also determines the data structure and whether any personal data is retained.

---

## Context

The `L2_new_skill_unmatched` template (Fix 2 of the 2026-05-31 unmatched-disclosure analysis) requires a deterministic record of emotion terms named by the user within the current conversation thread. Without it, the structural constraint "do not re-probe feelings already named" is LLM-discretionary and cannot be enforced deterministically — the root cause of the "how are you managing those feelings" anti-pattern observed 2026-05-31.

This proposal covers the field definition, write mechanism, lifecycle, read contract, and audit wiring. It does not cover the `L2_new_skill_unmatched` template itself, which is tracked separately and requires its own clinical review. **This proposal assumes §5 resolves to option A (permanent within-thread)**; if §5 resolves to option B, the proposal is replaced by a simpler per-turn transient read with no new field.

---

## 1. Write Mechanism (primary design decision)

Detection is **deterministic**, not LLM-inferred.

**Node:** Node 1 (`safety_check`) — the existing keyword-detection stage that evaluates `message_en` against the Rules Service before any graph bifurcation. This is the correct execution slot: pre-bifurcation, deterministic, negligible latency, consistent with the Rules Service pattern already used for crisis and clinical-flag detection.

**Audit note — operational vs safety signal:** `emotions_disclosed` detection rides on Node 1's execution slot for timing, not for safety classification. The field is operational/conversational state and must not be conflated with crisis or clinical-flag signals in the output_gate audit record. These are distinct categories with distinct clinical meanings.

**Mechanism:** New rule category `"emotion_terms"` in the Rules Service, following the same evaluation pattern as clinical-flag keyword detection. On match against the emotion-term lexicon, the rule returns matched terms. The Node 1 handler performs a **node-side read-modify-write**: reads `state.get("emotions_disclosed", [])`, computes the updated list via `list(dict.fromkeys(existing + new_matches))`, and returns the full updated list as the new field value. No LLM call; no probability threshold. The return value is the whole field, not a delta — this is the accumulation mechanism and it must be explicit in the implementation.

**Negation and attribution scoping (required before clinical sign-off):** Bare keyword matching will wrongfully suppress in at least three common cases:

- **Negation:** "I'm *not* sad", "I *don't* feel hopeless", "I *never* feel angry" — the negated emotion should not be appended.
- **Attribution to third party:** "my mum is worried about me", "he feels hopeless" — affect attributed to someone other than the user should not be appended.
- **Physical sense:** "hurt" is polysemous — physical pain and abuse disclosure are distinct from affect naming. `hurt` may belong in clinical-flag territory rather than the emotion suppression lexicon.

The implementation requires a negation window check (±3 tokens before the matched term) and a basic attribution filter (subject detection, or at minimum a first-person vs third-person signal). This is no longer a bare keyword lookup — it is a small NLP filter, and imperfect. Two open questions that must resolve before clinical sign-off:

**Match field — language-dependent:** §1 currently pins detection to `message_en`. For Arabic/Khaleeji disclosures, `message_en` is a machine translation, and negation particles and subject-attribution are precisely what translation distorts — a dropped negation particle or a flipped subject silently produces a false suppression. The authoritative match field must be language-conditional: `message_en` for English turns; `raw_message` (original Arabic) with Arabic morphology-aware negation patterns for Arabic turns. Translating-then-scoping inherits the translator's errors at the exact step where an error means suppressing a feeling the user negated. This is a clinical and implementation decision — route to clinical reviewer alongside the lexicon.

**Failure-direction preference (clinical call, not implementation):** The two error directions are not equal. A false append — suppressing a feeling the user did raise — is clinically worse than a false miss — failing to suppress, meaning the model re-probes, which is annoying but not harmful. When the negation/attribution filter is uncertain, the default must be to **not append** (fail toward re-probing, not toward silence). This applies especially near the crisis boundary (`hopeless`, `numb`). The clinical reviewer must set this bias explicitly; it cannot be left to implementation discretion.

Near-crisis terms (`hopeless`, `numb`) require explicit clinical sign-off on whether they belong in this lexicon at all or only in clinical-flag detection — false-positive suppression near the crisis boundary dampens follow-up exactly where it should not.

**Lexicon scope (requires clinical sign-off; conditional on negation/attribution handling above):**

Example English candidates:
```
sad, upset, angry, anxious, afraid, scared, hopeless*, lonely, numb*,
overwhelmed, frustrated, guilty, ashamed, worried, devastated, grieving
```
`*` — `hopeless` and `numb` flagged for clinical-flag boundary review before inclusion.  
`hurt` — removed pending polysemy decision; treat as clinical-flag candidate.

Arabic equivalents follow the MARBERT-validated keyword convention used in S1 and clinical-flag rules. Arabic lexicon requires the same clinical sign-off plus negation handling in Arabic morphology.

**Deduplication:** `dict.fromkeys()` pattern — preserves insertion order for clinical audit, consistent with the `si_explicit` dedup convention confirmed 2026-05-31.

---

## 2. Placement and Tier

*Conditional on §5 resolving to option A (permanent within-thread).*

- **Field name:** `emotions_disclosed`
- **Type:** `list[str]`
- **Default:** `[]` (empty list at thread start)
- **Tier:** Session-scoped operational state — peer to `active_skill_id`, `current_step`
- **Not a seventh enriched-therapeutic-state component.** The six §6 therapeutic components are unchanged. This is conversational/operational state whose function is within-thread re-probe suppression.
- **Rule 1 deviation framing:** Operational-state addition, smallest correct form.

If §5 resolves to option B, §2 is replaced by: no new field; transient per-turn matches read from Node 1's rule output within the same turn only.

---

## 3. Lifecycle and PDPL Boundary

**Session boundary definition:** "Session" is defined as a LangGraph `thread_id`. A new conversation (user action: `+ New conversation`) creates a new thread with a fresh SageState, including `emotions_disclosed: []`. The field never crosses thread boundaries. No explicit clearing mechanism is required — isolation is structural, enforced by the `thread_id` scope.

| Event | Action |
|-------|--------|
| New thread created | Field initializes to `[]` |
| Node 1 matches emotion term (post negation/attribution filter) | Node-side read-modify-write; full deduplicated list returned |
| Turn boundary (same thread) | Persists in checkpointed state |
| New thread created (new conversation) | Field initializes to `[]` — prior thread's value is not carried |
| Therapeutic Profile write | **Never** — field is never promoted to the Therapeutic Profile |

**Checkpoint store:** Current implementation uses Supabase via `AsyncPostgresSaver`. The field definition is store-agnostic — it is a Python `list[str]` in LangGraph state, serialized by whichever checkpointer is active. Migration to production infrastructure requires swapping the checkpointer only; the field definition and write mechanism are unchanged.

**PDPL data-minimization rationale:** Emotion terms are retained for the active thread's lifetime only. Sole purpose is within-thread re-probe suppression. Promotion to the Therapeutic Profile would retain emotion-word history across threads beyond its functional need.

**PDPL retention dependency:** Thread-scoped data in Supabase persists according to the checkpoint retention policy configured for the deployment. The PDPL boundary requires that this retention policy be documented and proportionate. The PDPL reviewer must confirm the existing policy is documented before approving.

---

## 4. Phasing — Write and Read Ship Together

**Phase 1 (no state changes):** The `L2_new_skill_unmatched` template with static prose constraints only. No field, no write, no PDPL surface. This phase can ship on Rule 1 + clinical template approval alone.

**Phase 2 (atomic — write + read in one release):** The `emotions_disclosed` field is written (Node 1 rule) and consumed (L2 binding in composer) in the same deployment. Collection and purpose coincide at every point the system is deployed. A v0.1 that writes-but-never-reads would persist personal affect data with no active purpose — contradicting the PDPL data-minimization rationale. Phase 2 requires this proposal's full approval stack (Rule 1 + PDPL + clinical).

**Note:** Phase 2 budget check for the L2 binding (v0.2) must be against the worst-case rendered string, not the template literal. The emotion list is truncated to three terms (`emotions_disclosed[:3]`); if more than three are present, renders as `"[first], [second], [third] (and others)"`. Worst-case: static ~28 words + `{intensity}` (1) + `{intensity_guidance}` (~8) + truncated list clause (~10) ≈ 47 words. Within the 50-word cap. The `[:3]` truncation means emotions four and onward are eligible for re-probing — this is best-effort suppression under truncation and must be documented in the spec rather than silently assumed.

**Merged constraint (Phase 2 only — avoids duplicate directive):** The static prose "Do not re-probe feelings they have already named" is *replaced* (not added to) with the bound version:

```
Named this session: {emotions_disclosed} — do not re-probe these.
```

**Empty-case:** When `emotions_disclosed` is `[]`, the bound clause is suppressed entirely. The static prose handles the empty case in Phase 1; Phase 2 suppresses the clause rather than rendering a null antecedent.

---

## 5. Suppression Semantics — PREREQUISITE CLINICAL DECISION

See **BLOCKING PREREQUISITE** at the top of this document. The clinical team must answer the question there before §2 and §4 (Phase 2) are finalized.

This section exists to surface the question, not to answer it.

---

## 6. Audit Wiring and Tests

**output_gate audit record (§13.1):** `emotions_disclosed` is included in the per-turn audit record alongside `clinical_flags`, `active_skill_id`, and `crisis_state`. It is labelled as an operational field distinct from safety/clinical-flag signals.

**Required tests before Phase 1 write-side merge (tests 1–8 must be green before any affect data is persisted):**

1. Emotion term in message → field written with correct term at Node 1
2. Negated emotion term ("I'm not sad") → term NOT appended
3. Third-party attribution ("my mum is worried") → term NOT appended
4. Same term repeated in a later turn → no duplication; insertion order preserved
5. No emotion term in message → field unchanged
6. New thread → field initializes to `[]`; prior thread's value not accessible
7. Field is absent from Therapeutic Profile after thread end
8. output_gate audit record includes `emotions_disclosed` for each turn, labelled as operational

Tests 6 and 7 are the PDPL/isolation guarantees — they must pass before any affect data is checkpointed, not just before Phase 2.

**Additional tests required before Phase 2 binding merge (9–11 gate the L2 read contract):**

9. Composer reads field; suppresses redundant follow-up question for a named emotion
10. Empty list → bound clause suppressed in rendered template
11. List > 3 terms → truncated to 3 with "(and others)"; budget not exceeded

---

## 7. Approval Gate

| Reviewer | Scope | Blocking? |
|---------|-------|-----------|
| §5 clinical decision | Suppression semantics: permanent vs immediate | Yes — gates entire proposal |
| Rule 1 approver | Operational-state addition; deviation framing | Yes — Phase 2 |
| PDPL reviewer | Data-minimization boundary; retention policy confirmation | Yes — Phase 2 |
| Clinical reviewer | Emotion-term lexicon (English + Arabic); negation/attribution handling; match field language-conditionality (message_en vs raw_message for Arabic turns); failure-direction preference (fail toward re-probing, not silence — must be set explicitly, not left to implementation); near-crisis term boundary (hopeless, numb — clinical-flag candidates) | Yes — Phase 2; lexicon, match-field, and failure-direction decisions also affect Phase 1 write mechanism |

---

## Dependencies

| Item | Status |
|------|--------|
| §5 clinical decision (suppression semantics) | **BLOCKING** — must resolve before this proposal routes |
| `L2_new_skill_unmatched` template (Phase 1, static) | Draft — can route to clinical review independently of this proposal |
| `L2_new_skill_unmatched` template (Phase 2, bound) | Not drafted — awaits this proposal's full approval |
| `composer.py` selector logic | Specced — `(primary_intent == "new_skill") AND (active_skill_id is None)` selects `L2_new_skill_unmatched` |
| `grief_loss` skill (Fix 4) | Blocked — inventory reconciliation; see `2026-05-30-arabic-kb-skills-expansion.md` Task 9 |
| Fix 1 (Tier 2 dual index) | Standalone §4.3 evaluation; independent of this proposal |
| L2 authority tier (Flag A) | Open architectural-review item — all L2 templates delivered as user-role; control instructions share injection surface with user turns |
