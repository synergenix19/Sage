# Vee packet — KB retrieval: removing the approximate index, and where the abstain line should sit

**Date:** 2026-08-19 · **For:** Vee (clinical sign-off) · **Prepared by:** engineering
**Decision requested:** confirm or reverse the abstain threshold **0.58**
**Status of the number:** provisional engineering value. It does not serve until you sign it.
**Paired change:** cdai PR #512 (drop the approximate vector index). The two ship together or
not at all — see "Why these are one change".

---

## 1. What this is about, in plain terms

When someone asks Sage an informational question, Sage searches the knowledge base and either
(a) answers from an article it found, or (b) **abstains** — declines to answer from the KB
because nothing relevant was found. The abstain line is a single number: how similar the best
matching passage must be before Sage is allowed to use it.

Two things are in front of you:

1. We are removing a database index that was **silently losing the right answers**.
2. Removing it changes the similarity numbers across the board, so the abstain line has to move
   with it. That line is the thing that decides whether an off-topic question can pull back
   crisis content, which is why this is your call and not ours alone.

## 2. What was wrong

The index was an *approximate* one: to be fast, it only searched a fraction of the library
(1 shelf in 50) and returned the best thing it found there. At our corpus size that speed buys
nothing measurable, and it was costing us the right article.

Measured against production on 2026-08-19, over the 24-question set used for the August corpus
refresh:

| Question asked | What Sage does today | After the fix |
|---|---|---|
| "where can I get urgent mental health help in the UAE" | **finds nothing, abstains** | serves the crisis-resources article (0.780) |
| "what should I do in a mental health crisis" | serves a **self-compassion** passage (0.474) | serves the crisis article (0.772) |
| "I want to understand self-harm and how to get help" | serves a self-compassion passage | serves the self-harm article (0.760) |
| "how can I support a friend going through a crisis" | serves a crisis article ✓ | serves a crisis article ✓ |

Crisis article reaching the top three: **2 of 4 → 4 of 4**. General questions: correct topic
**11 of 12 → 12 of 12**.

The second row is the one we would flag to you even if nothing else were in this packet. Today
that question does not abstain — it **answers, with the wrong passage**. A person asking what to
do in a crisis receives self-compassion material. That is not a hypothetical.

## 3. What it costs, and why the line has to move

Removing the index raises similarity scores for *every* query, including ones that should be
refused. The old line (0.42) was calibrated while the index was suppressing those scores — so
keeping 0.42 after removing the index would leave the door open:

> "where can I find job platforms in the UAE" → would serve the **crisis-resources article**
> (0.544) instead of abstaining.

An off-topic question pulling back crisis content is the specific outcome the August refresh was
verified against, so the line must move in the same change.

## 4. Where we propose the line, and why 0.58

With the index removed, the two groups separate cleanly:

```
off-topic questions   ...........  highest scored 0.5444
                                    ^
                            proposed line: 0.58
                                    v
in-scope questions    ...........  lowest scored 0.6168
```

- Every off-topic question scores **at or below 0.5444**.
- Every question that *should* be answered scores **at or above 0.6168**.
- **0.58 sits in the middle of that gap** — 0.0356 of room on one side, 0.0368 on the other.

**Provenance of these numbers.** They were re-measured on 2026-08-19 *after* a corpus repair,
against a knowledge base verified complete: **52 of 52 articles matching their source files,
265 chunks, nothing missing or truncated**. An earlier run of the same measurement was taken
while the database was quietly missing one Arabic article and holding another in truncated form;
those numbers are superseded, and the band moved by less than 0.001 when measured against the
corrected data. You are being shown the corrected run.

At 0.58, on this question set:

- **8 of 8** off-topic questions correctly abstain.
- **16 of 16** in-scope questions (12 general + 4 crisis) are correctly answered.

For contrast, with the index still in place that gap is only 0.015 wide (0.486 vs 0.501) — there
is no line that separates the two groups cleanly. **Removing the index is what makes a
defensible abstain line possible at all.** That is the strongest argument for the change, more
than the speed or the tidiness.

## 5. What we are asking you to weigh

The number is engineering's; the *judgement* is yours:

1. **Is mid-gap the right posture?** 0.58 balances the two error directions evenly. If you judge
   that one error is worse than the other, the line should move, and we will move it:
   - **lower** (nearer 0.55) → Sage answers more often, abstains less; more risk of serving
     something loosely related to an off-topic question.
   - **higher** (nearer 0.61) → Sage abstains more readily; more "I don't have information on
     that" on questions we could have answered.
2. **One topic outside this question set falls below the line.** All 16 in-scope questions in
   the set above are answered at 0.58. Separately, in our retrieval test fixtures, "what is
   exposure therapy" scores 0.450 — the corpus has no exposure-therapy article, and the nearest
   passage is a general therapy one. At 0.58 that question would abstain. We read that as
   *correct* (Sage should not answer from material that only looks adjacent), but it is a
   **content gap** for the authoring list rather than an argument about the threshold.
3. **This number has an expiry.** It was calibrated at the current corpus size. When the AR
   content lane lands, the distribution changes and 0.58 must be re-verified against this same
   question set. We have written that condition into the migration so it cannot be forgotten.

## 6. What is NOT changing

- No article text, no crisis copy, no helpline numbers. The single-source crisis resources
  (800-HOPE) are untouched.
- The crisis-detection path (S1/S3, the crisis card) is a **separate** surface and is not
  affected by any of this. What is in front of you is the *knowledge-base* path — a person
  asking an informational question — which is a secondary crisis surface, not the primary one.
- No change to what Sage says when it does abstain.

## 7. Honest caveats

- Measured on **English** only, on 24 questions. The Arabic side is measured only as far as the
  three AR questions in that set, and the AR corpus is separately mid-refresh.
- The 24-question set is a sample. We found that which questions the old index answered well was
  substantially arbitrary — the same article was reachable by one phrasing of a question and
  unreachable by another. So the *measured* failure rate understates the real one.
- Separately, and now resolved: the knowledge base had been quietly missing one Arabic article
  (`anxiety-001-ar`, on anxiety — a core clinical topic) and holding another in truncated form
  (`wellbeing-001-ar`, 1 of 4 sections), caused by a deploy-time sync defect. Neither is a crisis
  article. **Both are repaired and verified**, with the correct approved citations, and the
  numbers in this packet were re-measured afterwards. A detection check now runs after every
  sync so the same silence cannot recur. Noted here because it is the reason you may see two
  different corpus sizes in surrounding records (258 vs 265).

## 8. Sign-off

| | |
|---|---|
| Threshold **0.58** — confirm / reverse / amend to: | ☐ |
| If amended, value and reason: | |
| Index removal (PR #512) — noted / objection: | ☐ |
| Re-verification on AR corpus growth — agreed: | ☐ |
| Date / signature: | |

Nothing here reaches users until this sheet comes back and the owner gives a separate deploy
instruction.
