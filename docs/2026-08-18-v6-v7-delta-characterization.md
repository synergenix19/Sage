# v6→v7 delta characterization — the two hypotheses are one mechanism (2026-08-18)

The v7 baseline named two confounded candidates for the 10-cell presence→skill rise
(S2b, S2c, S3a, S4a, S4b, S4c, §1a, §4c): (1) behavior change from the F3/F4 embedding
fixes, (2) recovery from v6's 14 row-unattributable HTTP errors. Code-level read of the
F-sprint resolves this WITHOUT further prod spend: they are the same root.

## Mechanism

- F4 (#454) declares the state channel that documents the degradation:
  `embedding_timeout: True when skill_select's BGE-M3 embed timed out (keyword-only
  fallback this turn)` — i.e., the SKILL SEMANTIC TIER has a timeout path that
  silently degrades routing to keyword-only for that turn.
- F3 (#453) offloads BGE-M3 embedding OFF the event loop ("P1, ship-immediately").
  Pre-F3, embeds ran on the loop: under concurrent load — exactly the shape of a
  180-turn baseline run — loop contention produces embed timeouts.
- Timeout → keyword-only fallback → semantic-only rows (grief/self-compassion
  psychoed-proxy and structured-skill rows have thin keyword coverage) fall to
  `presence_only`. The same contention plausibly produced v6's 14 HTTP errors.

So v6's depressed rows and v6's errors were symptoms of one condition: semantic-tier
degradation under measurement load. F3 removed the contention; v7 ran with ZERO errors
and precisely the semantic-reach rows recovered.

## Status and residuals

- Confidence: mechanism-level (code + row-pattern consistency). Formal confirmation is
  now CHEAP because F4's channel is declared: any future run can read
  `embedding_timeout` per turn from audit/state. Assert it false on baseline runs —
  proposed as a standing instrument check in `measure_layer1_prod_http.py`.
- SERVING implication beyond measurement: real users during load spikes were receiving
  keyword-only routing with no observability until F4. Same family as the
  warmup-silent-failure finding (2026-06): semantic-tier degradation is silent by
  default. The F4 channel is the observability fix; alerting on it is open.
- Claim discipline holds: still no "improved by F1/F2" claims; the recovered rows are
  "measured without degradation for the first time," which is also why v6→v7 deltas
  remain indicative rather than improvement evidence.
