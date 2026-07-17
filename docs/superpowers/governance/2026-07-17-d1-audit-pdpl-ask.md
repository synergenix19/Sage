# PDPL confirmation ask — D1 screen audit row (#338)

**One-line answer to a framed question. Due today** — shadow writes this row, and shadow starts at the
dark-deploy, so the confirmation must close before the first prod row (including shadow) writes.

## What writes
A new decision-record class on turns where the D1 medical screen runs. **Three fields, no message content:**
- `screen_asked` (bool) — the contraindication question was asked
- `screen_answer_class` — one of: `clear_no | red_flag | yes | unclear | no_answer` (a **class**, not the user's words)
- `screen_branch_taken` — `proceed | medical_guard | grounding | abandoned_crisis`

**No free text, no message content is stored** — only the class and the route.

## Purpose
**Contraindication-decision traceability under the right-to-object.** A screen decides whether a user with a
possible cardiac/pregnancy contraindication is routed to a physical technique (TIPP) or away from it; that
decision must be traceable to its rule and answer-class, or it cannot be defended if objected to. The row is
the record. (This is why the write is #160 alert-or-fail: a swallowed write = a contraindication decision with
no record.)

## The ask (one line)
> Is a decision-record row of `{screen_asked, screen_answer_class, branch_taken}` — **class + route only, no
> message content** — an acceptable PDPL basis for contraindication-decision traceability under right-to-object,
> to write in prod (incl. shadow)?

▢ confirmed ▢ needs change: ______

*Blocks: the first prod audit-row write (shadow). Not the code, not GATE 0, not Vee's clinical ticks — those
proceed in parallel.*
