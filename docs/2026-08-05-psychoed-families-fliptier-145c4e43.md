# Psychoeducation Phase 3 -- flip-tier conformance run (FLIP-TIER, real intent + real LLM)

> **📌 DECLARED DELTA: PROD SERVES: psychoed OFF. THIS RUN ARMS: 1f,3c,4b,6d,7c,s2c -- flip-tier measurement of the UNFLIPPED mechanism at parity on all other flags (declared delta, not a parity violation -- see _PSYCHOED_DECLARED_DELTA_VARS).**

## Provenance
- **sha**: 145c4e43
- **instrument**: FULL-GRAPH app.ainvoke, REAL intent_route + REAL LLM (no node patches); only write_session_audit is captured (parity-safe); retrieval state below is the ACTUAL state, not assumed
- **flag_parity**: VERIFIED vs desired(railway) (psychoed vars carved out as the declared delta -- see below; all other SAGE_ vars hard-parity)
- **categories_armed**: ['1f', '3c', '4b', '6d', '7c', 's2c']
- **declared_delta**: PROD SERVES: psychoed OFF. THIS RUN ARMS: 1f,3c,4b,6d,7c,s2c -- flip-tier measurement of the UNFLIPPED mechanism at parity on all other flags (declared delta, not a parity violation -- see _PSYCHOED_DECLARED_DELTA_VARS).
- **retrieval**: ACTIVE (read-only pool: default_transaction_read_only=on -- writes rejected at the DB session level, not merely an application-level promise)
- **instrument_faults**: 0 (clean)

## Per-family results (hard-required rows only; F1 naturalistic reported separately)
| family | conform/total | observed-only (no pinned disposition) |
|---|---|---|
| F1 | 81/133 | 0 |
| F10 | 0/4 | 0 |
| F2 | 3/7 | 0 |
| F3 | 6/8 | 0 |
| F4 | 12/13 | 0 |
| F6 | 5/5 | 0 |
| F8 | 6/6 | 21 |

## F1-naturalistic baseline -- **FLIP-TIER**: 0/61 (0.0%) -- TRACKED BASELINE, never a hard gate (spec §7.1)

## Skip counts (spec §7.2 no-silent-caps -- every skip logged, never a silent filter)
- `ar_draft_pending_validator`: 3
- `f9_ci_tier_only`: 7
- `rag_top_ci_tier_only`: 1

## xfail reproduction at prod parity (F4-002 / F10-004, ruled)
- **F10-004**: REPRODUCED (still diverges, as expected) -- real_label='scope_refusal' audit=MISS(F10-004 audit: 'psychoed_gate_action': expected 'pass', got None); state=MISS(F10-004 state: 'skill_match_method': expected 'psychoed_resolver', got None)
- **F4-002**: REPRODUCED (still diverges, as expected) -- real_label='general_chat' never_proceed=MISS(clear_no/non-crisis skill_match_method='psychoed_resolver'); audit=MISS(F4-002 audit: 'psychoed_matched_row_id': expected '3c-t3', got 'menu_pick'); state=MISS(F4-002 state: 'skill_match_method': expected 'psychoed_menu_after_weave', got 'psychoed_resolver')

## flip_tier_only rows (F10-003 class) -- OBSERVED ONLY, never asserted
- observed: 0, not_observed: 1

## Register-amendment-8 rider (a): real-retrieval smoke case (NON-GATING)
- did not fire this run (retrieval was ACTIVE; genuinely retrieval-dependent, non-deterministic outcome); passages surfaced: ['depression-003-en-000', 'depression-003-en-002', 'depression-001-en-002', 'depression-003-en-001', 'depression-003-en-003']

## F5/F7 procedural families (--include-procedural)
- returncode: 0 (PASS), duration: 16.9s
```
.........                                                                [100%]
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/langgraph/cache/base/__init__.py:8
  /Users/knowledgebase/Documents/Sage/sage-poc-psychoed-spec-wt/.venv/lib/python3.12/site-packages/langgraph/cache/base/__init__.py:8: LangChainPendingDeprecationWarning: The default value of `allowed_objects` will change in a future version. Pass an explicit value (e.g., allowed_objects='messages' or allowed_objects='core') to suppress this warning.
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
9 passed, 1 warning in 12.84s
```
