# Source-integrity record 2026-07-17 — the table-stripped BOT BEHAVIOUR extraction

**Finding (the thread's 5th stale-instrument catch, and the furthest-reaching).** The working plaintext `scratchpad/bot_behaviour.txt` (1548 lines) is a **lossy** extraction of `BOT BEHAVIOUR.docx`: every Word **table was stripped to blank lines** on conversion. Grepping it for "Format" returns **zero** hits; only 2 of ~51 Format values survive as incidental prose. Every prior "Format-column" claim in this thread was made against a document **missing its tables** — the "~6-value enum I read from the doc" was reconstructed from prose fragments, not the actual column.

**Normative source going forward:** `scratchpad/bot_behaviour_full.md` — `pandoc -f docx -t gfm` of the real `.docx` (4661 lines, all 27 Skill/Format tables intact). Any doc-derived artifact that touched **tables** must cite this file, not the stripped `.txt`. Prose sections (bullet lists like §HR.0, the crisis/medical copy) survived the strip and are unaffected.

**Bounded contamination check (this is what makes the lineage trustworthy):**
- **Table-derived work in this thread:** the P0b Format enum (this spec — now redone from `bot_behaviour_full.md`) and the psychoed `instructional_set.py` `{sleep_hygiene}` derivation. The latter was cross-derived from `bot-behaviour-spec-source-2026-07-08.md` (not the stripped file) **and** is independently reconfirmed by this full re-extraction (`Instructional` = exactly 1 skill). So it stands.
- **Prose-derived work:** HR-1 §HR.0 triggers (a bullet list, survived), crisis/medical copy, the psychoed consult set (corpus-derived, not doc-tables). **Unaffected.**
- **Net: the re-verify set is empty of surviving errors** — but the check is recorded so the next person trusts the lineage rather than re-auditing.

**Lesson:** verify the instrument before trusting its reading applies to source files too, not just measurements. Relates to [[feedback_characterize_before_build]] and [[feedback_primary_record_over_inference]].
