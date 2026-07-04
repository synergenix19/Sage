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

## W6 MEASURED PASS (2026-07-04) — non-determinism DISSOLVED; deterministic misclassification is the real gap
**Temp-0 check:** `intent_route` classifier is ALREADY `temperature=0` (`_LLM_CONFIGS["classifier"]`). No decoding fix to grab.

**Consistency battery (N=5/phrase, local, `scripts/w6_routing_diagnostic.py consistency`):** ALL phrases STABLE (5/5 identical). **The "LLM non-determinism" hypothesis is DISPROVEN** — the classifier is deterministic; my earlier prod "inconsistency" was pipeline/session-state confounds in the probes, not classifier variance. Corrects the CORRECTION above.

**The real gaps are DETERMINISTIC misclassifications (intent_route / Node 2):**
| Phrase | Classified (5/5) | Routes to | Should |
|---|---|---|---|
| "how are you tracking my mood today" (EN mood) | `info_request` | skill_select→**knowledge_retrieve** (info path) — mood offered but turn answers as info; score_mood never enters | `new_skill` |
| "كيف مزاجي اليوم؟" (AR mood) | `general_chat` | freeflow | reach skill_select |
| "i have no motivation to do anything" (BA) | `general_chat` | freeflow | `new_skill` (STABLE miss, not the 1/7 noise first assumed) |

**Precision battery (intent_route→skill_select, local):** canonicals solid — overwhelm→dbt_tipp ✅, panic→grounding ✅, worry→worry_time ✅. Two anecdote "misses", both DEBATABLE: "relationship falling apart + worrying about money" → `financial_anxiety` (semantic_offer) over worry_time (genuine ambiguity — money IS mentioned); "partner cheated" → no skill (infidelity→mood_check_in is a questionable expectation; freeflow support may be correct — needs clinician view).

## Ranked fixes (measured)
1. **intent_route misclassifies skill-worthy phrasings** (EN mood→info_request; AR mood + BA→general_chat) — deterministic, reproducible. **This is now the evidence for the Cardinal-Rule-5 deterministic keyword PRE-PASS** (skill triggers matched BEFORE the LLM classifier can label them general_chat/info_request) — rules-before-LLM, audit-friendly, deterministic. Alternative: classifier prompt calibration. **ARCHITECTURE DECISION for the owner** (the keyword-pre-pass option, parked earlier as "reading (b) unsupported", is now evidence-backed — not as a graph-edge change but as a pre-classifier rules tier).
2. **semantic precision** (relationship+money → financial_anxiety vs worry_time) — reranker/anchor tuning; debatable; lower priority; eng-side.
3. **infidelity → mood_check_in expectation** — likely NOT a bug (freeflow support reasonable); one-line clinician view on whether infidelity should trigger a mood check-in.

**No trigger-pattern rule-data changes warranted** (triggers already match once skill_select is reached — see CORRECTION). The fix lives at Node 2 (classification / pre-pass), not Node 4 (triggers).
