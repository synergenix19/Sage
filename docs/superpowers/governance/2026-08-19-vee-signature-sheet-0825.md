# Vee signature sheet — 2026-08-25 (consolidated, one pass)

Everything below awaits your word on 2026-08-25 (or your earliest slot). Each item:
what you are approving in one sentence, where the full artifact lives, the operator
recommendation, and an approve-as-is line you can initial. Recommendations from
engineering are OPERATIONAL (ratify the conservative default already encoded, or the
staged artifact as built); every clinical boundary inside them remains yours to amend.
Items 7–9 belong to other lanes and are listed so this is the ONLY sheet in the
walkthrough; their asks are unchanged from their own documents.

**Change freeze is in force:** production and every staged surface are exactly as
described here — what you rule on is what is running / what will run.

---

## 1. Means-access rehearsal surface (packet item 1 · staged: PR #470, draft)

**Approving:** an AMENDMENT TO THE SPEC'S CANONICAL TRIGGER TABLE (C §0 — "This table
is the canonical list"): a new behavioral-sign row for means-access rehearsal phrasing
("took out my old pills and counted them"), firing crisis deterministically, including
mid-skill; with the must-NOT-fire exclusions (disposal, adherence, third-party custody).
Tier consequence: fires T2 via your signed `s1_any` tier rule, like every S1 flag.
Clinical basis inside the protocol itself: C §2's permitted safety question IS
means-access assessment ("Do you have access to something you could use to hurt
yourself?" — "standard means-restriction safety practice"); this surface escalates when
a user volunteers the affirmative answer unprompted. Today the table has no behavioral
class at all — that absence is the measured zero-affect gap.
**Full text:** `2026-08-18-vee-packet-means-access-cardiac.md` item 1; build on PR #470.
**Recommendation:** approve scope + both fixture sets as staged. Two boundary calls
flagged for you inside: (a) "counted out" is excluded (adherence reading) — a rehearsal
phrasing using "counting out" would be missed; (b) AR patterns are inactive PROPOSED
slots pending native-speaker authoring (recorded as a gap, not coverage).
**Condition on merge:** your signature value fills `approved_by` on the rules (left
null deliberately — no fabricated sign-off).

> APPROVE ITEM 1 AS STAGED: ______  · amendments: ______

## 2. Cardiac disposition re-sign as a phrasing-class (packet item 2)

**Approving:** re-signing the #413 cardiac escalation against the spec's OWN enumerated
family — the "⚠ Universal red-flag override (applies at every tier)": chest
pressure/heaviness, "crushing"/"stabbing"/"searing" chest pain, pain spreading to
arm/jaw/back, one-sided numbness/weakness — plus §1c's guard distinction "real
inability to breathe rather than panic-related breathlessness", which is the
NOT-boundary ready-made (panic breathlessness must not auto-escalate). Measured live:
the signed wording fires, a plain paraphrase does not. The disposition itself
(escalate_crisis) is already ruled (#413); this re-sign is the phrasing-class only.
**Full text:** packet item 2.
**Recommendation:** approve the class-based re-sign with the fixture-independence
requirement (eval fixtures are paraphrases, never the surface's own strings). You name
the class boundary: what somatic-panic phrasing must NOT auto-escalate (§1c's two open
presence cells sit adjacent).

> APPROVE ITEM 2 (re-sign as class): ______  · class boundary notes: ______

## 3. S4b self-worth FP exclusion (packet item 3 · staged: PR #471, draft, flag OFF)

**Approving:** a protective exclusion so deservingness framings WITHOUT existence
content stop drawing the crisis card (measured: stable across three windows). Spec
alignment is verbatim: "I don't deserve kindness" appears word-for-word in S4b §0's
deservingness-based-refusal trigger row — the false positive serves the crisis card
against the spec's own pathway-trigger vocabulary, so this exclusion protects the
spec's trigger table. The counter-set — deservingness + death/absence ("I don't
deserve to be here / to exist", "better off without me") MUST STILL escalate — maps to
C §0's passive-ideation and burden rows and S4b's guard route (severe/safety-relevant →
3b's protocol). The counter-set is part of what you sign.
**Full text:** packet item 3 (including the coupling caveat added 2026-08-19).
**Recommendation:** approve as staged, WITH the coupling in view: "I don't deserve X, I
want to die" phrasings do not fire S1 today (negation-window defect, now in the Phase-1
epic), so this build's existence-boundary is currently the load-bearing protection for
that sub-class, and the kill-switch carries that weight until the window fix lands.

> APPROVE ITEM 3 AS STAGED (coupling acknowledged): ______  · amendments: ______

## 4. Third-party crisis reports — one reconciled ruling (packet-2 item 3, owner of
record · staged: dark build PR #466, `SAGE_THIRD_PARTY_DEFERENCE` OFF)

**Approving:** (a) the third-party response path itself — Layer-1-clean + third-party
signal delivers helper-support content instead of the first-person crisis script; (b)
the draft content `CC-EN-TP-001` (validate concern · ask-directly guidance · helpline
framed for the friend · helper-state check); (c) your two flagged questions: does the
HELPER enroll in post-crisis monitoring, and does the crisis card show on helper turns?
**Full text:** `2026-08-18-vee-packet-2.md` item 3 + the deference decision request
(PR #466). Riders from the conformance lane: the behavior is two-window stable, and
"he'd be better off dead" third-party shapes still fire the deterministic tier
(bypassing deference) — span-coverage completion follows your ruling.
**Recommendation:** approve the path and content as drafted; on Q1 (helper
monitoring), ratify the encoded default (enrolls = fail-toward-support). Q2 (crisis
card) is a REAL trade-off, not a rubber stamp: the card's first-person framing is part
of the original calibration error, so showing it beside helper-support content partially
recreates that error — but hiding it removes the helpline surface from the turn. Your
call between resource-visibility and framing-consistency; the encoded default (shows)
errs toward resources. Either way is a one-line reversal later.

> APPROVE ITEM 4 (path + content): ______  · Q1 helper monitoring: ______  · Q2 card: ______

## 5. UNBUILT-row triage (packet item 5 — one line per row is enough)

**Approving:** a triage ruling for the 7 spec rows whose prescribed content was never
authored: §4a Emotions Wheel · §4b emotions psychoed · §5b Wins-Log · §7c connection
psychoed · S2c grief psychoed · S4a Kind Self-Talk · S4c Setbacks Guide.
**Recommendation:** default each to DEFER-TO-FULL-BUILD unless you want any for MVP or
formally descoped — deferral keeps the honest "UNBUILT" reporting line without
committing authoring time now.

> Per row (MVP / FULL BUILD / DESCOPE): §4a __ · §4b __ · §5b __ · §7c __ · S2c __ · S4a __ · S4c __

## 6. Arabic corpus ETA (packet item 6 — a date, not a signature)

**Asking:** an ETA (or the blocking constraint) for Khaleeji corpus batch-1 (#364, your
lane). The entire spec is unmeasured in Arabic; the AR baseline is the registered next
measurement trigger the moment the corpus lands.

> ETA / blocker: ______

## 7. Anger-with-harm Group-B patterns (canary lane — gates the 08-25 activation)

**Approving:** the pattern content for the NEW rule `SK-EN-HTO-002`. Precision on your
own record (2026-07-09 approval queue #2): you APPROVED Group A (explicit intent — live
and untouched, fires T2 via your signed `s1_any` tier rule), and ratified the HOLD on
the figurative Group-B list ("could kill him", "strangle", "could hurt him", "might do
something I regret") with the recorded reason that a deterministic lexicon
over-escalates figurative venting — your open ask was "rule Group B item-by-item".
**The new patterns are a THIRD class, not the held list:** ACTION-EVIDENCE of harm
proximity ("punched the wall next to her head" — physical acts near a person, no stated
intent, nothing figurative). Your recorded over-escalation concern is honored by
construction: the held figurative phrases sit in the canary's must-NOT-fire cells.
Activation runs the pre-committed 72h time-boxed canary
(`2026-08-18-219-canary-plan.md`: one must-NOT-fire trip = rollback, no averaging;
active probe cells at every checkpoint). Like Group A, HTO-002 fires T2 via `s1_any` —
signing includes that tier consequence.
**Recommendation:** sign the pattern set in the canary plan's cell definitions. This
guard is SPEC-MANDATED, not an extension: §4b's guard reads "anger with potential for
harm to self or others … is safety-relevant, not a neutral psychoeducation moment;
escalate appropriately." One judgment your signature resolves: the spec's examples are
stated-intent shapes ("I want to hurt someone"), while the live miss was action-evidence
without stated intent (wall-punch near a spouse) — covered by the guard's principle,
unreached by its examples. The must-NOT-fire wording (venting without harm content,
media references, idioms) is marked PROPOSED for exactly this signature.

> APPROVE SK-EN-HTO-002 (action-evidence) patterns: ______  · amendments: ______
> OPTIONAL — your still-open 07-09 ask, if you want it closed in the same pass, Group B item-by-item:
> "could kill him" __ · "strangle" __ · "could hurt him" __ · "might do something I regret" __ (blank = stays held)

## 8. Packet-2 items 1, 2, 4 (parallel lane — asks unchanged, listed for one walkthrough)

§3a oracle v2 signature + CD1 family tiers · the BA precision-gate content · the
`_meta.match` one-tick. Full text: `2026-08-18-vee-packet-2.md`.

## 9. P0 correctness batch — gated clinical items (parallel lane)

The P0 batch (`2026-08-18-p0-correctness-batch.md`) stages its clinician-path items
(derealization + panic/grief served-language changes) dark under the same DO-NOT-MERGE
convention; they join this walkthrough with their own asks per that plan.

---

**After your signatures:** #470/#471 merge with `approved_by` filled from this sheet;
the deference flag and SK-EN-HTO-002 activate per their plans (deploy owner executes);
the freeze lifts surface-by-surface as each signed item lands.
