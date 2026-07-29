# C1 flip execution record — two events, two ledger lines (2026-07-29)

Per the PO-amended flip sequence (readbacks bracketing each change; two flags = two attributable
events) and the Vee Option-1 ruling with its three in-ruling conditions.

## Event 1 — SAGE_INFO_REQUEST_CONSULT restore (consult back live)

- **Change:** desired `false` → `true` via the register's first sanctioned change (PR#387,
  `restore-consult-signed-value`, merged 19:22Z; item-1 pre-authorization, evidence chain in the
  register row's note). Serving converged (Railway restart) and readback-verified:
  `info_request_consult_enabled: true` on build `dec4a9e7`.
- **Live verify:** probe `c1-verify-consult-1785353480` — "What is anxiety?" →
  `info_request_skill_consult` → `psychoed_anxiety`, `gate_path standard`, **no cards** (C1 still
  dark), audit purpose NULL. Exact expected pre-flip state.
- **Authority:** existing ratification (Vee B1 + 2026-07-29 re-ratification + v7.3 record). No new
  ruling.

## Event 2 — SAGE_CONSULT_SOURCES flip (C1 live)

- **Change:** register's second sanctioned change (PR#389, merged `a4c0f0a0`): `null` → `"true"`
  with `signed_value` + `signature_ref` (Vee Option-1 2026-07-29 + PO amended-sequence approval).
  Applied via `apply_prod_flags.py --apply` — dry-run diff showed exactly ONE set, nothing else;
  one batched invocation; one restart.
- **Owner:** PO (this session's amended-sequence approval). **Timestamp:** 2026-07-29 ~19:45Z.
  **Build:** `dec4a9e7f4de` (C1 code, deployed under lock earlier this day; migration 018 applied
  and verified nullable BEFORE the flag, per the deploy-gate).
- **Readback both sides:** pre-flip `consult_sources_enabled: false` / post-flip `true`, consult
  `true` both sides, `crisis_copy_templated: true` both sides.

## Three live checks (probe sessions in prod session_audit, verbatim IDs)

| Check | Probe | Result |
|---|---|---|
| Consult-positive | `c1-check1-consult-1785354215` "What is anxiety?" | `psychoed_anxiety` consult; **3 article cards** in X-Sage-Sources; audit `cards_only`, 5 ids, sim 0.692; reply conversational (unchanged register) |
| KB-path unchanged | `c1-check2-kbpath-1785354215` "How do I sleep better?" | no skill; evidence cards as before C1; audit purpose **NULL** (evidence semantics), sim 0.624 |
| ABSTAIN floor | `c1-check3*` ×3 | **Live negative not naturally reachable:** all four consult-set topics have strong KB coverage (sims 0.70+). Floor verified by (a) unit fixture `test_cards_node_abstain_means_zero_cards` (abstain → zero cards, PR#384), (b) shared implementation — cards node calls the identical `repo.retrieve` + `COSINE_ABSTAIN_THRESHOLD=0.42` gate serving the KB path since PR#86, (c) `c1-check3c` (nonsense phrasing) demonstrated the floor binding at sim 0.456 on the KB path AND the consult's fail-open guard (no skill hijack). Stated per the primary-record standard: demonstrated properties only. |

**Label condition (ruling condition 1):** all emitted entries `type: article` → frontend label key
`reading` → **"Further reading"** (pinned by `source-card-labels.test.ts` + signed registry
comment). DOM-level visual confirmation: PO's browser check outstanding (5-second check; API +
component-pin verified here).

**Invariant:** every card ⊆ that turn's audited `knowledge_passage_ids` (3-card header cap from 5
audited ids) — holds on all probes. Purpose discriminator live (`cards_only` vs NULL) exactly per
ruling condition 2.

## Carried debt (into the flag-governance workstream)

- CONFIG/DEPLOY lock extension for flag writes (mutual exclusion, not just sanctioned-path +
  watchdog) — PO-ordered addition, ship-after per PO ("don't let it block step 3").
- The two same-day-earned guards (pre-flip readback gate; transcript-level writer investigation) —
  promoted-to-standing argument recorded in the RCA addendum.
