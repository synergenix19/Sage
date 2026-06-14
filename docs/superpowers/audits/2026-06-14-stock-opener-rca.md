# RCA: Stock sympathy/paraphrase openers persist in general_chat

> **Date:** 2026-06-14
> **Branch:** `fix/opener-layer-conflict`
> **Trigger:** Comparison vs ChatGPT showed Sage opening every distress turn with a stock
> sympathy/paraphrase line ("I'm sorry to hear you're not feeling good", "Feeling worthless
> can be very painful"), despite three L0 persona rewrites the same day that prohibit exactly this.
> **Status:** Fix drafted + tested. L2 content (v1.5.0) clinical sign-off recorded 2026-06-14 (per product owner). Deployment is staged: blocklist is deterministically verifiable pre-serve; L2 is live-unverified until a gated post-deploy re-probe.

---

## Verdict

It is **not** a wiring bug, and **not** merely a missing blocklist entry. The root cause is a
**direct contradiction between two prompt layers**, with an incomplete deterministic backstop as a
secondary contributor. Tuning L0 (done 3x on 2026-06-14) could never fix it because L0 was the
layer being overridden.

---

## Phase 1 — Evidence (boundary by boundary)

| # | Boundary | Finding |
|---|----------|---------|
| 1 | Prod vs code | Live deploy `632f55bb` created 14:42:18 (+04), 13s after merge `d15aad1` (L0 v2.2.0). App tree clean. **Prod = HEAD, not stale.** |
| 2 | Symptom on live prod | `POST /chat` "I'm not feeling too good today." returned *"I'm sorry to hear you're not feeling too good today. Would you like to talk about what's been going on?"* `intent=general_chat`, `crisis-flags=[]`, `intensity=5`, `gate-path=standard`. Reproduced, not a stale screenshot. |
| 3 | Regex correctness | `_BANNED_OPENER_RE` (isolated) catches all 9 listed families; does **not** match "I'm sorry to hear" or "Feeling worthless can be very painful" — not in the list. Works as written. |
| 4 | `output_gate` on this path | `graph.py`: `intent_route → freeflow_respond → output_gate → END`; retry loops back. Wired. |
| 5 | Field match | Gate reads `state["response_en"]` (`output_gate.py:220`); freeflow writes `"response_en"` (`freeflow_respond.py:166`). Same field, no silent no-op. |
| 6 | Intent gating | Check at `output_gate.py:307` runs on `gate_path="standard"`; general_chat not excluded. |
| 7 | Does model see OPENERS rule | `composer.py:501` puts `_build_l0_system_block()` first. L0 OPENERS is in the freeflow system prompt. |
| 8 | Retry correction injected | `composer.py:829` appends `[CORRECTION]` to the user prompt. Retry is not blind. |
| 9 | **The conflict** | L0 OPENERS: *"Warmth comes from substance, not from … a paraphrase of what they just told you."* L2 general_chat v1.4.0: *"reflect the feeling back before anything else."* Reflecting the feeling back **is** paraphrasing what they told you. Layers command opposite openers; the turn-level L2 directive wins. |
| 10 | Failure-of-the-failure | Even when a banned opener IS caught and the retry still trips, the gate substitutes `_VETTED_FALLBACK_RESPONSE` = *"I'm here with you. What would feel most helpful to share right now?"* — itself a generic opener. The gate guarantees "not these N phrases", not "substantive". |

Local pytest could not run (`sentence_transformers` absent; blocked by an `autouse session` fixture in `conftest.py`). Wiring proven by reading every boundary + isolated regex test + live prod probe.

## Root cause

- **PRIMARY:** prompt-layer instruction conflict. The responder faithfully executes L2 general_chat's
  explicit, turn-scoped *"reflect the feeling back before anything else"*, which renders as the stock
  sympathy/paraphrase opener L0's OPENERS rule forbids. Turn-level intent beats base persona.
- **SECONDARY:** `_BANNED_OPENER_PATTERNS` omitted the "I'm sorry to hear" sympathy family, so the
  backstop that should have caught the leak did not fire.
- **ARCHITECTURAL (noted, not fixed here):** a start-of-string phrase blocklist cannot enforce
  "substance-first"; it lags the model's defaults and its own fallback is a generic opener.

## Phase 4 — Fix (drafted on `fix/opener-layer-conflict`)

1. **PRIMARY** — `L2_intents/general_chat.json` v1.4.0 → **v1.5.0** (status `draft_pending_review`):
   opener directive changed from *"reflect the feeling back before anything else"* to
   *"Open by naming the specific thing the person raised. Validate before you inform, not by repeating
   their words back or opening with a stock sympathy line."* `validate-before-inform` invariant
   preserved. `word_budget` 190 → 200 to fit (content 199 words). Verified by composer trace that L2
   content is appended verbatim (`_build_l2_intent_block`); only L1 history is budget-truncated, so the
   validation clause cannot be clipped. Clinical sign-off recorded 2026-06-14.
2. **SECONDARY** — `output_gate.py` `_BANNED_OPENER_PATTERNS`: added the sympathy family
   (`i'm sorry to hear`, `i'm sorry you`, `i'm sorry that`, `i'm so sorry`, `sorry to hear`),
   anchored at `^` so mid-reply apologies are unaffected.

Tests: `tests/test_opener_layer_conflict.py` (content contract + regex backstop + over-match guards).
Verified red→green in isolation against the real source.

## Post-deploy re-probe (2026-06-14)

Merged to master via PR #27 (merge commit `8dc42ba`, both commits preserved; admin-merge bypass of
the REVIEW_REQUIRED gate, logged with green CI run `27500319703`). Deployed from master with
`railway up` (deployment `fdf39a43`, SUCCESS). Re-probed live prod:

| Probe | Result | node-path | Read |
|---|---|---|---|
| "I'm not feeling too good today." | "You're not feeling too good today. What's been going on that might be affecting how you feel?" | `… output_gate → output_gate_banned_opener_retry → freeflow_respond → output_gate` | **PASS.** Model still generated "I'm sorry to hear…" first; the **blocklist caught it** and the retry produced a direct-naming opener. Before fix this exact phrase returned "I'm sorry to hear you're not feeling too good today." |
| "I am not feeling too good today." | "I'm here with you. What would feel most helpful to share right now?" | `… banned_opener_retry → … → output_gate_fallback_substituted` | Net held. Generator produced a banned opener **twice**; gate substituted the vetted fallback. Safe but generic → follow-up #29. |
| "I feel completely worthless lately." | "Feeling worthless can be incredibly hard. What has been contributing to these feelings for you lately?" | `safety_check → intent_route → freeflow_respond → output_gate` | Paraphrase opener persists. Not blocklisted (FP risk); L2 v1.5.0 **inert** here, not harmful. Validation intact, no advice-first → follow-up #28. |

### Verdict
- **`b6d41c9` (blocklist): VERIFIED LIVE.** The retry node firing on probe 1 and replacing
  "I'm sorry to hear…" is direct proof it earns its place.
- **`41ed043` (L2 v1.5.0): shipped, contract-locked by tests, NO observed live effect yet, NO observed
  harm.** Not "verified" — inert on the one probe that could have exercised it. The net holds because
  the deterministic backstop is strong, not (yet) because the prompt layer changed the model's instinct.
  Prompt-layer real-world efficacy remains an **open question**.

### Rollback-trigger correction (do not read as "fail ignored")
The pre-agreed sub-condition (a) ("paraphrase opener present → revert `41ed043`") **fired** on probe 3,
but was **retired as over-broad**, not waived. (a) was a looser draft of the top-level trigger
("validate-before-inform weakened OR advice-first creeping in"), which is the correct, regression-scoped
rule and did **not** fire on any probe. Probe 3's paraphrase is a **pre-existing residual neither commit
caused** and the blocklist deliberately does not catch. Reverting `41ed043` would restore v1.4.0's
literal *"reflect the feeling back before anything else"* — i.e. re-introduce more of exactly the
behavior (a) was written to catch. Honoring (a) would optimize the proxy against the goal it stands for.
**Decision: keep both.** Trigger set corrected; condition (a) removed in favor of the regression-scoped trigger.

## Open follow-ups
- **#28** — pure-feeling paraphrase opener ("thing == feeling" collision). Needs a clinical-content
  design decision (what is a good opener when the feeling is the whole message?), not a regex.
- **#29** — generic vetted-fallback regresses openers to the mean on the double-banned path
  (boundary #10). Track the frequency of the double-banned → fallback path; it is a direct proxy for
  how often the prompt layer fails to internalize substance-first.
