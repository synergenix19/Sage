# AR-recall probe (TD5-forward)

Retrieval-relevance labels only (which corpus article answers a factual query),
NOT clinical-safety judgments. Synthetic harness asset under POC data-sovereignty
rules — engineering-authored, not clinical sign-off gated. Native-Khaleeji review
is the upgrade path toward true TD5.

Schema per row: query, gold_article_ids[], relevance_judgment, dialect_tag
(khaleeji|msa|en|ar), variance_type (orthographic|lexical|baseline|negative).

variance_type classifies KHALEEJI queries by what the rewriter can reach; MSA rows
are the regression baseline:

- orthographic (khaleeji): differs from corpus text only by Alef/Ta-marbuta/tatweel —
  within the v1 rewriter's reach. Expected: lift, or at minimum no loss.
- lexical (khaleeji): differs by dialect vocabulary — needs post-POC CAMeL/translation;
  results are REPORTED, not gated.
- baseline (msa): standard MSA phrasing, the no-regression control. Never tag MSA rows
  "orthographic" — it pollutes the split.
- negative (en|ar): clearly off-domain queries with no relevant corpus answer.
  `gold_article_ids: []` and `relevance_judgment: "none"` always. Correct retrieval
  behaviour is abstain=True, not a recall/MRR score — these rows are first-class
  TD5 negatives and partially unblock Item #2's negatives condition. Kept on
  `dialect_tag: en|ar` (not khaleeji/msa) since off-domain intent, not dialect
  variance, is what's being tested.

Bucket-to-acceptance mapping: msa/baseline = no regression; khaleeji/orthographic =
expected lift; khaleeji/lexical = reported only; en/negative + ar/negative =
abstain rate, evaluated via `scripts/negatives_smoke.py` and
`cosine_distributions()`, not `recall_at_k`/`reciprocal_rank`.

Khaleeji rows seeded from authored skill triggers where an info-request framing
exists (see plan Task 6 Step 1); net-new phrasings authored only for uncovered needs.

## Row count and provenance (this fixture: 40 rows / 14 info-needs + 12 negatives)

14 info-needs, each present as one khaleeji row + one msa row, covering 14 of the
21 articles in `data/knowledge_corpus/ar/`. Per-row provenance:

| article_id | khaleeji variance_type | source |
|---|---|---|
| anxiety-001 | lexical | authored: `psychoed_anxiety.json` target_presentations |
| anxiety-002 | orthographic | net-new |
| depression-001 | lexical | authored: `psychoed_depression.json` target_presentations |
| depression-002 | orthographic | net-new |
| stress-001 | lexical | authored: `psychoed_stress.json` target_presentations |
| stress-002 | orthographic | net-new |
| cbt-001 | lexical | brief's illustrative Step-2 pair (gold ids corrected, see below) |
| assertiveness-001 | lexical | net-new, grounded in `assertive_communication.json` trigger "تواصل حازم" |
| mindfulness-001 | orthographic | net-new |
| self-compassion-001 | lexical | net-new, grounded in `self_compassion_break.json` topic |
| grief-001 | lexical | authored: `grief_loss.json` target_presentations |
| gulf-001 | lexical | net-new (no skill models this topic directly) |
| values-001 | lexical | authored: `values_clarification.json` target_presentations |
| wellbeing-001 | orthographic | net-new |

9 lexical + 5 orthographic khaleeji rows + 14 msa/baseline rows = 28 recall rows,
plus 12 negative rows (6 en/negative + 6 ar/negative, added Task 4 of the
2026-07-03 abstain-cosine-gate plan) = 40 total.

Most authored Gulf-dialect triggers in the skill JSONs (e.g. `شو`, `وش`, `ليش`,
`شلون`) are lexical substitutions for MSA question words (`ما`, `ماذا`, `لماذا`,
`كيف`), not spelling variants — so the orthographic bucket is necessarily net-new:
it targets the specific failure mode the v1 rewriter (`rewriter.py`) fixes (Alef-hamza
forms `أ/إ/آ → ا`, Ta-marbuta `ة → ه`, tatweel `ـ` strip), which is a casual-typing
phenomenon orthogonal to dialect.

## gold_article_ids: real chunk ids, not article-family shorthand

Each corpus article is split into multiple chunks at ingestion
(`sage_poc/knowledge/ingestion.py::chunk_text`, ~75-word sentence-boundary chunks).
None of the 21 Arabic articles are `is_crisis_content`, so all are chunked (3-5
chunks each) — there is no single-chunk `"{article_id}-ar"` row in the DB for any
of them. `gold_article_ids` therefore lists every chunk id belonging to the
relevant article (e.g. `cbt-001-ar-000` .. `cbt-001-ar-004`), computed offline via
`chunk_text()` against the current `data/knowledge_corpus/ar/*.json` content (no
DB or embedding call needed — `chunk_text` is pure text splitting). `recall_at_k`
treats `gold_article_ids` as an OR-set ("any gold id in the top-k"), matching the
README's framing: relevance is at the *article* level, not a specific chunk.

This diverges from the task brief's illustrative 2-row example
(`gold_article_ids: ["cbt-001-ar"]`), which does not match any real row in the DB
given the current chunking (`chunk_text` splits `cbt-001-ar` content into 5
chunks). Using the article-level shorthand would make recall permanently 0
regardless of retrieval quality. If the corpus is re-ingested with different
content (changing chunk boundaries), re-run
`scratchpad/gen_probe_fixture.py`-equivalent logic (recompute via `chunk_text`)
before trusting these gold ids.
