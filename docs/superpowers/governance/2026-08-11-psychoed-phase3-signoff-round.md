# Psychoeducation Pathways — Phase 3 Sign-off Round (for Vee)

**Requested turnaround:** ______ (three items below are URGENT — they gate everything else)
**How to use this sheet:** each item is self-contained. Mark one box, add edits inline under
"Your answer." Nothing here approves a deployment or turns anything on for users — serving
remains mechanically blocked in CI until named engineering items resolve AND your signatures
below land. You are signing the named things only.

**Context in one paragraph (the measurement result this round prices against):**
The Phase-3 measurement produced our most consequential product number: naturalistic recall
of the psychoed pathway is 0/61 at both measurement tiers. The recognition layer is doubly
gated. Gate one is the trigger tables: real users phrasing naturally essentially never hit
doc-verbatim phrases, so the deterministic pathway's naturalistic reach is currently zero —
that is the floor under your F1 bar (item 2) and moves the block-hints addendum (item 3)
from routine to priority. Gate two is an engineering defect, not a product characteristic:
36% of even doc-verbatim phrases currently can't reach the matcher because transit depends
on the intent classifier — ticketed HIGH against the ruled design and being fixed, not
accepted. Read reach-after-fix as table coverage alone; that is what your bar should price.
Misses degrade to today's behavior in every case — the safety analysis is unchanged.

---

## URGENT ITEMS

### 1. AR validator — name the validator (URGENT: first domino for everything Arabic)
Nothing Arabic can be graded, signed, or served until a named clinical validator owns the
AR chain. All AR fixture rows are marked draft-pending-validator and are excluded from
every coverage count until this name exists.
**Your signature means:** the named person (or explicit deferral with a date) owns AR
clinical validation.
☐ NAME: ____________________  ☐ DEFERRED until: ______  ☐ Discuss
**Your answer:**

### 2. F1 acceptance bar (packet ask 11) — set the bar against the measured floor (URGENT)
You are setting the naturalistic-recall bar the pathway must clear before serving. Price it
knowing: today's floor is 0/61 (designed-honest baseline of a phrase-matching v1); the bar
applies to the FLIP-TIER number (real classifier, prod parity), never the CI number; and
after the reachability fix, reach = trigger-table coverage alone.
**Your signature means:** the pathway may not serve a category until flip-tier naturalistic
recall for it meets your number.
☐ BAR: ______ %  ☐ Different shape (describe below)  ☐ Discuss
**Your answer:**

### 3. Block-hints addendum — per-phrase block hints for answer-first categories (URGENT)
The recognition gap above is closed clinically (better trigger coverage / ratified hints),
not by loosening matching. This asks you to author/ratify per-phrase block hints; fixture
rows carrying re-pin markers re-pin automatically when your hints land.
**Your signature means:** the hint set you return is ratified content; we re-pin
expectations to it.
☐ APPROVE (hints attached/route to me)  ☐ EDIT  ☐ Discuss
**Your answer:**

---

## STANDING RATIFICATIONS (from the build; each is live-in-code but flag-OFF)

### 4. The 40 content blocks + scripts, as transformed (em-dash diffs)
The ratified source was transformed (em-dash removal, formatting) for serving. The diffs
doc→served-artifact are the evidence; no wording changed beyond the ruled transformation.
**Your signature means:** the served copies are your ratified copies.
☐ APPROVE  ☐ EDIT (list blocks)  ☐ Discuss
**Your answer:**

### 5. Deflection→crisis (design-added extension to the screening weave)
Your doc's weave branch was binary yes/no. As built, a DEFLECTION of the screening question
("actually, what is anxiety?") escalates like an ambiguous reply — fail-closed. This was
design-added and needs your ratification.
**Your signature means:** deflection-escalates is clinically correct behavior.
☐ APPROVE  ☐ EDIT  ☐ Discuss
**Your answer:**

### 6. Collision winners — including the new six-wide question
Two phrases live in multiple categories ("Why do I feel numb?" 3c/s2c; "What's happening to
me?" 1f/3c — currently 3c interim). Your pairwise defaults were ratified when only pairs
could collide; with all six categories armed the same defaults now win six-wide, and
measurement confirmed they do. Also standing: the weave-dominance rule (weave question,
full stop — nothing shares that turn).
**Your signature means:** the declared winners (incl. six-wide) and the interim 3c defaults
are your call; the resolver changes only if your winners change.
☐ APPROVE as declared  ☐ EDIT winners (specify)  ☐ Discuss
**Your answer:**

### 7. §7c reclassification (ruled amendment) — confirm
Previously ruled; this confirms your sign-off on the reclassification as recorded in the
design spec's register.
☐ CONFIRM  ☐ REOPEN
**Your answer:**

### 8. Human-referral close — authorship
The referral close copy needs a named clinical author (it is served verbatim on referral
paths).
☐ I AUTHOR (attached/route to me)  ☐ APPROVE current draft  ☐ Discuss
**Your answer:**

### 9. Classifier A thresholds (acute-distress suppression)
The thresholds that suppress psychoed serving when acute distress co-occurs with a trigger
hit (lexical/structural/numeric/upstream-state classes). Measurement confirmed each class
fires genuinely (verified hit-plus-veto, not phantom matches).
**Your signature means:** the suppression thresholds are clinically placed.
☐ APPROVE  ☐ EDIT (specify class)  ☐ Discuss
**Your answer:**

### 10. Guard-script body/close segmentation (the two-question ruling)
Ruled fix for two findings with one cause: the diagnosis-guard's consent close and a
category's framing question were creating two-question turns colliding with the screening
weave. Fix is composition: your stage-1 script splits into body/close FIELDS — zero wording
change — so exactly one question owns any turn. Because it segments signed copy, the split
itself needs your ratification.
**Your signature means:** the field split of your ratified script is approved (wording
untouched).
☐ APPROVE  ☐ EDIT  ☐ Discuss
**Your answer:**

### 11. Consent-to-serve interim (formal_diagnosis walk-through) — acknowledge
Known interim, flip consideration: today a "yes" to the guard's walk-through offer is
answered by general conversation (safe; quarantine verified), not the ratified block. The
build ticket exists; any formal_diagnosis flip decision is made knowing this.
☐ ACKNOWLEDGED  ☐ BLOCK formal_diagnosis flips until built  ☐ Discuss
**Your answer:**

### 12. mindfulness_body_scan — deroute or sign
After MM's deroute, body_scan (also unsigned, no contraindications) absorbs the derouted
demand live. Same class, same decision needed: deroute it too, or sign it.
☐ DEROUTE  ☐ SIGN (review to follow)  ☐ Discuss
**Your answer:**

---

**Not asked here:** deploy approval (routine, nothing user-visible changes); any flag flip
(mechanically blocked in CI until the reachability fix lands AND items above resolve);
S2c anything (gated on the reunification-lexicon P0, escalated separately); AR anything
beyond item 1.
