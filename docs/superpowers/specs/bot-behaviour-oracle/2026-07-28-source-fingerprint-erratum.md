# Erratum — 2026-07-17 source-integrity record's descriptive table count (2026-07-28)

**Scope:** the 07-17 record's fingerprint line "pandoc -f docx -t gfm of the real .docx (4661 lines, all 27 Skill/Format tables intact)". The record states no counting method.

**Finding:** against the pinned docx (`BOT_BEHAVIOUR_ratified_source.docx`, SHA-256 `62948d51…fa6c`, hash-verified):

| Axis | Value | Method |
|---|---|---|
| Default-wrap line count | **4,661 exactly** | `pandoc -f docx -t gfm` (no wrap flag) — matches the record to the line |
| `--wrap=none` line count | 2,696 | canonical extraction variant (one line per paragraph) |
| Total tables | **62** on BOTH wrap variants | 61 pipe + 1 raw-HTML (§6b relationship-safety recognition-phrase table, merged cells) |
| Skill/Format-header tables | **26** on BOTH wrap variants | pipe-header grep `Skill\*\*.*Format\*\*` |
| Record's "27" | probable = 26 pipe + the §6b HTML-rendered table | **inference** — the record does not state its method; cannot be confirmed or refuted from the record |

**Adjudication (2026-07-28 ruling):** identity was decided NOT on the count but on the record's five load-bearing derived facts, all re-derived from the fresh extraction:

1. 51 Format rows across the Skill/Format tables — **reproduced exactly**.
2. 16 distinct verbatim Format values incl. every nuance (bare "Visual"=Emotions Wheel; "Video/audio guided"=Body Scan distinct from "Video"; three differently-worded staged formats = Worry Tree / §1e Box Breathing→Worry Tree / Life Compass; 4-way Info family; exactly one true format-OR = §S5a "Video / guided conversation") — **reproduced exactly**.
3. Instructional = exactly one skill (Sleep Hygiene) — **reproduced exactly**.
4. Category-dependent Format values for Worry Time and (Structured) Problem-Solving — **reproduced exactly** (plus the "Psychoeducation" offer-row varies Info/Give-options-from-1f; not a skill_id, consistent with the record's framing).
5. Gap sets — doc side **reproduced** (10 genuine doc pathways with no skill_id after removing OR-combination rows, arrow-chains, and info-family rows; cbt_thought_record + psychoed_anxiety/depression have no Format cell; no readiness-ruler row exists in the doc). Registry side differs from the record's "exactly 4" ONLY by registry evolution since 07-17 (`mi_readiness_ruler` deprecated in `757bb9d3`; several skills added after the record) — verified in `git log -S`, not assumed.

**Conclusion:** the pinned docx is content-identical on every axis the 07-17 record measured. The 27-vs-26 is a counting-method artifact, resolved as above so the next reader inherits resolution, not the puzzle. `scripts/extract_bot_behaviour_full.sh` now asserts: default-wrap 4,661 (equivalence to the record), canonical `--wrap=none` output, table population 61 pipe + 1 HTML (§6b named explicitly, so pandoc-version variance in table rendering re-opens loudly, not silently), 26 Skill/Format pipe headers, six §0 psychoed trigger tables.

**Process notes for the record:**
- The Task-1 implementer subagent hit the fingerprint mismatch (line-count flag artifact), reported BLOCKED with exact numbers, made no commit, and did not tweak the script to pass — the stop discipline working exactly as designed.
- The six §0 psychoed trigger tables passed population and content probes on both wrap variants throughout — the psychoed chain's own integrity was never in question. This reconciliation protected the shared normative source's identity, which is worth the pause.
