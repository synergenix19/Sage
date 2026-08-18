# §1a Skill-Request Delivery (presence_only Gap) Implementation Plan — v2 (post-review)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Revision note (v2, 2026-07-28):** amended per architecture/clinical review. Blocking findings B1 (screening state gates the binder), B2 (AR reaches the binder through translation; gate on session language), B3 (third decision-gate branch: intent-taxonomy fix) integrated. Material corrections M1 (POC stand-in for Active Issues List), M2 (single symptom-matcher surface; write-site decided by Phase 0 routing evidence), M3 (dissociation guard moves to Clinical Flags), M4 (binder renamed `zero_candidate_request_binder`), M5 (moderate binding dropped from v1 scope, documented) integrated. Coverage gaps (crisis, AR, audit-trail, step-up, latency) added to Tasks 6–8.

**Revision note (v3, 2026-07-28):** Phase 0 approved to execute. C1a/b/c integrated (screen design: duration mandatory before any offer, red-flag quality clause conditional on physical-symptom mention, `cleared` derivable from disclosure content). C2 integrated (chronic-case spec-internal conflict marked for clinician adjudication, not silently resolved). C3 integrated (every guard asserts the positive alternative path; `diverted` test added; medical-guard existence = Phase 0 Q6). Minors: shared `matching.py` module, audit assertions extended to skill id + model version, cross-session `cleared` added to migration note, scope-lock comment. C1/C2 artifacts travel to the clinician in ONE packet; they gate Task 5 Step 3b, not Phase 0.

**Goal:** When a user in an established, screened mild-anxiety context explicitly asks for an exercise/tool, the bot offers the §1a Tier-1 skill choice (box_breathing + grounding_5_4_3_2_1) through the existing R1 consent gate, instead of deflecting into exploration.

**Architecture:** No new delivery machinery. The R1 consent gate's `default_offer` path already renders the spec's step-4 behavior (offer of ≤2 skills with plain-language blurbs via `L2_skill_offer`). The gap is upstream: an explicit skill request carries no symptom language, so it produces zero candidates in `skill_select`. The fix is a deterministic `zero_candidate_request_binder`: a data-file lexicon of request phrasings + a session presentation-context channel **that carries §1a screening state**, feeding candidates into the existing consent gate **only when the screen is cleared**. All behind a default-OFF flag. If Phase 0 shows the request never reaches `skill_select` at all (intent misclassification), the primary fix moves to `intent_route` and the binder becomes contingent (decision gate, Task 2).

**Tech Stack:** Python (LangGraph graph in `sage-poc/src/sage_poc/`), pytest, existing rules-engine + consent-gate + clinical-flags machinery, conformance matrix runner.

## Global Constraints

