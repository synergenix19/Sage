# SDD Ledger — psychoed Phase 1 content plan (2026-07-23)
Plan: docs/superpowers/plans/2026-07-23-psychoed-phase1-content-plan.md
Branch: docs/psychoed-pathways-design (contains pinned docx Task 1 needs; plan named feat/psychoed-phase1-content but branching off unmerged docs branch would orphan the PR — recorded deviation)
Base at start: dad19358
Checkpoints retained by controller: T1 fingerprint, T10 expected-fail, per-category transcription diffs
T1 fingerprint reconciliation: erratum committed, constants verified by controller (checkpoint held)
Task 1: complete (commits 4c65338a..5635cb1c, review clean; Minor: extraction file swept into erratum commit by controller git add -A, byte-identical verified by reviewer live re-run)
Task 2: complete (commit 501bf826, review clean; 1f-b1 transcription controller-verified exact)
Task 3: complete (commits dfec196f..850817c5, review clean; Minors: registry-rule valid-direction only fixture-tested; provenance-fix red-run not captured. 1f rows=inferred provenance, worry_tree bridge=null pending clinician)
Task 4: complete (commits 165ee86b..ca210851, review clean, no findings; 3c framing sanctioned-equivalent; 3c-t4/t5 inferred; bridge removed per spec 4.3)
Task 5: complete (commit 734dbcdd, review clean; 4b-b6 stage-direction excluded; diagnosis_guard armed category-agnostic per spec 5.5, noted for packet)
Task 6: complete (commit 66f2eca7, review clean; 6d guard=E7-adjacent flagged -> packet flip-consideration alongside §6a-guard blocker; red-run methodology accepted)
Task 7: complete (commit 2e4bfda3, review clean; condition-level bridge schema added; §7c ruled-amendment realized; guard routes 7a/7b summarized for packet)
Task 8: complete (commit 72f433f6, review clean; S2c all doc_table; reunification phrasing correctly excluded from tables -> provenance_note; flip_gate_note verbatim)
Task 9: complete (commits db0bd40f..6c52488d, review clean; human_referral_close=PENDING-CLINICIAN adjudicated; 3c-b7 restored byte-identical; count-claim scrubbed)
Task 10: complete (commits ab6c659b..6e89765e, staged red observed by controller, subsumption gap found by reviewer + fixed; collision table: 2 exact + 2 subsumption entries, 3 pending clinician; weave-dominance rule -> packet ask 3)
Task 11: complete (commit 227a2414, review clean; weave data draft w/ evaluation_semantics pinned; EN-only, AR gated on validator)
Task 12: complete (commit 3b2ec3d2, review clean; Minor: block-disk cross-check subset-only, rogue block-only category tolerated — final-review triage)
Task 13: complete (commits a13c2718..f953672f, review clean; packet enumerates 40+18+4+31 by name, 12 asks, 3rd period+capital site 6d-b2 self-found; Lane-3 clock STARTED)
Task 14: complete (commits 5197afd2..5291bc1b, re-review RESOLVED all 5; handoff notes carry verbatim keys, corrected 3-form bridge taxonomy)
Final review: READY FOR MERGE after fix wave 969c802e + pin re-stamp bb5829cd (138 tests green; 68 dash sites = 64 comma / 4 period+capital, all 4 read-differently sites enumerated for clinical)

--- CLEANUP RULING (2026-07-28, session close) ---
Keep worktree + branch until the sign-off packet signs. At signature: move this .superpowers/sdd/ audit trail (task briefs, reports, review packages, this ledger) into docs/superpowers/governance/ adjacent to 2026-07-28-psychoed-signoff-packet.md IN THE SAME CHANGE that deletes the worktree/branch. Rationale: the trail answers "who transcribed this ratified copy, against what source, reviewed by whom, with what catches" — clinical-governance weight outlives the branch. Branch itself carries nothing the merge commit (95bf2370) lacks.

# SDD Ledger — psychoed Phase 2 mechanism plan (2026-07-28) [RECONSTRUCTED after reviewer git-reset incident; committed henceforth]
Plan: docs/superpowers/plans/2026-07-28-psychoed-phase2-mechanism-plan.md (amended: gap-1 pathway-clear, gap-2 escalation audit)
Branch: feat/psychoed-phase2-mechanism | Checkpoints: T8 diff ✓done, T11 hash-gate branches ✓done, T12 byte-identity, T13 escalation graph test
P2 Task 1: complete (a0a5e602; Low: red transcript not pasted)
P2 Task 2: complete (98311d10; Medium report gap fixed post-hoc; standing rule: no red transcript = rejected)
P2 Task 3: complete (e9aacd8e; ACCEPTED DEVIATION: pathway keys default at consumers — binding on 8/10/11)
P2 env fix: uv sync --extra dev (pytest-asyncio missing) -> Mechanism-A baseline 18/18 GREEN
P2 Task 4: complete (b5051512; adversarial hand-traces fail-closed correct)
P2 Task 5: complete (4d3b93d9; threshold band probes exact)
P2 Task 6: complete (8fa4ff79..14a1f6be; plan-code KeyError found; Medium ambiguity fixed: multi-match fails closed both tiers)
P2 Task 7: complete (efba7f39..bcdfc8e4; MEDIUM-HIGH false-attestation fixed; template status strings ADVISORY — flag is only gate; menu_first+weave = data-guarded)
P2 Task 8: complete (d71f3da6..7e9bba3b; controller checkpoint + independent review clean; 9 clear sites; accepted: path-accumulation, escalation-scoped clear)
P2 Task 9: complete (e2590959; kb_ref schema additive, 28/28 skills load)
P2 Task 10: complete (16a9af8d..cc981b39; HIGH plan-gap fixed: backstop gated active-skill + Classifier A per spec §2.1/§2.2)
P2 Task 11: in progress (6482155f..1f96fec1; checkpoint: mismatch branch correct, corruption hole fixed, EN entry gate added; REVIEW: Medium menu-after-weave AR path open; Low compose_turn1 exception→server handler, triage at final review)
INCIDENT: T11 reviewer popped pre-existing s3_semantic stash + reset --hard destroyed uncommitted ledger (this reconstruction); stashes verified intact; ledger committed from now on
P2 Task 11: complete (commits 6482155f..a463f394; checkpoint fixes: corruption chain, EN entry gates x2, menu-after-weave AR fall-through; Low compose_turn1-exception noted for final triage; INCIDENT recovered, no-stash-pop rule standing)
