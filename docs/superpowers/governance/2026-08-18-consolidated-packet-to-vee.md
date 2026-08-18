# Consolidated packet to Vee — §3a records + measurement (2026-08-18)

**Route:** PO relay, per house convention.
**Relay recommendation (owner, 2026-08-18): walk Vee through this packet LIVE, not async.**
Item 2 is the reason: "eight of your signed rules read as unsigned because of a duplicate
JSON key" is most likely to be misread in isolation — it is a question about a file-format
artifact, **not** an assertion that her sign-off record is corrupted — and her answer to it
may reframe how she reads items 1, 3 and 4. Open with item 2's framing, then take the rest
in order.
**Form (owner direction, 2026-08-18):** every item arrives **pre-answered from the git
record** — timeline, signing commits, and approval-sheet references — with a concrete
recommendation, so each ask is a one-tick confirm (or edit), never open-ended research.
**Why one packet:** four queued items share context (the §3a oracle, its harness, and the
safety-rule record); bundling them lets Vee rule once with the full picture instead of three
trickles. Each item carries its evidence SHA. Items 1, 2 and 3 are **record questions**
(what did you actually sign / how should the signed record read); item 4 is **information
feeding a design decision** (the F5 detector rebuild) — no engineering change ships on any
of these before her words come back.

**Evidence anchors:**
- Corrected §3a harness run of record: `fix/p2-instruments` @ `0775682c`
  (`evidence/2026-08-18-3a-harness-rerun.txt`), executed from `feat/low-mood-3a-impl`
  @ `d2c40704` with the fixed instrument (config stamp: effective V2, reranker fp32,
  exemplar anchors; oracle blob `46199ded`).
- Signed oracle: `src/sage_poc/rules/data/safety/low_mood_3a_triggers.json`
  (blob `46199ded`, `_meta.status`: SIGNED by clinician (Vee), 2026-07-10).
- Safety-rule files (item 2): `crisis_keywords.json` blob `8152919c`,
  `passive_si_patterns.json` blob `265924d5` (both `origin/master` @ `c0f66e49`).

---

## Item 1 — `_meta.match` in the signed §3a oracle describes a matcher that does not exist

The signed JSON's `_meta.match` reads (verbatim excerpt):

> "Matching code lives in nodes/low_mood_detect.py: family/token-aware, deterministic, no
> LLM. … the code additionally generalizes a few families (energy scope, numb/flat
> subject-anchoring, motivation object-generic checks) so paraphrases in the same family
> still fire…"

The shipped code is the 10-substring minimal placeholder (the 231-line family/token-aware
matcher was **rejected on adversarial review** and reverted in `055f4516`; the module's own
header NOTE records this). So the signed record describes a mechanism the running system
does not have.

**What the history shows (pre-answered):** the prose was true for exactly twelve minutes.
`30de34cc` (2026-07-10 00:48) wrote `_meta.match` describing the family/token-aware matcher
it shipped; `055f4516` (01:00) reverted the matcher on adversarial review but did not touch
the JSON; the signing commit `f1bb1b52` (02:57) carried the already-stale prose forward. So
this is a record-maintenance correction of text that was stale at signing through an
engineering revert — not a signing error, and not a question about what Vee approved
(her sign-off was R1–R7 + CD1–CD5, the vocabulary and criteria, which are untouched).

**Recommendation — proposed replacement `_meta.match`, for one-tick approval:**

> "Matching code lives in nodes/low_mood_detect.py: MINIMAL PLACEHOLDER — deterministic
> substring match over the 10 patterns in that module, input normalized via
> rules/normalize.normalize_text (no LLM). The family/token-aware generalizing matcher
> previously described here was rejected on adversarial review (13.3% novel recall / 20%
> novel FP) and reverted in 055f4516 before this file was signed. Robust §3a detection is
> a pending redesign (semantic recall + clinician-owned precision gate); the deterministic
> crisis-firing guarantee stays on safety_check's SI-answer catch. This file is the
> clinician-owned vocabulary source and the SIGNED eval oracle. Do NOT add trigger
> vocabulary beyond list A here."

**Asked of Vee:** approve the replacement wording above (or edit it) — the signed artifact
is never edited without her word.
**Not asked:** any change to the 39 trigger phrases or the lookalike lists.

## Item 2 — duplicate `approved_by` keys: which is the true record?

Eight active safety rules carry **two** `approved_by` keys in the same JSON object —
`"clinical_lead"` first, `null` second. JSON last-key-wins, so the parsed value is `null`,
and the loader logs all eight as **UNAPPROVED ACTIVE** on every boot:

- `crisis_keywords.json`: SK-EN-003, SK-EN-004, CK-CH-001, CK-CH-002, SK-EN-006
- `passive_si_patterns.json`: SK-AZ-002, SK-AR-003, SK-EN-005

