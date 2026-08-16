# Ticket: diagnosis-guard consent-to-serve (spec 5.5 yes-branch) has no deterministic implementation

**Filed:** 2026-07-31 · **Source:** psychoed Phase 3, Task 8 (F6/F7/F10 fixture families), first-run
characterization of `F10-004` — surfaced by fixture authoring, independently confirmed by reviewer
with a live repro, human-ruled
**Status:** open — fix requires its own branch and normal review; `F10-004` disposed as strict-xfail
pending this ticket, not fixed here · **Type:** BUILD (spec-sanctioned-behavior-UNBUILT — distinct
from a built-mechanism-divergent-behavior bug; see "Class note" below)
**Links:** `.superpowers/sdd/2026-07-30-psychoed-phase3-fixtures-plan/task-8-report.md`,
`tests/fixtures/psychoed/f10_diagnosis.jsonl` (`F10-004`, `F10-004b`), `docs/superpowers/specs/
2026-07-23-psychoeducation-pathways-design.md` §5.5

## The gap

Design doc §5.5's diagnosis-guard row split describes: "Guard-script yes-branch (\"Want me to walk
through that?\" → consent): serve the relevant concept block through the same audited path." No
code path in `src/sage_poc/` implements this. A "yes" reply following a `formal_diagnosis` stage-1
serve produces **no serve of any kind** — `psychoed_serve` stays `None`, `skill_match_method` stays
`None`, `psychoed_gate_action` stays `None` (the integrity gate never even runs, since there is no
`psychoed_serve.block_id` for it to check).

**Mechanism (root cause, traced end to end):**
1. `skill_select.py`'s psychoed block reaches `psy_resolver.resolve(...)` normally on the "yes"
   reply (no PSY-WEAVE-1 interception for a non-weaving category — see the companion ticket
   `2026-07-31-weave-vs-guard-consent-precedence.md` for the weave-enabled-category case).
2. `resolver.resolve()`'s active-category branch (`resolver.py` ~L189-193) only ever matches a
   normalized reply against the ACTIVE category's own `menu_label` set via `_match_menu_label`.
   "yes" matches no `menu_label` — unsurprising, since the guard's own stage-1 serve
   (`serve.py`'s `formal_diagnosis` branch) never offers a menu in the first place
   (`psychoed_menu_offered` stays `false` after it, confirmed).
3. There is no OTHER state channel anywhere in this codebase tracking "the guard's own consent
   question is outstanding," the way `offered_skill_ids` / `offer_response` /
   `offer_choice_skill_id` track a SKILL offer's consent (R1 flow). Grep-confirmed zero hits for
   any diagnosis-guard-specific consent/pending-question channel.
4. Net: "yes" falls through `skill_select`'s psychoed block completely unchanged and reaches
   `freeflow_respond` via the generic `psychoed_continuation` L2 override (delta 15's mechanism) —
   the same path an unrelated push-further reply takes (see `F10-003`).

## Class note (why this is a BUILD ticket, not a BUG ticket)

Distinct from `2026-07-30-menu-label-short-token-substring-collision.md` (F4-002's class): that
ticket is a **built-mechanism-divergent-behavior** bug — the mechanism exists and runs, but a
specific input collides with an unrelated tier and produces the wrong output. This ticket is
**spec-sanctioned-behavior-UNBUILT** — there is no mechanism to diverge from. Phase 2's own
self-review deferred the consented yes-branch to "the continuation layer" (freeflow/LLM judgment),
and this fixture mechanically proved that deferral left §5.5's consent path with zero deterministic
implementation, not merely an edge-case gap in an existing one.

## Verification (live repro, before filing)

Full-graph, `PSYCHOED_PATHWAYS_ENABLED=true`, category `1f` (chosen specifically to avoid the
`3c` weave confound — see the companion ticket): turn 1 `"do I have GAD"` (1f-t3, `formal_diagnosis`)
→ turn 2 `"yes"`. Observed: `psychoed_serve: None`, `skill_match_method: None`,
`psychoed_active_category: "1f"` (pathway persists, un-hijacked), `psychoed_gate_action: None`,
response is the stub LLM's fixed continuation reply (freeflow was reached and invoked). Confirmed
`resolver.resolve()`'s active-category `_match_menu_label` call against `"yes"` returns no hit for
any of `1f`'s block `menu_label`s.

## The fix (not here)

**Definition of done (ruled):** implement through the EXISTING serve path — a "yes" reply (while a
formal_diagnosis guard question is the most recent psychoed turn) resolves to the relevant concept
block and transits the SAME audited path any other serve does (composed via `serve.py`, verified by
`output_gate`'s psychoed hash gate, `psychoed_blocks_served` appended) — **no new mechanism class**.
This likely requires a new state channel analogous to `offered_skill_ids`/`offer_response`
(e.g. something like `psychoed_diagnosis_guard_pending` + the block/category it should resolve to
on consent), wired into `skill_select.py`'s psychoed block ahead of the ordinary resolver call.
Needs its own branch and normal review cycle — this is a safety-adjacent surface (diagnosis
guard-rail content), never a drive-by fix on a fixtures branch.

**Named flip consideration:** the `formal_diagnosis` route itself (both this gap and the sibling
`resolver-pick-block-unconditional-false-mismatch.md` bug) should register as a flip-precondition
note for whichever category first goes live with a `formal_diagnosis`-routed trigger row — lands at
Task 10 (baseline measurement / flip-readiness register), not decided here.

**Definition of done includes the fixture re-pin.**
1. `F10-004`'s strict xfail (`tests/fixtures/psychoed/f10_diagnosis.jsonl`,
   `pytest.mark.xfail(strict=True)` gated on this ticket path) turns **xpass** when the fix lands,
   which fails CI loudly and forces the re-pin.
2. Re-pin `F10-004` to assert the SPEC-INTENDED outcome directly (audited block serve:
   `skill_match_method == "psychoed_resolver"`, `psychoed_gate_action == "pass"`,
   `psychoed_blocks_served` grew), removing the xfail marker.
3. `F10-004b` (the interim quarantine-floor regression case: a "yes" reply must never leak psychoed
   block content into the continuation via a mis-ranked retrieval passage, even while the
   consent-to-serve mechanism is unbuilt) is **NOT retired by this fix** — it survives permanently
   as the continuation-turn quarantine regression case, since the new consent mechanism and the
   quarantine floor are independent properties (one is "consent should serve," the other is
   "absent consent, nothing must leak").
