# STANDING RULE — Instrument Parity, Mechanical (Follow-up 1, SIGNED 2026-07-28)

**SIGNED by reviewer 2026-07-28** in the mechanical shape below (helper-only
invocation, refuse-on-gap, refuse-on-deploy-window, CI-grep enforcement, provenance
stamped on artifacts; coverage-hole PR as ordered prerequisite).

**Rationale document:** `2026-07-28-parity-incident-q6-artifact.md` (the near-miss
incident, kept OPEN). This rule carries its own justification: a non-parity harness
produced a clinically alarming readout indistinguishable from a real one and
consumed a full escalation cycle; next time the readout may not be an artifact.

## The rule (mechanical, not procedural)

1. **One supported invocation path for evidence.** The graph-invocation helper
   (extracted from the parity runner) is the ONLY supported way to invoke the graph
   for any run whose output feeds a decision, memo, matrix row, or escalation. It:
   - derives the full flag set from the `/health/version` serving readback,
   - REFUSES to run on readback gaps (a flag in `config.py` not covered by readback
     is a hard error, not a default), and on serving≠desired deploy windows,
   - stamps every resolved flag + build SHA into its output structure.
   Scripts that invoke the graph directly do not produce evidence. Enforcement:
   a CI check greps instrument scripts for direct `build_graph`/`ainvoke` usage
   outside the helper module (same enforcement pattern as check_state_channels).
2. **The artifact carries its provenance, not just the run.** Every characterization
   readout, memo evidence block, and matrix row embeds the flag set + SHA it was
   produced under, inline, so a non-parity artifact is DISTINGUISHABLE at read time.
   Run 1's readout was indistinguishable from a valid one at the point it was read
   and escalated on; that is the actual failure this rule closes.
3. **Prerequisite PR:** close the readback coverage hole first —
   `SAGE_INFO_REQUEST_CONSULT`, `SAGE_HIGH_RISK_DETECTION`,
   `SAGE_HR_NEUTRALITY_GATE` added to `/health/version` raw_env (no behavior
   change). Rule 1's refuse-on-gap makes this hole loud instead of silent.
4. **Distributional rider (from the Node-2 bistability finding):** for runs whose
   verdict depends on an LLM-classified turn, the helper supports N-sample mode and
   the artifact records the distribution, not a single trajectory. The conformance
   matrix is not citable as settled evidence until per-row stability is established
   this way.

Asks: (a) approve rule 1's helper-only enforcement mechanism, (b) approve the
coverage-hole PR, (c) assign the audit-row additions from the bistability finding
(decode params, seed-if-sampled, classifier context hash) to the same PR train.
