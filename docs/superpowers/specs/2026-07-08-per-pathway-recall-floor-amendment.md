# Per-Pathway Recall Floor — Signed Gate-Config Amendment (DRAFT for PO + clinical signature)

SIGNED-BY: Rohan (PO) · clinical lead (approved)   DATE: 2026-07-08   AMENDS: `gate_config.py` G6 (2026-07-08)
> Same G6 discipline + provenance-with-artifact. Signed via the recall-concentration disclosure packet (PR #206) — one signature event covering disclosure + this floor + the pathway list.

## Why (from the disclosure)
The aggregate in_scope recall tripwire (51.77%) demonstrably HID a fully-suppressed pathway (§3a BA, 0/5). A per-pathway floor makes the next concentrated gap a **gate failure**, not an audit discovery.

## The floor — a SUPPRESSION DETECTOR, honest about small n
Per-pathway n in the corpus is small (§3a was 0/5). This is NOT a fine-grained percentage (the G6 `n_floor=30` logic: 5 cases cannot carry a precise rate). It is a total-suppression detector, which is the clinically meaningful threshold anyway:
- **Zero-recall on any listed core pathway = HARD gate failure** (no core pathway may be fully suppressed).
- **Below 40% on a listed pathway = WARNING requiring disposition** (recorded, not auto-blocking).
- Aggregate 51.77% tripwire unchanged; this is additive.

## Core clinical pathway list (BY LIST, not adjective — clinician owns membership)
Proposed initial set (from the skills inventory's target_presentations; clinician confirms/edits in the same ruling):
| pathway | skill(s) |
|---|---|
| depression / behavioural activation | `behavioral_activation` |
| anxiety cluster | `box_breathing`, `grounding_5_4_3_2_1`, `progressive_muscle_relaxation`, `dbt_tipp` |
| worry | `worry_time`, worry_tree |
| self-worth / self-criticism | `self_compassion_break`, `cognitive_restructuring` |
| grief (presence-mode) | `grief_loss` |
| sleep | `sleep_hygiene` |
| boundaries / interpersonal | `interpersonal_effectiveness`, `assertive_communication` |

"Core" is what's on this list — never a vibe re-litigated per gate run.

## Gate-run watch (engineering)
BA exemplar enrichment moves the bi-encoder candidate surface + the reranker score distribution. **Watch the id_oos cells** — an over-broad exemplar set leaks the safety win back (id_oos abstain drops below the 0.906 floor). That is exactly why bin (b) exists. If the gate shows id_oos regression, the fix **narrows the exemplar set; it never touches τ.**


## SIGN-OFF (2026-07-08): APPROVED — zero-recall=hard-fail, <40%=warning; pathway list approved as proposed.
