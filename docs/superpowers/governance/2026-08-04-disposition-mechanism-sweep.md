# Disposition–mechanism sweep — which mechanism POSITIVELY produces each signed disposition (2026-08-04)

**Question (owner-posed, post-cardiac):** the cardiac gap's shape was *a signed disposition carried only by
the LLM's classification* — measured at 6/20 no-crisis-resources in a failing window. Is it the last one,
or just the found one? This map names, for every clinician-signed disposition, the mechanism that produces
it, in three bins:

- **DET** — deterministic end-to-end (lexicon/rule/template; or local-model with pinned weights — same
  input, same output). Window-independent.
- **LLM** — the signed disposition exists ONLY if the LLM classifier/generator produces it. Each of these
  is a latent 6/20: the pins stabilize within-window only (window-bounded-verification rule, 2026-07-31).
- **HYB** — deterministic on the safety-critical half (usually detect or final copy), LLM on the other
  (usually render or entry). Exposure = the LLM half; noted per row.

Sources: `signed_clinical_fields.json` (12 pins), `safety_rule_activation_map`, the approval-sheet lineage
(1a–1d, D1 A1/A2, B1, C1, GL-1, item-1–5 of 2026-07-30, K-batch, 7a–7d), and this week's measured behavior
(8/36 re-pin rows, N=20 cardiac characterization). Mechanism claims verified against source, not recalled.

## The map

