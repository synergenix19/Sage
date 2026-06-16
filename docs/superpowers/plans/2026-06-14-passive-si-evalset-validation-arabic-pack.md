# #18 Eval Set — Clinician Validation + Arabic/Arabizi Expansion Pack

> **Status:** DRAFT clinical-authoring spec. Touches nothing live. This is the FOUNDATION S2/MARBERT
> trains and is evaluated on — it must be confirmed data, not 27 first-pass cases, before the build.
> **Surface:** CRISIS. Clinician (native Khaleeji for AR/AZ) authors/validates; clinical sign-off on scope.
> **Sequencing:** this pack is the dependency for the S2 build plan
> (`2026-06-14-s2-marbert-build-plan.md`). Validate here first; build on confirmed data.

## 0. Why this comes first
The first-pass run (`scripts/passive_si_s3_precision.py`, 27 EN cases) was enough to **refute** "S3 is
redundant" (S3 marginal recall 5/15) but is a **weak estimate of the overlap geometry**, and the
**Gulf-Arabic / Arabizi buckets are empty**. S2 is only as good as this set. Two settled outputs
depend on the expansion:
1. Settle whether a high-recall threshold can trim the worst S3 FPs without dropping real SI
   (currently "looks unlikely, not proven" — needs a larger, validated sample).
2. Give S2 a bilingual train/eval foundation — especially Arabic, the highest-risk path.

## 1. Part A — validate + expand the English set
- **Clinician review the existing 27 labels** in `tests/fixtures/passive_si_eval/eval_en.jsonl`
  against the 3-bucket definitions; correct any mislabels (esp. borderline "burden"-type cognitions,
  which were deliberately EXCLUDED from the first pass as clinician-call territory).
- **Expand each bucket** to a target size set with the clinician (recommend ≥40 per bucket: passive_si
  / distress_not_si / cooccurring) so the FP-vs-TP score geometry is estimable, not anecdotal.
- **Bucket definitions (confirm/adjust):**
  - `passive_si` (expected_crisis=true): passive ideation the system MUST catch — "no reason to keep
    going", "tired of being alive", "wish I could disappear". No active-method content (that's a
    different, higher tier).
  - `distress_not_si` (expected_crisis=false): low self-worth / hopelessness-adjacent that is NOT SI —
    "I feel like a failure", "worthless", "not good enough". This is the FP class.
  - `cooccurring` (expected_crisis=true): the distress phrase EMBEDDED with passive-SI — the
    load-bearing edge that exposed the unsafe exclusion (`cooc-en-03`).

## 2. Part B — author the Gulf-Arabic + Arabizi buckets (highest-risk, native-Khaleeji clinician)
This is the riskiest gap, for two compounding reasons:
1. **S1 is the SOLE detector on AR/AZ** — `safety_check.py:128-134` documents that S3 (BGE-M3) does
   NOT generalize at threshold for Arabic idioms (0.70–0.74) or Arabizi (0.39–0.81). So on the Arabic
   path there is no semantic backstop; the keyword lexicon is load-bearing.
2. **The MT step can SILENTLY DROP the SI signal.** Arabic input is translated to English
   (`safety_check.py:89 async_translate_to_english`) before some checks. A Gulf idiom carrying passive
   SI can translate to bland English that neither S1-EN nor S3 flags — a silent miss.

**Therefore the Arabic eval MUST test the RAW path, not just the translation.** For each AR/AZ case
record and measure separately:
- `text_ar` / `text_raw` (verbatim) → S1 Arabic/Arabizi keyword rules (the real production path).
- the MT output (AR→EN) → does the SI survive translation? Flag any case where SI is present in AR
  but absent after MT ("MT-dropped-SI") — these are silent-miss candidates and a finding in their own
  right, independent of S2.

**Deliverables:** `eval_ar.jsonl` and `eval_az.jsonl` in the SAME schema as `eval_en.jsonl`
(`{id, text, lang, bucket, expected_crisis}`), native-Khaleeji authored, same 3 buckets, ≥30 per
bucket where feasible. Gulf dialect specifics (not MSA), including the supplication/idiom forms that
the existing FPE-AR entries hint at (e.g. frustration idioms that are NOT SI vs genuine passive SI).

## 3. Part C — re-run + settle the open question
After validation + expansion, re-run `scripts/passive_si_s3_precision.py` (extend it to load the AR/AZ
files) and report, per language per bucket: S1 recall, S3 marginal recall over S1, S3 precision, the
MT-dropped-SI count, and the **FP-vs-TP score histograms** so the threshold-separability question is
answered from a real sample. This is the data the S2 plan stands on.

## 4. Governance & boundaries
- Synthetic eval phrases are test assets, not clinical-population data ([[data-sovereignty-test-harness]]);
  any external corpus needs clinical sign-off before merge ([[test-content-guardrails]]).
- Any Judge/LLM used to help label must be calibrated vs the human rater before its labels count.
- **Do NOT lower `S3_THRESHOLD`; do NOT prune S1 keywords** (S1 is the only AR/AZ detector).
- **Design invariant:** high-recall posture holds; this set measures precision but never licenses a
  change that lowers recall below current S1∪S3.

## 5. Sign-offs
- [ ] EN label validation + expansion scope — clinician: __________  date: ______
- [ ] Gulf-AR + Arabizi bucket authoring — native-Khaleeji clinician: __________  date: ______
- [ ] MT-dropped-SI findings reviewed (any silent-miss → own remediation) — clinician + eng: ______
