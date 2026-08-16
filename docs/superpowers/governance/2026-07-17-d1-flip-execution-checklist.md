# D1 enforce-flip — pre-registered execution checklist (#338)

**Written BEFORE the shadow window closes, so flip day reads a checklist, not decisions.** The
monitored-enforce window's opening mirror of the shadow window's. Every decision is already made and signed;
flip day is mechanical.

## Preconditions (all must be TRUE before flip begins)
- ▢ Shadow window CLOSED by rule: **N=40 TIPP turns** observed OR **14-day cap** reached
  (2026-07-17-d1-shadow-window-criteria.md), read reported WITH n.
- ▢ Shadow read PASSES: fire-rate in the 70–95% band, disclosure-population non-trivial, **zero**
  zero-tolerance breaches (no crisis-mishandle, no audit-swallow) during the window.
- ▢ Vee's two lines CONFIRMED (comma-swap bytes + RULING 3 split) — done 2026-07-17.
- ▢ serve/resume MERGED and DEPLOYED DARK (flag-off, byte-identical, already serving) — so flip touches zero
  code (recommended: land it in the shadow window, not at flip). GATE 0 addendum on the record.
- ▢ Mid-hold side-effect incidence (2026-07-17-d1-veto-mid-hold-side-effects.md) confirmed RARE in the
  window; if not rare, HALT flip and pull the veto-marker fix forward.

## Flip motion (mechanical — one flag + one migration against an already-serving tree)
1. ▢ **Apply migration 015** to prod (enforce audit columns) and VERIFY the columns exist
   (`screen_asked / screen_answer_class / screen_branch_taken`) — the same asyncpg verify used for 014.
   MUST precede the flag, or the enforce audit write fails on unknown columns.
2. ▢ **Claim the deploy lock** (deploy_prod.sh) even though it is flag-only — one-writer-to-prod, and the
   flag change triggers a redeploy.
3. ▢ **Flip** `SAGE_D1_SCREEN=true` (enforce). Leave `SAGE_D1_SCREEN_SHADOW` as-is (enforce wins; shadow
   branch is skipped when enforce on).
4. ▢ Wait for the redeploy to land; confirm serving SHA unchanged (flip touches no code) via /health/version.

## First-screened-turn behavioral probe (the flip's SG-2-seam-live check)
Drive one full screen cycle on prod, assert each hop:
- ▢ acute-overwhelm TIPP-routing turn → **question SERVED** (response present), and the served bytes
  **hash-match the manifest** `d1_screen_question_en` sha256 (the pinned, Vee-confirmed bytes reaching a user).
- ▢ answer each class, confirm the branch LIVE: `clear_no` → TIPP resumes; `contraindication_disclosed` /
  `yes` / `unclear` / topic-change → grounding (routed away); `red_flag` quality → 998 guard; crisis-in-answer
  → crisis path, hold abandoned.
- ▢ enforce audit row lands with `screen_asked` / `screen_answer_class` / `screen_branch_taken` populated
  (anonymised class+route, PDPL schema).
- ▢ a non-screen turn → row byte-identical to master (no screen columns).

## Monitored-enforce window (armed at flip)
- ▢ Answer-class distribution criteria ARMED (RULING 3, Vee-confirmed split): `unclear` dominance →
  wording returns to Vee before "verified."
- ▢ **Zero-tolerance halt rows** armed: any crisis-in-answer mishandled OR any audit swallow → **halt**.
- ▢ Read the answer-class distribution off the first N real screened turns (or fixed window, whichever fills).

## Halt lever (named, pre-authorized)
- ▢ **`SAGE_D1_SCREEN=0`** → proven dark state (serve/resume unreachable-with-flag-off is byte-identical to
  master, tested). Instant rollback, no code deploy. Held here.

## On verification
D1 verified → the **C1 revisit** returns to Vee: TIPP-leads becomes an honest question, because the screen
that guards it is real, measured, and signed at every layer (question bytes, branch table, activation).
