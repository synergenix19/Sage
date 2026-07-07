# info_request Turn-Aware — CLOSURE (prod-verified) — 2026-07-07

**Status: CLOSED.** The engagement chain that began with a screenshot of a dry, list-shaped dead-end on "what is anxiety" is behaviorally fixed and verified in production.

## Ship record (source-linked custody)
- PR **#153** merged → master `6082273`.
- Deployed via `railway up` from the verified latest master; build **`a6277ed2`** reached SUCCESS and was confirmed the **newest/active** deployment with the freeze held throughout (gap-class-5 guard — no stale parallel deploy won the race).

## Behavioral closure evidence — prod smoke transcript
Two turns, **same session** (so `prev_primary_intent` carries via the checkpoint), against prod build `a6277ed2`:

**Turn 1 — fresh `what is anxiety`**
- `X-Sage-Intent: info_request`; node-path contained **no `directive_posture_set` and no `question_discipline_applied`** — the D4 amendment holding (directive_posture no longer fires on info_request, so nothing strips the close).
- Closed with the **surviving triage question**:
  > "Are you asking about anxiety for yourself or just curious in general?"

**Turn 2 — same session, consecutive `what are the symptoms of anxiety`**
- `prev_primary_intent == info_request` → composer selected `L2_info_request_repeat` → **statement fallback, zero questions**:
  > "…If you want to know more, I'm here for you."

Both behaviors live, through the real output_gate — the seam that amputated v2.0.0. This is the third time in the chain the isolated-vs-live distinction was load-bearing; the full-graph eval + prod smoke are now the standard for conversational-behavior changes.

## Non-blocking follow-ups (tracked, not part of closure)
1. **Falcon-34B re-run** must cover the three turn-aware scenarios (this ran on GPT-4o; generation-shape adherence is model-specific — the standing transfer caveat).
2. **Directive-posture audit ticket** (`2026-07-07-directive-posture-infofire-audit.md`) — low priority, now largely resolved by the amendment (info_request no longer sets the flag).
3. **#125** overflow/L1-budget test still red (pre-existing, unrelated).

## Governance trail
D4 amendment recorded against LOCK-QDISC-22 (`2026-07-07-info_request-d4-amendment-turn-aware.md`); full-graph eval results (`2026-07-07-info_request-turnaware-fullgraph-eval-results.md`); signer Rohan Sarda (clinical lead) confirmed verbatim; register attribution correction appended (`2026-07-07-l2-engagement-signoff-register.md`).
