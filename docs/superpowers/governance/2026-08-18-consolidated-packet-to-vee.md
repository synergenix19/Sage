# Consolidated packet to Vee — §3a records + measurement (2026-08-18)

**Route:** PO relay, per house convention.
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

**Asked of Vee:** confirm the corrected `_meta.match` wording (we will draft it to state the
placeholder mechanism + the pending redesign, for her sign-off) — the signed artifact is
never edited without her word.
**Not asked:** any change to the 39 trigger phrases or the lookalike lists.

## Item 2 — duplicate `approved_by` keys: which is the true record?

Eight active safety rules carry **two** `approved_by` keys in the same JSON object —
`"clinical_lead"` first, `null` second. JSON last-key-wins, so the parsed value is `null`,
and the loader logs all eight as **UNAPPROVED ACTIVE** on every boot:

- `crisis_keywords.json`: SK-EN-003, SK-EN-004, CK-CH-001, CK-CH-002, SK-EN-006
- `passive_si_patterns.json`: SK-AZ-002, SK-AR-003, SK-EN-005

These eight are exactly the rules on the approved_by governance burn-down — meaning the
burn-down may be partly an artifact of this JSON defect rather than genuinely missing
sign-offs. We cannot determine from the file alone whether `"clinical_lead"` reflects a real
recorded sign-off that a later edit clobbered, or was added in error against rules that were
never signed.

**Asked of Vee / PO:** the true-record determination per rule (signed or not), against
whatever primary sign-off records exist. Engineering then removes the duplicate keys to
match her answer — one commit, no content change beyond the key.
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

**Asked of Vee:** whether the CD3/R4 exclusion (and CD1 tiering) applies to the oracle's
next iteration, i.e. the denominator for future measurements.
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
