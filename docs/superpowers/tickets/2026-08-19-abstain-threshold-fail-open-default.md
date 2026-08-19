# Ticket (SAFETY-ADJACENT): the KB abstain gate defaults to fail-open, so any environment missing one env var silently serves everything

**Filed:** 2026-08-19 · **Status:** open
**Source:** surfaced by the cdai PR #512 measurement harness, which read the threshold as `0.0`
while prod serves `0.42` — the run was salvaged by re-evaluating raw similarities, but the
defect is structural, not a property of that one harness
**Type:** deterministic-guardrail gap on a safety-relevant gate

## The defect

`src/sage_poc/config.py`:

```python
COSINE_ABSTAIN_THRESHOLD = float(os.getenv("SAGE_COSINE_ABSTAIN_THRESHOLD", "0.0"))
```

`0.0` disables the gate entirely (`if COSINE_ABSTAIN_THRESHOLD > 0.0` in
`postgres_repository.py`). The default is deliberate — it is the documented instant rollback —
but it means **absence of configuration is indistinguishable from a decision to serve
everything**. Any process that does not carry the variable — a probe script, a local harness, a
new worker, a CI job, a future environment — silently runs with the closed-RAG abstain contract
switched off, and nothing in the output says so.

That is the wrong direction for a gate whose entire job, as the #512 measurement showed, is to
stand between an off-topic query and crisis content.

## How it actually bit

The #512 A/B harness imported `COSINE_ABSTAIN_THRESHOLD` to classify abstain outcomes and got
`0.0`. Every "abstain" it reported was therefore computed under fail-open while prod serves
`0.42`. The numbers were rescued only because the harness happened to record raw
`top_similarity` per query, allowing re-evaluation at the readback value afterwards.

**The rescue depended on an operator remembering to re-evaluate.** A harness that recorded only
the abstain booleans would have produced confident, quotable, wrong numbers — and they would
have read as evidence for a safety-surface decision. This is exactly the class the
measurement-parity rule exists to prevent: parity asserted mechanically from serving readback,
never from what the operator assumed the environment held.

## Fix candidates

**Minimum (harness-side, narrow):** any script producing quotable retrieval numbers asserts the
threshold it is using against the serving readback before printing anything, and fails loudly on
mismatch. Fixes the instrument, not the class.

**Better (config-side, deterministic):** make absence fail closed rather than fail open.
`SAGE_COSINE_ABSTAIN_THRESHOLD` unset outside an explicit test context should either take the
calibrated value or refuse to start, so that "serve everything" requires someone to *write*
`0.0` rather than to forget a variable. The rollback path is preserved — it just becomes an
explicit act with a value attached, which is what a rollback should be. This is the
deterministic-guardrails principle: the safe state should not be contingent on operator memory.

**Adjacent, worth deciding at the same time:** `config/prod_flags.yaml` classes
`SAGE_COSINE_ABSTAIN_THRESHOLD` as **`class: feature`**. The #512 evidence shows this flag
screens crisis content off off-topic queries; under the 2026-07-28 taxonomy
(screens/preempts/terminates on risk content → safety) that reads as **`class: safety`**.
Reclassifying subjects it to signed-value discipline and CI enforcement, which is the mechanism
that would keep a future threshold change from moving without clinical sign-off. Governance
call, not a unilateral edit — raised here rather than made.

`SAGE_KNOWLEDGE_ABSTAIN_THRESHOLD` sits behind the same pattern and should be reviewed together.

## Related

- cdai PR #512 (drop ivfflat + threshold 0.42 → 0.58) — the run that surfaced this
- `docs/superpowers/tickets/2026-07-23-parity-guard-readback-coverage-gap.md`
- Sibling class: corpus sync fail-open silent chunk loss (filed same day)
