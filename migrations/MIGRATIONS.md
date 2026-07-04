# Migration Number Ledger

Migration numbers are CLAIMED HERE AT BRANCH CREATION, before writing the file, so two
concurrent branches never independently mint the same number (a silent merge/deploy-runbook
conflict — root cause of a real collision on 2026-07-03 when `feat/abstain-cosine-gate` and
`feat/crisis-tiering` both created a `006`). Add a row when you start a branch that needs a
migration; keep it in ascending order.

| # | file | branch | table | status |
|---|------|--------|-------|--------|
| 004 | 004_add_s3_score_to_session_audit.sql | (merged) | session_audit | applied |
| 005 | 005_add_knowledge_query_trace_to_session_audit.sql | feat/arabic-rewriter-wiring (merged #84) | session_audit | applied prod 2026-07-03 |
| 006 | 006_add_crisis_tier_to_session_audit.sql | feat/crisis-tiering | session_audit | claimed |
| 007 | 007_add_knowledge_top_similarity_to_session_audit.sql | feat/abstain-cosine-gate | session_audit | claimed (renumbered from 006 to avoid collision) |
| 008 | 008_add_precedence_to_session_audit.sql | feat/e-build-b0-precedence | session_audit | claimed — DEPLOY GATE for SAGE_ROUTE_PRECEDENCE flip |
