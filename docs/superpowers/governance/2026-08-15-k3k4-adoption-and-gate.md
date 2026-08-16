# K3/K4 recognition clauses — Vee adoption + signed gate record (2026-08-15)

**Mechanism and grade:** first cut authored at Vee's own request (PO relay commission),
adopted with her clarifying rulings (PO relay, 2026-08-15). Draft-adoption signature, the
established mechanism of this stream. Her rulings are quoted below verbatim where they
gate implementation.

## Adopted clause 1 — behavioral_activation (K4, section-7b lineage)

Appended to `semantic_description` (748 chars total):
> "Wanting to reconnect with people or re-engage socially after a period of withdrawing,
> isolating, or losing touch; taking one small social step back, such as replying to one
> message, a short check-in text, or a brief call, repeated to rebuild contact."

Bins: (a) as proposed. (b) as proposed, with the grief exclusion now ENFORCED
deterministically (below). **(c) ruled: the estranged-specific-person case goes to IE
("BA owns the pattern; IE owns the person")** — recorded as the routing intent; no code
carries it yet (the presentations that surface it route through 6b's own recognition).

## Adopted clause 2 — interpersonal_effectiveness (K3, section-6b lineage)

Landed as a dedicated `semantic_anchors` entry, NOT a description append — max-over-anchors
lets the clause embed alone; the description-append form drowned in the 591-char existing
text (measured: targets still wrong-routed). Anchor text:
> "Recognizing oneself as the one overstepping or crossing a line with another person and
> wanting to stop; preparing the conversation to own the behavior, repair the
> relationship, and change the pattern, using the same DEARMAN structure and self-respect
> skills."

**Her clarified framing (adopted, verbatim):** "DEARMAN confirmed for the
self-as-transgressor case, applied as conversation structure (Describe the behavior,
Express ownership, Assert the change I'll make, Reinforce the relationship) — with FAST
retained as the guard against the opposite failure: the apology collapsing into
self-abasement or excessive self-blame. The skill's step framing for this presentation
should emphasize repair-and-change, not request-making." The step-framing emphasis is
recorded as her clinical guidance for this presentation's delivery; step-content edits
were not commissioned and none were made.

Bins: (a) as proposed. (b) as proposed. **(c) ruled: repeated overstepping resolves into
the next conversation = 6b's machinery, CONDITIONAL on the probe pair below** — her tick
is bound to those probes existing and passing.

## The scoped evolution of the description principle (her paragraph, entered as ruled)

The standing principle held `semantic_description` to technique identity only, with
presentation matching living in `target_presentations` (the M2 single-symptom-surface
lesson). These clauses deliberately blur that separation, for a legitimate reason:
paraphrase variety exceeding keyword reach is what Tier 2 exists for. It enters the
record as a SCOPED EVOLUTION, not a drift: **presentation enrichment is permitted in
descriptions/anchors only when it rides the full signed gate** (fixtures-first, mandatory
`calibrate_threshold` re-run, harm-0, id_oos floor, staging/graph probe pair). That is
what distinguishes this front-door change from the back-door pollution the original rule
banned. This PR is not license for gate-free description edits.

## The gate, as run (all evidence 2026-08-15, local BGE, prod-parity flags)

1. **Fixtures-first failure evidence:** pre-clause, the targets wrong-routed —
   "i want to reconnect with people" -> interpersonal_effectiveness 0.4827;
   "i need to stop crossing a line" -> stop_technique 0.5270; "i keep overstepping
   with my wife…" -> self_compassion_break 0.4741.
2. **Post-clause targets:** all four resolve correctly, above threshold (BA 0.524/0.560;
   IE 0.611/0.578).
3. **Calibration (mandatory):** re-run both arms. The gap-gate failure verdict is
   PRE-EXISTING on clean master (baseline gap -0.4388; post-clause -0.4446; the delta is
   one off-topic score moving +0.006, still below the routing threshold — no off-topic
   routes). τ untouched. Routing/rerank/abstain suites incl. the id_oos floor tests:
   224 green.
4. **Her conditional probe pair (full-graph, real classifier):**
   - harm-colored ("crossed a line last night and i hurt her") -> `crisis_response`
     (safety tier owns the turn; never reaches matching) ✓
   - control-colored ("she never listens, she needs to learn") -> NO IE offer ✓
   - grief-colored ("reconnect with people since the loss of my father") -> initially
     FAILED (BA offered) -> **fixed by the deterministic bin-(b) swap**: BA-in-offer +
     bereavement signature (the SAME single-sourced `_GRIEF_TERMS` as the S2a deference,
     never a second list) -> `grief_loss` offered, marker `ba_grief_exclusion_swap`.
     Re-verified both directions: grief -> grief_loss/swap=True; clean -> BA/swap=False ✓
   - contented solitude -> no route ✓
5. **Wrong-route no-regress:** covered-IE-territory spot-check green; full routing
   suites green; known-shadow ledger unchanged.
6. **Pinned:** `tests/test_k3k4_recognition.py` (8 tests, @slow/real-BGE, E7
   paraphrase-independent).

**Remaining before serving:** prod deploy under lock + live behavioral probe pair
(description/anchor changes are LIVE routing changes once deployed — no flag gates them;
rollback = revert PR). EN-only this pass; AR rides the AR track.

## Addendum — gate round 2 (2026-08-16, post-deploy findings)

The live probe pair (the gate's final rung) caught two defects the local gate missed:

1. **The veto could not see the anchor** (measured 3/3 live: `keyword_rerank_veto` killed
   the K3 offer against the description alone). Mechanism fix: the veto now scores the
   SAME signed texts Tier-2 ranks — description AND anchors, max per skill (M2's one-
   recognition-surface principle applied to the veto). Monotonically less aggressive,
   only for skills carrying signed anchors; id_oos/abstain suites green.
2. **The adopted anchor's opening over-matched self-critical schema phrasings**
   (test_skill_select's CBT fixture ranked IE 0.4926 — a latent matcher regression that
   shipped in #438 because that suite was omitted from the final gate batch; my
   omission, recorded. Live impact none on probe: the classifier routes the fixture
   phrasing to freeflow before matching). Fix: the anchor wording NARROWED, scored
   empirically for separation (K3 targets 0.587/0.568; CBT fixture 0.4742 < CBT's own
   0.4843 — CBT reclaims it):
   > "Crossing a line or overstepping with a partner, family member, friend, or
   > colleague; preparing the apology or repair conversation with them, owning the
   > behavior and what will be different, using the same DEARMAN structure and
   > self-respect skills."
   **RE-ADOPTED as written (Vee + PO deploy go, one relay, 2026-08-16: "We have
   approved it") — the wording was presented verbatim as the approval artifact, so
   approve-as-written is the adoption under the established draft-adoption mechanism.**
   Full gate green (289 tests, test_skill_select included this round); deploy follows.

## Addendum — round 3 and CLOSE (2026-08-16)

**K3 (the commissioned fix) is LIVE and verified: "i need to stop crossing a line"
offers interpersonal_effectiveness 3/3 on the served build (6cae3379).** The path there
required widening BOTH cross-encoder call sites to the one recognition surface
(keyword-veto in round 2, semantic-side _rerank_route in round 3 — each measured live
before fixing). K4, all four exclusion bins (incl. the live grief swap), and the CBT
fixture hold on every probe round.

**K3-b (my added hard paraphrase, "i keep overstepping...") is a measured recall
boundary, NOT a defect in the commissioned fix:** under prod's V2 flags the bi-encoder
ranks worry_time/dbt_tipp/cognitive_restructuring above IE on that phrasing, so IE never
reaches the cross-encoder's top-5. Pinned as an xfail with the full reason (visible,
never silently green). Chasing it means bi-encoder-tier work with real margin risk —
a follow-up decision, not part of this adoption.

**Two instrument lessons earned this round, recorded as rules:**
1. Local probe scripts MUST export prod-parity flags (prepare_evidence_env or explicit
   SKILL_*/SAGE_* riders) — my V2-off locals produced false "K3-b fixed" readings twice.
2. Deploy convergence keys on the deployment-status API + a behavioral probe of the
   change itself, NEVER build_sha (third SHA-lie instance this month; the variable-
   restart window serves old code under the new SHA).
