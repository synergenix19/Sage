# To Vee — S2a grief tier (design question) + K6 sleep (clean leftover), one sheet

Two items, bundled into one touchpoint (rides alongside the reconciliation packet already in your court).

## 1. S2a fresh grief — a TIER question, not more keyword removals
K5 (approved: remove one over-broad grief keyword) shipped, but the guarded re-measure shows S2a stayed 0/5:
removing `someone died` wasn't enough because the five fresh-grief phrasings each match a *different* bare
death-announcement exemplar (`lost someone`, `passed away`, `my father died`, `death of a loved one`, …).
Picking them off one at a time would gut the exemplar list that **S2b (processing grief, skill IS prescribed)
legitimately needs**. So this isn't a keyword problem — it's a tier problem.

**The ruling (small, clinical, yours):** where does the line sit between fresh grief → *presence* (doc-prescribed
for S2a) and processing-stage grief → *skill-eligible* (S2b)?
- **Fresh death announcement → PRESENCE:** a raw statement of a loss — "someone I love died," "I've just lost
  someone," "my dad passed away," "someone close to me just died." Be present; do not push a technique.
- **Processing-stage → SKILL-ELIGIBLE:** help-seeking about living with the loss — "how do I cope with losing
  them," "I can't stop grieving," "I've been struggling since they died," "I don't know how to grieve."

If you approve that split, the fix is deterministic: the bare-announcement exemplars move OUT of `grief_loss`
(so fresh grief → presence), the help-seeking/processing exemplars stay IN (so S2b → skill). I'll sort the
current `grief_loss.target_presentations` into the two piles for your one-tick confirm, and the both-direction
fixtures assert fresh→presence AND processing→skill so neither regresses.
> ▢ approve the fresh-vs-processing split (I'll bring the exemplar sort for confirm)  ▢ edit the line  ▢ discuss

## 2. K6 — S1b sleep (the clean leftover)
Same class as K1–K4 (a covered-elsewhere affect phrasing that just isn't in the keyword layer). "I never feel
rested when I wake up" → `intent=new_skill` but no skill matched; `sleep_hygiene` already carries sleep
phrasings, this is one register wider (non-restorative sleep is a direct sleep-quality report).
> **K6 §S1b:** add "never feel rested" / "don't feel rested" → sleep_hygiene track  ▢ approve  ▢ edit  ▢ reject

## On approval
K6 lands with the K1–K5 batch's shape (per-category fixture, disposition-ownership check). S2a's split becomes
a follow-up PR once you confirm the exemplar sort. Neither is a served-behavior change until the deploy-owner
authorizes the push.