- **Characterize before build:** Phase 0 must confirm the mechanism full-graph before any Phase 1 code is written. The Task 2 gate has THREE branches; do not collapse them.
- **Screening gates delivery (B1+C1):** the binder never offers on an unscreened context, and the screen is ADAPTIVE: it asks only what the session has not already supplied (§1a: "don't ask what's already been said"). `cleared` is derivable from disclosure content when onset/trigger is present and no red-flag descriptors appeared; the dedicated screen turn is the fallback for cold contexts, not the sole path (C1c). Duration is MANDATORY before any offer: `chronicity: unknown` never passes, and the screen asks duration whenever the session has not supplied it — it is the §1a Mild core question and the sole reliable "more than mild" discriminator (C1a; the Moderate flow's duration-skip is a deliberate acute-tier tradeoff that does NOT transfer to Mild). The red-flag quality clause fires ONLY when physical symptoms were mentioned in the session (§1a: "only if physical symptoms are mentioned"; blanket cardiac framing to a non-somatic presentation is a health-anxiety amplifier) (C1b). Tier derivation: conflict defaults to the higher tier; intensity alone never proves "mild".
- **Spec conflicts are adjudicated by the clinician, not the implementer (C2):** BOT BEHAVIOUR §1a is internally inconsistent on the chronic case (section 6 guard: referral "instead of" self-guided tools; section 2 routing logic: skill "alongside" referral when the user wants one). The implementation takes "alongside" as the more specific passage BUT the packet names the conflict, presents both readings, and marks the choice PENDING Vee's ruling; condition 7 isolates it so a ruling is a one-branch change, not a rewrite.
- **Guards assert the positive path (C3):** every guard test asserts the alternative pathway FIRED (acute offer, HR referral, medical guard, crisis response), never merely that the binder stayed silent. The failure direction of these guards is "offer nothing", which is indistinguishable from the presence_only gap this plan exists to eliminate.
- **Language-gated, not list-gated (B2):** AR sessions reach the binder with translated `message_en`; the EN lexicon WILL match them. The binder gates on session language: `detected_language == "ar" and not AR_VALIDATED` → skip, regardless of which list matched. Asserted with an Arabic-input test.
- **Skill Description Principle:** `semantic_description` is technique identity ONLY. Do NOT fix this gap by adding request language to any `semantic_description`. A `calibrate_threshold.py` re-run motivated by this plan is a plan violation.
- **Single symptom-matcher surface (M2):** exactly one symptom lexicon (`target_presentations` via `SKILL_REGISTRY`) and one matcher implementation, shared by Tier 1 and the breadcrumb writer. No second symptom keyword list anywhere, in any node.
- **One source of truth for presentation (M1):** the enriched-state Active Issues List is NOT implemented in the POC (verified: zero references in `src/`). `recent_presentation` is a POC stand-in for it, declared as such in code comment and packet, with the migration path named (fold into `active_issues` when that component lands; the binder then reads the most recent anxiety-family issue's screening state).
- **State-channel seam (#191/#205/SG-2):** every new SageState key: declared, per-turn/clear semantics explicit, `check_state_channels.py` manifest, graph-level test.
- **Contraindication guards are positive and persistent (M3):** dissociation/derealization gating uses Clinical Flags (existing persistent, auditable mechanism), consulted positively by the binder. Absence-of-a-write is never a guard. Do NOT alter flag persistence config (Clinical Flag Lifecycle guardrail).
- **Assert on behavior, not prose:** tests assert on state, `path` markers, and audit records, never response copy.
- **Fixture independence (E7 lesson):** conformance fixtures must be naturalistic phrasings, never lexicon entries verbatim (CI-checked).
- **Regression-by-improvement (both-direction fixtures):** OCD iatrogenic veto (PR#155), bare-emotional-words guard, §1f curiosity routing (PR#362), dissociation/derealization guard, declined-skill no-reoffer, crisis preemption, acute-path precedence.
- **No em dashes in rule action content** or any JSON copy the LLM can render. Use commas.
- **Clinical sign-off:** the flag does not flip ON in prod without clinician (Vee) sign-off. Consent-gate artifacts are themselves `draft-pending-review`; this plan rides that governance train.
- **Measurement parity:** matrix re-runs go through the parity-enforcing runner (PR#360) only.
- **Deploy:** default-OFF flag `SAGE_SKILL_REQUEST_DELIVERY`; `deploy_prod.sh` with ancestry check; rollback = flag off.
- **Latency budget:** binder adds one substring pass over a ≤32-entry lexicon plus one dict lookup on the zero-candidate path only; budget ≤1ms, no LLM call, no embedding call. Stated in packet; violated = finding.

## File Structure

- `tests/fixtures/conformance/1a_transcript_replay.json` — Phase 0 replay fixture (observed 3-turn transcript)
- `scripts/characterize_1a_gap.py` — Phase 0 full-graph replay + audit-path readout
- `docs/superpowers/governance/2026-07-28-1a-gap-mechanism.md` — Phase 0 findings memo (decision-gate artifact)
- `rules/data/skill_matching/skill_request_phrases.json` — request-phrasing lexicon + generic binding table (data)
- `src/sage_poc/nodes/skill_select.py` — shared symptom matcher extraction + `zero_candidate_request_binder` (modify)
- `src/sage_poc/nodes/intent_route.py` — breadcrumb write-site IF Phase 0 shows disclosure turns bypass `skill_select` (modify, conditional)
- `src/sage_poc/state.py` — `recent_presentation` channel declaration (modify)
- `src/sage_poc/config.py` — `SAGE_SKILL_REQUEST_DELIVERY` flag (modify)
- `tests/test_skill_request_delivery.py` — unit + both-direction guard tests
- `tests/test_graph_skill_request.py` — full-graph seam + audit-trail tests

---

## Phase 0 — Characterize the mechanism (GATING)

### Task 1: Transcript replay fixture + characterization script

**Files:**
- Create: `tests/fixtures/conformance/1a_transcript_replay.json`
- Create: `scripts/characterize_1a_gap.py`

**Interfaces:**
- Produces: per-turn readout of `primary_intent`, `secondary_intent`, `emotional_intensity`, `intent_confidence`, node path (`state["path"]`), Tier-1 candidate list, Tier-2 best score + skill id, fired `skill_matching_rule:<id>`.

- [ ] **Step 1: Write the replay fixture** with the three observed user turns verbatim:

```json
{
  "case_id": "1A-NAT-000-observed",
  "provenance": "live transcript 2026-07-28, naturalistic, NOT lexicon-derived",
  "turns": [
    "I'm feeling anxious",
    "can you tell me how to manage my anxiety",
    "are there any exercises i can do"
  ],
  "spec_expectation": {
    "turn_3": "self_help_skill offer: box_breathing or grounding_5_4_3_2_1 (BOT BEHAVIOUR §1a step 4), AFTER §1a screen"
  }
}
```

- [ ] **Step 2: Write the characterization script.** Reuse the conformance runner's graph-invocation helper (in `scripts/bot_behaviour_audit/`); full-graph turns on one session thread. Per turn, dump the interface fields above plus `offered_skill_ids`, `active_skill_id`, and whether `skill_select` executed at all (presence in `path`).

- [ ] **Step 3: Run against local full graph** with prod flag parity (flags derived per `config.py`, matching serving config).

Run: `uv run python scripts/characterize_1a_gap.py`
Expected: three per-turn blocks. Record verbatim into the memo.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/conformance/1a_transcript_replay.json scripts/characterize_1a_gap.py
git commit -m "chore(1a): transcript replay fixture + gap characterization script"
```

### Task 2: Mechanism memo + three-branch decision gate

**Files:**
- Create: `docs/superpowers/governance/2026-07-28-1a-gap-mechanism.md`

- [ ] **Step 1: Write the memo** answering, with Task 1 evidence pasted in:
  - **Q1:** On turn 3, what did `intent_route` return, and did `skill_select` execute? (Note: `info_request` early-returns before the tiers; `general_chat` may route to freeflow without `skill_select` — both are "never reached matching".)
  - **Q2:** If matching ran, what did Tier 1 and Tier 2 produce?
  - **Q3:** On turn 1, did the disclosure turn reach `skill_select`? (Determines the breadcrumb write-site, Task 4: if disclosure turns bypass `skill_select`, the writer must live where those turns DO run, using the shared matcher.)
  - **Q4:** Do the 3 `presence_only` runs in matrix v5 §1a share this signature? YES/NO per run, from the v5 run artifacts.
  - **Q5 (systemic, RT-4/S-4):** Is Tier 2 functional and correctly thresholded? State the Tier-2 best score for turn 3 and for the naturalistic §1a misses, against `SEMANTIC_THRESHOLD`. The memo must say explicitly whether the binder is a targeted fix or a patch over a non-functional Tier 2; if the latter, name it as feeding the retrieval-core re-arch (skill_select as retrieval+ABSTAIN), and the binder ships anyway only as a bounded stopgap with that dependency recorded.
  - **Q6 (diverted-branch dependency, C3):** Does a medical-guard pathway exist and FIRE full-graph when the §1a universal cardiac red-flag descriptors appear? Run the standalone probe "i have crushing chest pain and it's spreading to my arm" and record the full path and user-visible outcome. If no medical-guard response fires, that is a BLOCKING finding escalated in its own right, independent of which gate branch is selected: the binder's `diverted` branch would otherwise produce silence with no medical prompt, the worst outcome in this feature.
- [ ] **Step 2: DECISION GATE, three branches:**
  - **(a) Request reached matching, zero candidates (M2-mechanism):** proceed to Phase 1 as written.
  - **(b) Candidates were produced but a rule/gate suppressed the offer:** STOP; the fix belongs in the consent-gate rules; amend this plan.
  - **(c) Request never reached matching (classified `info_request`/`general_chat`, or confidence-gated):** the PRIMARY fix is the `intent_route` taxonomy/definitions (a `new_skill` clarification or explicit-request signal), because a binder in `skill_select` cannot run on turns that never reach it, and a workaround leaves the classifier wrong for every other category (1b–1f, 3c, 4b, 6d, 7c). Amend this plan: intent fix first (with its own SPOF-guard regression tests), binder becomes contingent or unnecessary. Note: intent-prompt changes touch the bare-emotional-words SPOF; the guard test (`-k "bare_emotional_words"`) is a hard gate on that branch.
- [ ] **Step 3: Commit** `docs(1a): gap mechanism memo + three-branch decision gate`.

---

## Phase 1 — Fix (only after the Task 2 gate passes on branch (a); branches (b)/(c) re-plan first)

### Task 3: Request-phrase lexicon + generic binding table + flag

**Files:**
- Create: `rules/data/skill_matching/skill_request_phrases.json`
- Modify: `src/sage_poc/config.py`
- Test: `tests/test_skill_request_delivery.py`

**Interfaces:**
- Produces: `load_skill_request_data() -> dict` in `skill_select.py` (phrases + bindings); `settings.SKILL_REQUEST_DELIVERY: bool`; `settings.SKILL_REQUEST_AR_VALIDATED: bool` (default False).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_skill_request_delivery.py
from sage_poc.nodes.skill_select import load_skill_request_data

def test_request_lexicon_loads_and_is_lowercase():
    data = load_skill_request_data()
    assert len(data["phrases_en"]) >= 8
    assert all(p == p.lower() for p in data["phrases_en"])
    assert "are there any exercises" in data["phrases_en"]

def test_binding_table_is_generic_and_registry_valid():
    from sage_poc.skill_ids import SKILL_REGISTRY
    data = load_skill_request_data()
    for key, skill_ids in data["bindings"].items():
        category, tier = key.split("/")
        # DELIBERATE v1 SCOPE LOCK (M5): widen ONLY by adding a clinician-signed offer-table
        # row for the new tier/category, never by editing this assertion to "fix the test".
        assert tier in ("mild",)
        for sid in skill_ids:
            assert sid in SKILL_REGISTRY

def test_request_data_has_no_em_dash():
    import pathlib
    raw = pathlib.Path("rules/data/skill_matching/skill_request_phrases.json").read_text()
    assert "—" not in raw
```

- [ ] **Step 2: Run to verify failure.** Run: `uv run pytest tests/test_skill_request_delivery.py -v` — Expected: FAIL, `load_skill_request_data` not defined.

- [ ] **Step 3: Write the data file.** Bindings are a generic `category/tier -> skill_ids` table sourced from the BOT BEHAVIOUR offer tables, populated in v1 with the single signed row; the schema, not the row-count, is the generalization path (packet states it, so future categories are rows, not new binders):

```json
{
  "version": "2.0.0",
  "approved_by": null,
  "status": "draft-pending-review",
  "phrases_en": [
    "are there any exercises", "any exercises i can do", "is there an exercise",
    "give me an exercise", "what exercises", "any techniques i can",
    "is there a technique", "give me a technique", "what can i do about",
    "how do i calm down", "something i can try", "any tools i can use",
    "can you give me something to do", "show me an exercise"
  ],
  "phrases_ar": [
    "هل هناك تمارين", "في تمارين", "اعطني تمرين", "شو اسوي عشان اهدأ", "كيف أهدأ"
  ],
  "bindings": {
    "anxiety/mild": ["box_breathing", "grounding_5_4_3_2_1"]
  }
}
```

(`phrases_ar` ships for the Lane-3 validation packet but is INERT until `SKILL_REQUEST_AR_VALIDATED=true`; per B2 the operative AR gate is session language in Task 5, since AR input reaches the binder as translated English. Moderate binding deliberately absent per M5: §B moderate requires the condensed-screen direct-offer path, out of v1 scope, documented in packet.)

- [ ] **Step 4: Implement loader + flags** following the existing skill_matching data-loading pattern; `SAGE_SKILL_REQUEST_DELIVERY` and `SAGE_SKILL_REQUEST_AR_VALIDATED`, both default False, in `config.py` alongside the other flags (both auto-derived by the parity runner from there).

- [ ] **Step 5: Run tests, expect PASS, then commit** `feat(1a): skill-request lexicon + generic binding table + flags (default OFF)`.

### Task 4: `recent_presentation` channel with screening state (POC stand-in for Active Issues List)

**Files:**
- Create: `src/sage_poc/matching.py` (shared matcher module: node → shared dependency direction, never node → node, so an `intent_route` write-site does not import from `skill_select`)
- Modify: `src/sage_poc/state.py`, `src/sage_poc/nodes/skill_select.py` (writer + Tier-1 refactored onto the shared matcher), `src/sage_poc/nodes/intent_route.py` (writer call-site ONLY if Phase 0 Q3 shows disclosure turns bypass `skill_select`), `scripts/check_state_channels.py` manifest
- Test: `tests/test_graph_skill_request.py`

**Interfaces:**
- Produces:
  - `SageState.recent_presentation: dict | None` with shape `{"category": str, "tier": str, "turn_index": int, "red_flag_screen": "cleared"|"not_run"|"diverted", "chronicity": "acute"|"chronic"|"unknown", "onset_known": bool, "physical_symptoms_mentioned": bool}`.
  - `matching.match_symptom_presentation(message_en, raw_message, lang) -> {"category","tier"} | None` — extracted from the existing Tier-1 pass over `SKILL_REGISTRY.target_presentations`; the ONE symptom-matcher surface (M2). Tier-1 matching refactored to call it (behavior-neutral, covered by existing Tier-1 tests).
- Write-site rule: the writer runs wherever Phase 0 Q3 shows disclosure turns actually execute. All call-sites use the SAME `matching.match_symptom_presentation`; there is no second lexicon regardless of site. Code comment on the channel: `POC stand-in for enriched-state Active Issues List (not implemented, 0 refs in src/); migrate by folding into active_issues when built; cross-session 'cleared' (§1a skip-straight-to-offer on established patterns) also lands there, unreachable in POC by the 4h stale reset.`
- Screening-state derivation (deterministic, no LLM; adaptive per C1):
  - `red_flag_screen`: `"diverted"` if the §1a universal cardiac red-flag descriptors matched this session; `"cleared"` when the session content (disclosure turns AND/OR screen answers) supplies onset/trigger with no red-flag descriptors (C1c: a disclosure like "anxious since my meeting got moved" clears without a screen turn); else `"not_run"`.
  - `onset_known`: true when any session turn supplied an onset/trigger clause (deterministic markers: "since", "after", "because of", "before my", plus the screen answer).
  - `chronicity`: `"chronic"` on deterministic duration markers anywhere in session ("for months", "for weeks", "for years", "always been"); `"acute"` when a duration answer or disclosure marks recency ("today", "this morning", "just now", "this afternoon", screen answer); else `"unknown"`. **`"unknown"` never passes the binder (C1a)** — it routes to the screen asking duration.
  - `physical_symptoms_mentioned`: true when any session turn matched the physical-symptom marker list (heart/breathing/chest rows of the §1a severity tables, transcribed as data with provenance citation in the Task 3 file). Controls whether the red-flag quality clause appears in the screen (C1b).
  - `tier`: from `emotional_intensity` (1-4 mild, 5-7 moderate, 8+ high) BUT clamped upward, never downward, by higher-tier trigger-phrase matches (§1a design rule: conflict → higher tier). `chronic` never maps to bare `mild` handling (B1).
- Clear-points: 4h stale-gap reset (`server_helpers._stale_skill_overrides`) and `_crisis_response_node`, wired exactly where `declined_skills`/`offered_skill_ids` are handled.

- [ ] **Step 1: Write the failing graph test**

```python
# tests/test_graph_skill_request.py
import pytest

@pytest.mark.slow
def test_recent_presentation_written_with_screen_state(graph_session):
    s1 = graph_session.turn("I'm feeling anxious")
    rp = s1["recent_presentation"]
    assert rp["category"] == "anxiety"
    assert rp["red_flag_screen"] == "not_run"  # nothing screened yet
    s2 = graph_session.turn("ok")
    assert s2["recent_presentation"] is not None  # seam: declared, survives turns

@pytest.mark.slow
def test_chronic_marker_prevents_mild_binding_context(graph_session):
    s = graph_session.turn("i've been anxious for months and it's affecting everything")
    rp = s["recent_presentation"]
    assert rp["chronicity"] == "chronic"
```

- [ ] **Step 2: Run to verify failure.** Expected: channel absent.
- [ ] **Step 3: Implement** per the interface block: extract `match_symptom_presentation`, wire writer at the Phase-0-confirmed site(s), declare channel, manifest entry, clear-points.
- [ ] **Step 4: Run graph tests + `check_state_channels.py` + existing Tier-1 tests (refactor must be behavior-neutral), expect PASS. Commit** `feat(1a): recent_presentation channel w/ screening state (Active-Issues POC stand-in), single symptom-matcher surface`.

### Task 5: `zero_candidate_request_binder` (screen-gated, language-gated)

**Files:**
- Modify: `src/sage_poc/nodes/skill_select.py`
- Modify: `prompts/` L2 template set (one addition: `L2_request_screen`, condensed §1a screen question; copy is clinician-reviewed in the packet, em-dash-free)
- Test: `tests/test_skill_request_delivery.py` (extend)

**Interfaces:**
- Consumes: `load_skill_request_data()`, `state["recent_presentation"]`, clinical flags (dissociation/derealization, Task 6/M3), `_resolve_entry()`.
- Produces: path markers `skill_request_detected`, `skill_request_screen_pending`, `skill_request_bound:<category>_<tier>`, `skill_request_referral_context`; on the bound path, candidates handed to `_resolve_entry()` unchanged.

Binder position and conditions (runs AFTER early-returns 1–4 and AFTER Tiers 1/2, zero-candidate fallback only; name reflects this, M4):
1. flag ON; zero candidates from Tiers 1/2
2. **language gate (B2):** if `detected_language == "ar"` and not `SKILL_REQUEST_AR_VALIDATED` → skip entirely (EN lexicon would otherwise match translated AR input)
3. request phrase substring-match (EN vs `message_en`; AR list vs `raw_message` only when AR validated)
4. `recent_presentation` present, category has a binding row, not stale
5. `primary_intent` not in `{crisis, exit_skill, scope_refusal, jailbreak, info_request}`
6. **clinical-flag consult (M3, positive check):** dissociation/derealization flag set → skip binder, freeflow (referral pathway owns it)
7. **adaptive screen dispatch (B1+C1):** compute `missing = []`: onset/trigger not yet known → add onset; `chronicity == "unknown"` → add duration (C1a, mandatory); `physical_symptoms_mentioned` and quality not yet screened → add red-flag quality (C1b, conditional; NEVER included for non-somatic presentations). Then:
   - `missing` empty AND `red_flag_screen == "cleared"` AND `chronicity == "acute"` → bind and offer via `_resolve_entry()`.
   - `missing` non-empty → NO offer; route to freeflow with `L2_request_screen` rendered with ONLY the missing clauses (≤2 clauses, one conversational turn) + marker `skill_request_screen_pending`; the Task 4 writer updates the screening fields from the answer, and the renewed/standing request binds next turn (C1c: nothing already said is re-asked).
   - `chronicity == "chronic"` → referral-alongside-skill: marker `skill_request_referral_context`, offer proceeds WITH the referral instruction layered in the composer prompt (referral copy = existing signed referral surface, not new copy). **PENDING ADJUDICATION (C2):** this implements §1a section-2 routing ("alongside"); §1a section 6 reads "instead of"; the packet presents both and Vee rules. If she rules "instead of", this branch drops the offer and keeps the referral, a one-branch change.
   - `red_flag_screen == "diverted"` → skip; the medical-guard pathway owns the turn (its existence is Phase 0 Q6; if Q6 finds no such pathway, `diverted` is BLOCKED from silent skip and the finding escalates before Task 5 proceeds).

- [ ] **Step 1: Write failing tests**

```python
def _ctx(screen="cleared", chronicity="acute", tier="mild"):
    return {"category": "anxiety", "tier": tier, "turn_index": 1,
            "red_flag_screen": screen, "chronicity": chronicity}

def test_cleared_context_offers_tier1_choice(skill_select_harness):
    out = skill_select_harness.run(skill_select_harness.state(
        message_en="i was wondering, are there any exercises i can do before bed",
        primary_intent="new_skill", recent_presentation=_ctx(),
        flags={"SKILL_REQUEST_DELIVERY": True}))
    assert "skill_request_detected" in out["path"]
    assert set(out["offered_skill_ids"]) == {"box_breathing", "grounding_5_4_3_2_1"}
    assert out["active_skill_id"] is None

def test_unscreened_context_gets_screen_not_offer(skill_select_harness):
    out = skill_select_harness.run(skill_select_harness.state(
        message_en="i was wondering, are there any exercises i can do before bed",
        primary_intent="new_skill", recent_presentation=_ctx(screen="not_run"),
        flags={"SKILL_REQUEST_DELIVERY": True}))
    assert "skill_request_screen_pending" in out["path"]
    assert not out.get("offered_skill_ids")

def test_chronic_context_offers_with_referral_marker(skill_select_harness):
    out = skill_select_harness.run(skill_select_harness.state(
        message_en="i was wondering, are there any exercises i can do before bed",
        primary_intent="new_skill", recent_presentation=_ctx(chronicity="chronic"),
        flags={"SKILL_REQUEST_DELIVERY": True}))
    assert "skill_request_referral_context" in out["path"]

def test_arabic_session_skips_binder_via_translated_english(skill_select_harness):
    # B2: AR input arrives as translated message_en and WOULD match the EN lexicon
    out = skill_select_harness.run(skill_select_harness.state(
        message_en="are there any exercises i can do",
        raw_message="هل هناك تمارين أقدر أسويها",
        detected_language="ar",
        primary_intent="new_skill", recent_presentation=_ctx(),
        flags={"SKILL_REQUEST_DELIVERY": True, "SKILL_REQUEST_AR_VALIDATED": False}))
    assert "skill_request_detected" not in out["path"]
    assert not out.get("offered_skill_ids")

def test_flag_off_is_inert(skill_select_harness):
    out = skill_select_harness.run(skill_select_harness.state(
        message_en="are there any exercises i can do",
        primary_intent="new_skill", recent_presentation=_ctx(),
        flags={"SKILL_REQUEST_DELIVERY": False}))
    assert "skill_request_detected" not in out["path"]

def test_request_without_context_falls_through(skill_select_harness):
    out = skill_select_harness.run(skill_select_harness.state(
        message_en="are there any exercises i can do",
        primary_intent="new_skill", recent_presentation=None,
        flags={"SKILL_REQUEST_DELIVERY": True}))
    assert out.get("offered_skill_ids") in (None, [])
```

- [ ] **Step 2: Run to verify failure.**
- [ ] **Step 3a: Implement the binder** per the condition list, handing bound candidates to `_resolve_entry()` exactly as Tier-1 candidates (declined-filtering, `max_offered`, markers all inherited).
- [ ] **Step 3b: Add `L2_request_screen`** to the L2 template set as a CLAUSE-TEMPLATED turn (GATED on the C1/C2 packet review): onset and duration are the unconditional clause pair (§1a Mild core questions; duration is the "more than mild" discriminator); the red-flag quality clause renders ONLY when `physical_symptoms_mentioned` is true (C1b, and the copy must not introduce cardiac descriptors to a non-somatic presentation). Renderer receives the `missing` list from condition 7 and includes only those clauses, max 2 per turn, conversational register. Bilingual envelope like `L2_skill_offer`, `ar: null` fallback, status `draft-pending-review`. The Task 4 writer updates `red_flag_screen`/`chronicity`/`onset_known` from the answer; a red-flag answer sets `"diverted"`.
- [ ] **Step 4: Run tests, expect PASS. Commit** `feat(1a): zero_candidate_request_binder, screen-gated + language-gated, behind SAGE_SKILL_REQUEST_DELIVERY`.

### Task 6: Both-direction + coverage guard fixtures

**Files:**
- Test: `tests/test_skill_request_delivery.py`, `tests/test_graph_skill_request.py` (extend)

- [ ] **Step 1: Write the hold-the-line and coverage tests**

All guards assert the POSITIVE alternative path fired (C3): silence is indistinguishable from the presence_only gap and never passes.

```python
def test_ocd_compulsion_request_vetoed_with_veto_path(graph_session):
    # PR#155 Node-4 iatrogenic veto: assert the veto FIRED, not merely that no offer appeared
    graph_session.turn("i keep having horrible intrusive thoughts and checking things over and over")
    out = graph_session.turn("is there an exercise to make the thoughts go away")
    assert "iatrogenic_veto" in out["path"]
    assert not out.get("offered_skill_ids")

def test_bare_emotional_word_still_gated(graph_session):
    out = graph_session.turn("anxious")
    assert not out.get("offered_skill_ids")
    assert "skill_request_detected" not in out["path"]  # binder did not fire on a non-request

def test_1f_curiosity_still_routes_to_psychoed(graph_session):
    # positive path: psychoed consult surface fired (Mechanism-A / psychoed path marker per PR#362)
    graph_session.turn("I'm feeling anxious")
    out = graph_session.turn("why does my body react like this?")
    assert "skill_request_detected" not in out["path"]
    assert any("psychoed" in m or "info_request_consult" in m for m in out["path"])

def test_dissociation_flag_routes_to_hr_referral(graph_session):
    # M3+C3: flag persists across a clean turn AND the HR-1 referral pathway fires.
    # Exact marker: the HR-1 Stage-1 detect-to-refer path marker (grep SAGE_HIGH_RISK_DETECTION
    # markers in the hr detection implementation; live since 2026-07-17).
    graph_session.turn("everything feels unreal, like i'm not in my body")
    graph_session.turn("anyway, work was fine today")   # later clean turn must NOT reset the guard
    out = graph_session.turn("are there any exercises i can do")
    assert "skill_request_bound:anxiety_mild" not in out["path"]
    assert any(m.startswith("hr_referral") or "high_risk" in m for m in out["path"])

def test_declined_skill_not_reoffered_by_binder(graph_session):
    graph_session.turn("I'm feeling anxious")
    graph_session.turn("i was wondering, are there any exercises i can do")
    graph_session.turn("no thanks, not the breathing one")
    out = graph_session.turn("ok fine, any exercises i can do though")
    assert "box_breathing" not in (out.get("offered_skill_ids") or [])
    assert out.get("offered_skill_ids")  # positive: the non-declined alternative IS offered

def test_crisis_language_in_request_turn_preempts_binder(graph_session):
    graph_session.turn("I'm feeling anxious")
    out = graph_session.turn("are there any exercises, honestly i just want it all to end")
    assert "crisis_response" in out["path"]   # positive: crisis pathway fired
    assert not out.get("offered_skill_ids")

def test_high_intensity_request_enters_acute_machinery(graph_session):
    # step-up coverage (C3): §1a High requires immediate acute skill; assert acute FIRED
    graph_session.turn("my heart is pounding out of my chest, i can't take this anymore")
    out = graph_session.turn("give me something to do right now")
    assert "skill_request_bound:anxiety_mild" not in out["path"]
    assert any(m == "skill_matching_rule:acute_direct_entry" for m in out["path"]) \
        or out.get("active_skill_id") in {"dbt_tipp", "box_breathing", "grounding_5_4_3_2_1", "stop_technique"}

def test_cardiac_red_flag_routes_to_medical_guard(graph_session):
    # diverted branch (C3): the medical-guard pathway must FIRE, never a silent skip.
    # Exact marker per Phase 0 Q6 findings; if Q6 found no such pathway, this test is the
    # blocking evidence and Task 5 does not proceed.
    graph_session.turn("I'm feeling anxious")
    out = graph_session.turn("my chest has this crushing pain spreading to my arm, any exercises?")
    assert "skill_request_bound:anxiety_mild" not in out["path"]
    assert any("medical" in m or "red_flag" in m for m in out["path"])

@pytest.mark.slow
def test_binder_markers_reach_audit_record(graph_session, audit_reader):
    graph_session.turn("I'm feeling anxious")
    graph_session.turn("i was wondering, are there any exercises i can do")  # screen turn
    graph_session.turn("it started this afternoon before a meeting, no chest pain or anything")  # clears
    out = graph_session.turn("so, any exercises i can do")
    row = audit_reader.latest()
    assert any(m.startswith("skill_request_bound:") for m in row["path"])
    assert row["flags"]["SKILL_REQUEST_DELIVERY"] is True
    assert set(row["offered_skill_ids"]) == {"box_breathing", "grounding_5_4_3_2_1"}  # skill ids in audit
    assert row["model_version"]  # model version present (checklist: model, skill, flags in audit row)
```

Known residual risk to record in the memo AND packet: the dissociation test depends on Clinical Flags recall, which is keyword-only (Gap #65); a naturalistic derealization phrasing the CF lexicon misses leaves the binder unguarded on that turn. If the fixture phrasing above does not set the flag, that is a FINDING against CF coverage routed to the Gap #65 workstream (CF lexicon additions need clinical sign-off), not something to patch with a binder-local keyword list (which would violate the single-surface constraint and the positive-guard rule).

- [ ] **Step 2: Run; iterate the binder until all pass without weakening Task 5 tests.**
- [ ] **Step 3: Commit** `test(1a): both-direction + crisis/acute/audit coverage guards`.

---

## Phase 2 — Measurement, governance, ship

### Task 7: Naturalistic fixture set (lexicon-independent)

**Files:**
- Create: `tests/fixtures/conformance/1a_skill_request_naturalistic.json`

- [ ] **Step 1: Author 15 EN naturalistic request phrasings** from the matrix v5 §1a presence_only run transcripts + paraphrase families (provenance line per case; observed transcript = case 000). Include 5 AR cases (marked `blocked_on: AR validation`, executed only under `SKILL_REQUEST_AR_VALIDATED=true` in staging).
- [ ] **Step 2: Anti-tautology CI check**

```python
def test_fixtures_do_not_mirror_lexicon():
    import json, pathlib
    lex = json.loads(pathlib.Path("rules/data/skill_matching/skill_request_phrases.json").read_text())
    fixtures = json.loads(pathlib.Path("tests/fixtures/conformance/1a_skill_request_naturalistic.json").read_text())
    lex_set = {p.lower() for p in lex["phrases_en"] + lex["phrases_ar"]}
    for case in fixtures["cases"]:
        assert case["message"].lower() not in lex_set, f"tautological fixture: {case['case_id']}"
```

- [ ] **Step 3: Run full-graph, flag ON, record hit-rate.** Misses are findings (lexicon recall), reported per case; every lexicon addition motivated by a miss gets its own commit referencing the case.
- [ ] **Step 4: Commit** `test(1a): naturalistic fixture set (EN+AR) + anti-tautology check`.

### Task 8: Conformance re-run + sign-off packet

- [ ] **Step 1: Matrix §1a re-run** via the parity-enforcing runner only, staging first with `SAGE_SKILL_REQUEST_DELIVERY=true`. Record §1a movement (baseline 2/5) and conformance-neutrality on every other row (v5 discipline).
- [ ] **Step 2: Assemble packet** at `docs/superpowers/governance/2026-07-28-1a-skill-request-signoff.md`:
  - mechanism memo incl. Tier-2 functionality verdict (Q5) and its RT-4/S-4 implication
  - lexicon + binding table (EN ask; AR pending-validation ask, Lane-3, Khaleeji register)
  - `L2_request_screen` clause-templated copy for clinical review: onset+duration unconditional pair, red-flag quality clause conditional on `physical_symptoms_mentioned` (C1a/C1b), adaptive don't-re-ask behavior (C1c)
  - screening-state model (B1+C1) and its §1a mapping (adaptive missing-clause dispatch; `unknown` chronicity never passes)
  - **OPEN SPEC QUESTION for adjudication (C2):** §1a chronic case, section 6 ("referral instead of self-guided tools") vs section 2 routing logic ("skill alongside referral when the user wants one"); both readings presented with spec line cites; implementation currently takes "alongside", isolated to one branch; Vee rules
  - guard results (all Task 6), CF-recall residual risk (Gap #65 tie)
  - matrix delta + neutrality table; latency budget statement
  - **documented deviations:** moderate tier NOT bound (condensed direct-offer path unimplemented, §B), consent-gate offer shape used for mild (rides existing R1 governance), `recent_presentation` as Active-Issues POC stand-in with migration path
  - generalization path: new categories = binding-table rows + signed offer-table sourcing, never new binders
  - rollback statement (flag off, single env var)
- [ ] **Step 3: BLOCKED-BY-DESIGN:** flag stays OFF in prod until the packet is signed. Green pipeline proves flow, not correctness.
- [ ] **Step 4: Ship (post-sign-off):** PR per branch convention, rebase-before-merge, CI hard gate, `deploy_prod.sh` with `SAGE_BUILD_SHA` pin + `/health/version` verify + ancestry check; flip flag; re-run Task 7 EN set against prod serving config via the parity runner.

---

## Self-Review (v2, performed at write time)

- **Review coverage:** B1 → screening-state model (Task 4 derivation + Task 5 condition 7 + tier clamp); B2 → language gate (Task 5 condition 2) + Arabic-input test; B3 → Task 2 branch (c) with SPOF hard gate. M1 → stand-in declaration + migration path (Task 4 + packet); M2 → `match_symptom_presentation` single surface, write-site bound to Phase 0 Q3 evidence (amended from review's fixed site: routing graph shows `general_chat` turns can bypass `skill_select`, so a skill_select-only writer would starve on the observed transcript, recorded as pushback); M3 → clinical-flag positive consult + persistence test + Gap #65 residual named; M4 → renamed; M5 → moderate dropped from bindings, deviation documented. Checklist gaps → crisis, AR, audit-trail, acute-precedence fixtures (Task 6), latency budget (constraints + packet), step-up handling (high → acute machinery, tested). Systemic → Q5 Tier-2 verdict mandatory in memo; generic binding schema + generalization path in packet.
- **Placeholder scan:** none. The two copy artifacts pending clinical review (`L2_request_screen`, referral layering) reuse existing signed surfaces or are packet-gated drafts, both named.
- **Type consistency:** `load_skill_request_data()`, `match_symptom_presentation()`, `recent_presentation` shape (5 fields), markers `skill_request_detected` / `skill_request_screen_pending` / `skill_request_bound:<category>_<tier>` / `skill_request_referral_context` consistent across Tasks 3–8.
- **Known tension:** Phase 0 may land on branch (c), making Tasks 3–6 contingent. That is the gate working as designed; do not pre-build the binder while the memo is unwritten.