| # | Signed disposition (signature) | Mechanism that produces it | Bin |
|---|---|---|---|
| 1 | Explicit SI / crisis phrases → crisis card (S1 lexicon, SK-EN/AR-001-003, tiering v7.1) | Node-1 keyword lexicon → short-circuit `crisis_response`, templated copy, tier rules | **DET** |
| 2 | Harm-to-others → crisis (HTO-001, Vee 07-09) | Node-1 rule (deterministic backstop; semantic tail unmeasured, known) | **DET** (tail: LLM) |
| 3 | Crisis copy + helpline numbers (GL-1, CRISIS_RESOURCES) | Templated, single-sourced, hours-aware card; CI-pinned | **DET** |
| 4 | D1 medical screen question + branch table (A1/A2, Vee 07-17) | Pinned strings + deterministic branch map (`.get(...,'grounding')` fail-safe) | **DET** |
| 5 | Psychosis/mania/dissociation → HR referral (CF-007/008/009, 07-17) | Node-1 clinical-flag lexicon → HR terminal; Node-8 neutrality gate template-swaps the copy | **DET** detect+copy |
| 6 | HR referral copy (SAKINA + hours, Vee 07-22) | Pinned template, verbatim drift-guard | **DET** |
| 7 | Derealization → anxiety-track referral (CF-010, 1a–1d + item-1) | Node-1 verbatim strings → deterministic terminal, pinned copy | **DET** (recall gap known: 4 strings, E7-shape — a MISS falls to LLM routing, currently safe-direction) |
| 8 | OCD compulsion → veto + ERP referral (#218) | Deterministic veto patterns + pinned referral line at output_gate | **DET** |
| 9 | Harm-intrusive → abstain (07-08 packet) | Deterministic veto patterns | **DET** |
| 10 | §5 psychosis content-neutrality (account-frame) | Node-8 deterministic allowlist gate → template swap | **DET** |
| 11 | Pure panic → grounding (§1c-A, Vee 07-28, scoped-back item-1) | Keyword `acute_direct_entry` ("panic attack" cluster) = DET; **non-keyword §1c-A phrasings enter via intent_route's LLM** — measured: "out of control" / "losing my mind" → presence 2/5 rows | **HYB — LLM entry** |
| 12 | Cardiac class → crisis (item-3, Vee 07-30) | **TODAY: LLM classification only** (override deference covers the intent=crisis door; the freeflow door is LLM's). Node-1 rule BUILT INERT (PR#402) — flips to DET on Vee's tick | **LLM → DET on tick** |
| 13 | Grief/fresh-loss → presence-mode grief_loss (S2a ruling) | LLM classification end-to-end; measured over-fire: "passed away and I can't cope" → crisis 1/5 (iatrogenic crisis card on a bereaved user; diagnosis PR#380) | **LLM** |
| 14 | Skill contraindications honored at delivery (signed per-skill contraindication strings) | **LLM discretion at compose time** — the gate does not fire on LLM-discretionary contraindication strings (standing finding, §6b OCD most acute) | **LLM** |
| 15 | HR protocol takes priority mid-skill "same way crisis does" (§HR) | Crisis half = deterministic short-circuit; **HR mid-skill half rides LLM state reading — measured 4/5 (SF-2)** | **HYB — LLM half** |
| 16 | Psychoed question → prescribed psychoed skill (B1, Vee 07-23) | `info_request` is an **LLM intent class** → deterministic consult mapping; −§1f single-variant flicker in the 8/36 re-pin is this entry moving | **HYB — LLM entry** |
| 17 | Keyword-batch offers (K1/K2, §3a/§3b clauses, §1e, §6b DEARMAN) | Keyword prepass + reranker (fp32 pinned, deterministic given weights) = DET; **non-keyword paraphrase variants enter via LLM intent** (mechanism-2 residue; −§3a flicker) | **HYB — LLM tail** |
| 18 | Sensitive-topic venting suppression (Routing-SF-2) | Deterministic routing authority **fed by LLM-scored signals** (intensity/engagement) | **HYB — LLM input** |
| 19 | Jailbreak/scope refusal + identity single-source (CUO-ID-001) | Deterministic detector + derived response (K3 "crossing a line" over-catch = known over-fire, safe direction) | **DET** |
| 20 | Post-crisis step-down never-snaps-to-none (W2/G4) | Deterministic consecutive-clear counter; S7 classifier is LLM but step-down requires BOTH | **HYB** (fail-safe direction) |
| 21 | MM deroute while unsigned (Vee 07-31 item 3) | Deterministic skip-set (KEYWORD_SEMANTIC_SKIP) | **DET** (successor finding queued: body_scan absorbs the demand, itself unsigned — Vee item already filed by the parallel stream) |

## The worklist — LLM-carried rows ranked by clinical stakes

1. **Row 12, cardiac → crisis.** Built, inert, one tick from DET. *Same-day item; nothing to build.*
2. **Row 13, grief → presence (S2a).** The inverse failure shape: an over-escalation serving a crisis card
   to bereaved users, measured live 1/5, diagnosis already written (intent_route "can't cope" over-fire,
   PR#380). Deterministic realization = a grief-context suppression/deference rule at the same altitude the
   cardiac rule occupies — same build pattern, opposite direction. **Recommend: next inert build.**
3. **Row 14, contraindication delivery.** Signed clinical constraints carried by compose-time LLM
   discretion, no gate. Deterministic realization = contraindication strings become output_gate-checked
   (the #218 ERP-referral pattern generalized). Larger build; needs its own characterization first
   (which skills, which strings, measured miss rate — two windows).
4. **Row 15, HR mid-skill priority.** Measured 4/5 once, single window. Needs a two-window characterization
   before any build (the window rule's first scheduled use beyond cardiac).
5. **Rows 11/16/17 LLM entries (§1c-A residue, psychoed entry, keyword-batch tails).** Real but
   lower-stakes: the failure mode is under-delivery of a skill/psychoed offer (presence instead), not a
   missing crisis resource or a contraindicated delivery. They ride the existing enrichment tracks
   (increment 4, sibling clauses) rather than new deterministic builds.
6. **Row 18, venting suppression inputs** — audit-only observation first; no known miss.

**Bottom line:** the cardiac shape was NOT unique. Two more signed dispositions are carried wholly by the
LLM (grief-presence, contraindication delivery) and one signed priority is half-carried (HR mid-skill).
None of the three has crisis-resource stakes as high as cardiac's (grief's failure is an unwanted crisis
card — iatrogenic but resource-PRESENT; contraindication's is a wrong-skill delivery; HR's is a delayed
referral) — which is consistent with cardiac having been the right one to jump the queue. The v7 thesis
(rules evaluate first, the LLM renders language) now has its empirical worklist: rows 13 → 14 → 15, in
that order, each entering as characterize-then-build-inert-then-tick.