These eight are exactly the rules on the approved_by governance burn-down.

**What the history shows (pre-answered — the determination is in the record):**
commit `f4ed6740` — "clinical(GOV-270): sign all 16 active safety rules (clinician-approved
2026-07-15)" — recorded the clinical lead's ratification per the GOV-270 approval sheet
(`docs/escalations/2026-07-15-270-approval-sheet.md`, landed in `ea49af17`, merged via
PR #323). Its diff **inserted** `"approved_by": "clinical_lead"` as a new first line in each
rule object **without removing the scaffold `"approved_by": null`** already present further
down — so JSON last-key-wins silently discarded each signature the moment it was recorded.
All eight flagged rules are inside GOV-270's enumerated sixteen (CF-001..004, CK-CH-001/002,
SK-AR-001/003, SK-AZ-001/002, SK-EN-001/003/004/005/006, SK-EN-HTO-001). The other eight of
the sixteen were subsequently cleaned by unrelated edits (e.g. `bed4260e`,
`d9b978b1` — SK-EN-HTO-001 deliberately manifest-signed instead); these eight are simply the
ones where the scaffold null survived.

**Recommendation, for one-tick approval:** the true record is **SIGNED — all eight**
(`clinical_lead`, GOV-270 approval sheet, 2026-07-15). Engineering deletes the surviving
`null` key from each of the eight (one commit, no other change), the loader's
UNAPPROVED-ACTIVE warnings clear, and the approved_by burn-down closes entirely as a
mechanical artifact of the signing commit.

**Asked of Vee / PO:** confirm the GOV-270 record covers these eight as history shows (or
name any rule whose sign-off she considers open despite it).
**Not asked:** any judgement on the rules' clinical content.

## Item 3 — CD3/R4 tiering: the denominator question (no gate pressure)

The corrected harness run of record measured, against the signed 39-phrase oracle:

- **JOINT recall 0.615 (24/39)** — pre-registered gate ≥ 0.90: **FAIL**
- **FP 0.200 (3/15)** — pre-registered gate ≤ 0.00: **FAIL**

The oracle's own `_meta.status` says: "Apply on next iteration: CD1 tiering … and CD3/R4
exclusions (I feel numb / I feel stuck / I don't feel like myself EXCLUDED from
BA-enrichment, cross-category)." Three of the fifteen misses are exactly those CD3/R4 items.
Under that proposed exclusion the derived figure is 24/36 = **0.667 — presented as an
annotation only, not adopted**: the signed 39-phrase denominator governs, and the
pre-registered gate was registered against it. Changing the denominator is a clinical-scope
decision that belongs to Vee alone (the same rule as item 1).

**Critically: the tiering question is moot for the gate verdict.** Recall fails ≥ 0.90 on
either denominator (0.615 and 0.667 both fail), and FP 0.200 fails ≤ 0.00 independently.
Her tiering call can be made on clinical merits with zero pressure that it flips a verdict.

**What the history shows (pre-answered):** the "Apply on next iteration" sentence entered
`_meta.status` in the signing commit itself (`f1bb1b52`, 2026-07-10) — it is **Vee's own
recorded instruction at signing**, not a new proposal. Confirming it is executing her
recorded direction, not making a fresh clinical call.

**Recommendation, for one-tick approval:** apply the tiering as she instructed on 2026-07-10
— the CD3/R4 exclusions (and CD1 tiering) take effect for the oracle's next iteration, so
the denominator for future measurements is 36; the 2026-08-18 result stands as measured on
the signed 39.

**Asked of Vee:** confirm her recorded 2026-07-10 instruction still stands (or revise it).
**Not asked:** any revision of the 2026-08-18 result — it stands as measured on the signed
oracle either way.

## Item 4 — the harness FAIL motivates the F5 detector rebuild (design premise, for context)

The corrected measurement establishes citably what the rebuild plan assumed: **joint
keyword + semantic routing does not clear the R7 bar** (0.615 / 0.200 vs ≥ 0.90 / ≤ 0.00),
and per the in-code redesign note the intended architecture is **semantic recall
(BA-offerable) + a clinician-owned precision gate**, with the deterministic crisis-firing
guarantee staying on safety_check's SI-answer catch. One of the three FPs is keyword-tier
("didn't sleep well so I've no energy today" → target_presentations), scoping that leak to
a targeted lexicon fix, not a classifier.

**Why it is in this packet:** Vee's answers to items 1–3 — the corrected `_meta.match`
wording, the denominator, and the shape of her precision gate — define F5's target before
implementation starts. F5 does not begin against an unanswered packet.
**Not asked:** approval of any implementation; that returns as its own decision request
with the rebuild's measured evidence, through the fixed harness only.
