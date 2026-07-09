# Diagnostic — Node 4 (skill_select) reachability for naturally-phrased messages

**Filed:** 2026-07-04 (surfaced by W4 prod verification — `mood_check_in` never entered on prod). **Type:** architecture-conformance (v7 §4.2 pattern 2). **Owner:** _routing workstream (assign)_. **NOT W4/W2 scope.**

## What W4 surfaced
The W4 anchor guard is E2E-proven but could not be confirmed on prod: every AR mood-rating probe — including exact `target_presentations` triggers ("كيف مزاجي اليوم؟") and a 2-turn accept flow — routed `intent_route → freeflow_respond`. `node_path` never contained `skill_select`; `active_skill_id` empty. So `score_mood` never executed and the guard (correctly) no-opped.

## The two-reading question, resolved with evidence
**(a) intent_route misclassifies vs (b) the graph edge skips skill_select** — resolved to **(a), scoped narrowly:**

- **NOT (b).** `graph._route_after_intent` DOES route `new_skill`/`info_request`/acute-general_chat/offer-accept/monitoring/psychotic → `skill_select` (graph.py:214-230). The edge exists.
- **NOT a wholesale Node-4 bypass.** Prod `session_audit` (2289 turns): **942 (~41%) reached `skill_select`; 547 ran an active skill.** The trigger inventory IS consulted in production regularly. The earlier "trigger layer unreachable" hypothesis is **not supported** — skills route and run.
- **It IS (a), for mood-check phrasings specifically.** `intent_route`'s classifier labelled "كيف مزاجي اليوم؟" as `general_chat` (normal intensity) → freeflow, so the mood trigger never reached Node 4's keyword match.

## The conformance nuance — narrower than first framed (see MEASURED below)
Node 4's deterministic trigger inventory runs *after* the LLM classifier emits a skill intent, so it structurally depends on `intent_route` pre-labelling the message a skill intent. **The initial hypothesis was that this broadly starves the trigger layer — the measured battery (below) does NOT support that:** 6/7 canonical triggers reached `skill_select` and 5/7 correctly surfaced the expected skill. The classifier routes clear triggers to Node 4 reliably. What remains is **per-skill trigger precision** (mood_check_in) + occasional borderline classification (behavioral_activation) — calibration, not architecture. **Owner decision** is therefore narrower: fix the two specific gaps as rule-data (Cardinal Rule 4), and separately decide whether the general_chat→freeflow default for genuinely-ambiguous messages is an accepted POC simplification.

## Mood instrument — separate scoped item (do not let the routing diagnostic absorb it)
v7 frames mood check-in as **optional per-session, PROM-like** → proactive offering (session-start/end skill loading), NOT user-initiated entry. So even under reading (a), the complete fix for mood under-administration includes the **proactive-offer mechanism** — its own scoped item, independent of the classifier question.

## Cheap next diagnostic (deferred)
Sample prod `node_path` + the classified intent for a set of known KB-trigger phrases ("I can't sleep", "I keep worrying") to measure how often natural pattern-2 phrasings reach `skill_select` vs freeflow — quantifies the calibration gap before deciding (a)-calibration vs §4.2-deviation.

## MEASURED (2026-07-04) — battery of 7 canonical KB-trigger phrases → prod
| Trigger (expected) | reached skill_select | outcome |
|---|---|---|
| grounding_5_4_3_2_1 | yes | matched + ENTERED ✅ |
| dbt_tipp | yes | matched + ENTERED ✅ |
| worry_time | yes | matched + OFFERED (keyword_offer, pending accept — correct R1) ✅ |
| box_breathing | yes | matched + OFFERED ✅ |
| problem_solving_therapy | yes | matched + OFFERED ✅ |
| behavioral_activation | **NO** | intent_route → freeflow (reachability miss) |
| mood_check_in (EN "how are you tracking my mood today") | yes | **skill_match_method=none** (no keyword match) |
| mood_check_in (AR "كيف مزاجي اليوم؟") | **NO** | freeflow |

**Headline: 5/7 canonical triggers correctly surface the expected skill** (direct entry or R1 offer). The trigger layer is **broadly healthy** — the earlier "trigger layer subordinated / mood unreachable" framing is **NOT supported by the data**; corrected here. Two narrow gaps remain, both rule-data/calibration (Cardinal Rule 4), NOT architecture:
1. **`mood_check_in` trigger precision** — its `target_presentations` don't match natural mood phrasings ("how are you tracking my mood today" → no match; AR phrasing → not even a skill intent). This is why W4's `score_mood` is unreachable. Fix = add natural EN+AR mood phrasings to `mood_check_in` triggers (clinician-owned trigger patterns). Lands together with W4's prod confirmation + the G5-b signature.
2. **`behavioral_activation` classification miss** — "i have no motivation" classified general_chat → freeflow (1/7). Borderline intent_route case; measure across more phrasings before tuning.

**Implication for W6:** the W6 anecdotes (relationship→money-worry mismatch, TIPP-not-executed, mood-for-infidelity) are **skill_select MATCH-PRECISION + offer/execute** issues on a broadly-working layer — a **measured precision-tuning pass**, NOT a reachability rebuild. Reading (a) confirmed but NARROW (per-skill trigger precision), not the broad classifier-subordination hypothesis.
