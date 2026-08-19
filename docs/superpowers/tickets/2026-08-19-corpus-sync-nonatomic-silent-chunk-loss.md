# Ticket (SAFETY-ADJACENT): corpus sync deletes before re-ingesting without a transaction — prod is serving a corpus with one AR article missing and one truncated

**Filed:** 2026-08-19 · **Status:** open, LIVE DEFECT — prod data is currently wrong
**Source:** AR chunk-delta diagnosis ordered as a pre-deploy gate on cdai PR #512 (drop ivfflat)
**Type:** data-integrity defect in the deploy-time sync path, not a content or chunker defect

## What is wrong in prod right now

Measured read-only against prod (`tcekehffneiqcdyhzobi`) on 2026-08-19, comparing every
corpus file's chunk output against the rows actually stored:

| article | expected chunks | in prod | lost |
|---|---|---|---|
| `anxiety-001-ar` | 4 | **0 — absent entirely** | 4 |
| `wellbeing-001-ar` | 4 | **1 — present but truncated** | 3 |

All 50 other articles match exactly. Corpus files are unchanged in git since the KB refresh
deploy (`cff64a1f`), so this is not an authoring change — prod diverged from the committed
corpus on its own.

The truncated article is the more dangerous of the two. A missing article abstains and is
therefore visible; `wellbeing-001-ar` **retrieves and serves a fragment**, and no surface
reports anything wrong.

## Reconciling the two prior numbers (this closes both)

- PR #457's post-deploy record: **262 chunks**. Today: **258**. Expected from files: **265**.
- 265 − 3 = 262: `wellbeing-001-ar` was **already torn at the #457 deploy**. The "AR
  depression-family stored chunks differ by 3 from current-chunker output" finding logged in
  that PR had the right magnitude and the **wrong article** — the AR depression family
  (`depression-001/002/003-ar`) matches its files exactly. It was never chunker drift.
- 262 − 4 = 258: `anxiety-001-ar` was lost **after** that verification, which explicitly cited
  `anxiety-001-ar-000` as live. That is new movement — corpus state changing with no record.

So: not "the known drift plus one". One misattributed tear, plus one new loss, one mechanism.

## Mechanism (characterized, not inferred)

`src/sage_poc/knowledge/sync.py`, `apply_sync`:

```python
for art in plan.to_ingest:
    await _delete_prefix(conn, chunk_prefix(art))     # commits immediately
    result.chunks += await ingest_article(art, pool)  # acquires a SEPARATE pooled connection
```

1. **No transaction wraps the pair.** The delete commits on its own.
2. **The re-ingest needs a different connection** (`pool`, not the held `conn`), so it can fail
   for reasons the delete never encounters — notably connection-pool exhaustion.
3. **Startup wraps the whole thing fail-open**, so serving continues on the damaged corpus.

Prod logs show the trigger firing, twice:

```
[sage/startup] corpus sync failed (retrieval will abstain):
  (EMAXCONNSESSION) max clients reached in session mode - max clients are limited to pool_size: 15
```

Delete commits → pool exhausted → re-ingest raises → loop aborts → the article stays deleted
until some later sync happens to succeed. `wellbeing-001-ar` shows the same failure landing
*mid-insert*, which is how an article ends up present-but-partial.

This is the same family as the warmup silent-failure finding: a background, fail-open path on a
clinical surface that degrades quietly and reports success upstream.

## Why safety-adjacent

Nothing here is AR-specific or crisis-specific — the mechanism is language- and
content-agnostic. Crisis articles are stored as **single whole-document chunks**, so the torn
mode for a crisis article is not truncation but **total disappearance** of `crisis-00X-en` from
the corpus, with retrieval abstaining and no alarm. That has not happened; nothing prevents it.

## Fix candidates

1. **Wrap delete + re-ingest in one transaction per article** (and let `ingest_article` accept
   the held connection instead of reaching for a second one). Removes the torn state entirely —
   an article is either its old version or its new one, never neither and never half.
2. **Post-sync integrity assertion**: after sync, compare stored chunk counts per article to the
   corpus files and log/alert on any mismatch. Cheap; would have caught both of these at deploy.
3. **Reconsider fail-open here.** Fail-open is right for *retrieval*; for a *mutation* that has
   already deleted rows, continuing silently is what turns a transient connection error into
   permanent data loss.
4. Separately: the `pool_size: 15` session-mode ceiling is being hit at startup at all — worth
   understanding whether sync should hold one connection rather than compete with the pool.

## Repair of current prod state

A successful sync run restores both articles from the committed corpus (content is intact in
git). That is a prod-serving mutation and belongs to the owner's deploy word — it should be
done deliberately and verified by re-running the integrity comparison, not left to the next
incidental restart.

## Related

- cdai PR #512 (drop ivfflat) — this diagnosis was its pre-deploy gate; #512's before/after
  evidence must rest on a corpus whose state is understood.
- PR #457 (KB refresh; the misattributed 3-chunk note lives in its post-deploy comment)
- Sibling class: warmup silent failure (WARNING + continue on a clinical path)
