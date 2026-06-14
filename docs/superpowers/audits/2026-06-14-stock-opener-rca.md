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

## Residuals / follow-ups

- The "X can be very painful" reflective-sympathy form (screenshot 1) is **not** blocklisted
  (too high a false-positive risk for a generic regex). The PRIMARY L2 rewrite targets this class;
  confirm via post-deploy prod probe.
- `_VETTED_FALLBACK_RESPONSE` is itself a generic opener (boundary #10). Left unchanged here to keep
  the fix minimal; flagged for a separate decision.
- Behavioral proof is the live prod re-probe after deploy (Railway is manual `railway up`, no
  auto-deploy), with the exact screenshot phrases.
