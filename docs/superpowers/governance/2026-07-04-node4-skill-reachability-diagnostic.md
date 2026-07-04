# Diagnostic — Node 4 (skill_select) reachability for naturally-phrased messages

**Filed:** 2026-07-04 (surfaced by W4 prod verification — `mood_check_in` never entered on prod). **Type:** architecture-conformance (v7 §4.2 pattern 2). **Owner:** _routing workstream (assign)_. **NOT W4/W2 scope.**

## What W4 surfaced
The W4 anchor guard is E2E-proven but could not be confirmed on prod: every AR mood-rating probe — including exact `target_presentations` triggers ("كيف مزاجي اليوم؟") and a 2-turn accept flow — routed `intent_route → freeflow_respond`. `node_path` never contained `skill_select`; `active_skill_id` empty. So `score_mood` never executed and the guard (correctly) no-opped.

## The two-reading question, resolved with evidence
**(a) intent_route misclassifies vs (b) the graph edge skips skill_select** — resolved to **(a), scoped narrowly:**

- **NOT (b).** `graph._route_after_intent` DOES route `new_skill`/`info_request`/acute-general_chat/offer-accept/monitoring/psychotic → `skill_select` (graph.py:214-230). The edge exists.
- **NOT a wholesale Node-4 bypass.** Prod `session_audit` (2289 turns): **942 (~41%) reached `skill_select`; 547 ran an active skill.** The trigger inventory IS consulted in production regularly. The earlier "trigger layer unreachable" hypothesis is **not supported** — skills route and run.
- **It IS (a), for mood-check phrasings specifically.** `intent_route`'s classifier labelled "كيف مزاجي اليوم؟" as `general_chat` (normal intensity) → freeflow, so the mood trigger never reached Node 4's keyword match.

## The real conformance nuance (worth an owner's eye, not alarm)
Node 4's deterministic 600+ trigger inventory only runs *after* the LLM classifier emits a skill intent (`new_skill`/`info_request`/acute/offer/monitoring). So v7 §4.2 pattern 2 ("user says 'I can't sleep' → skill_select matches a trigger → skill injected") depends on the classifier pre-labelling that message a skill intent. The deterministic layer is subordinated to the probabilistic one. This works broadly (41% reach), but naturally-phrased messages the classifier reads as `general_chat` never consult the trigger inventory. **Decision for the owner:** is that the intended design (accepted POC simplification) or a §4.2 deviation? If the latter, options are classifier prompt/calibration (Falcon-3B) or a pre-classifier keyword pre-pass.

## Mood instrument — separate scoped item (do not let the routing diagnostic absorb it)
v7 frames mood check-in as **optional per-session, PROM-like** → proactive offering (session-start/end skill loading), NOT user-initiated entry. So even under reading (a), the complete fix for mood under-administration includes the **proactive-offer mechanism** — its own scoped item, independent of the classifier question.

## Cheap next diagnostic (deferred)
Sample prod `node_path` + the classified intent for a set of known KB-trigger phrases ("I can't sleep", "I keep worrying") to measure how often natural pattern-2 phrasings reach `skill_select` vs freeflow — quantifies the calibration gap before deciding (a)-calibration vs §4.2-deviation.

## CORRECTION (2026-07-04) — mood fix is NOT trigger patterns
Follow-up measurement overturns gap #1's framing. Running `skill_select_node` locally on "how are you
tracking my mood today" returns **`offered:['mood_check_in'], keyword_offer`** — the triggers ALREADY
match; `active_skill_id` is None only because it is an R1 OFFER pending accept (correct). So `score_mood`
is reachable on EN via trigger → offer → **accept** → skill enters → score_mood. My single-turn probes
stopped at the offer. On prod the same phrase behaved INCONSISTENTLY across runs (reached skill_select
in one battery; no offer in the accept-flow run) — the signature of `intent_route` LLM-classifier
non-determinism, not a missing keyword. **Therefore: adding trigger phrasings is the WRONG fix** (they
already match). The real mood item is (i) `intent_route` classification consistency for skill/mood
phrasings [EN variance + AR not-classified-new_skill], and (ii) the offer→accept flow — both belong in
the **W6 measured pass** (multi-sample per phrase for the LLM variance), NOT a Node-4 trigger-pattern
checkbox. No clinician trigger-pattern approval is warranted.
