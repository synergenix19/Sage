# Psychoeducation Phase 1 — Content & Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce the complete, validated, clinician-signable psychoed content layer — 40 blocks, 6 manifests, 6 trigger tables, collision table, shared scripts, PSY-WEAVE-1 draft data, and the sign-off packet — with zero graph code.

**Architecture:** Content-as-code under `data/psychoed/` (same governance class as the lexicons: phrases in data, runner in code). Every artifact is transcribed verbatim from the full-fidelity doc extraction, em-dash-scrubbed, schema-validated, and source-cited. CI tests enforce schema, scrub, citation, coverage-by-name, single-sourcing, and declared-collision completeness. Spec: `docs/superpowers/specs/2026-07-23-psychoeducation-pathways-design.md`.

**Tech Stack:** Python 3 (repo standard), `uv run pytest`, JSON data files, `jsonschema` if already a dependency — otherwise hand-rolled validators (no new dependencies).

## Global Constraints

- **Verbatim transcription:** block/script text is transcribed character-for-character from `docs/superpowers/specs/bot-behaviour-oracle/bot_behaviour_full.md`, then em-dash-scrubbed. NEVER paraphrase, never author. The scrubbed text becomes the signable artifact (spec §3.6).
- **Em-dash rule:** no `—` (U+2014) or `–` (U+2013) in any served-copy field (`content`, `framing_statement`, `menu_offer`, `check_in`, shared scripts, weave patterns). Replace with comma or period per sentence sense. Enforced by test.
- **Source citation:** every artifact carries `source_citation: {file: "docs/superpowers/specs/bot-behaviour-oracle/bot_behaviour_full.md", section: "<doc section>"}` (spec §3.3; 2026-07-17 stripped-.txt rule — trigger tables are Word tables and MUST come from the full extraction).
- **No clinical-content invention:** where the doc is ambiguous, flag in the packet's open-questions list; do not resolve clinically.
- **Category IDs:** `1f`, `3c`, `4b`, `6d`, `7c`, `s2c`. Block IDs: `<category>-b<N>` in doc order (e.g. `1f-b1`).
- **Branch:** `feat/psychoed-phase1-content` off current master. One commit per task. No memory-directory writes (work-session rule).
- **Everything here is default-inert:** no production code path reads `data/psychoed/` until Phase 2. Tests + scripts only.

## File Structure

```
data/psychoed/
  blocks/en/{1f,3c,4b,6d,7c,s2c}/<block_id>.json   # 40 block files (KB-article-compatible + psychoed extension)
  manifests/<category>.json                          # 6 pathway manifests
  trigger_tables/en/<category>.json                  # 6 trigger tables
  collisions/collision_table.json                    # declared cross-category resolutions
  shared/shared_scripts.en.json                      # #321 single-sourced ratified scripts (data; Phase 2 loads into constants)
  weave/psy_weave_1.en.json                          # PSY-WEAVE-1 draft data (clinician-pending)
scripts/psychoed_ingest/
  __init__.py
  schemas.py                                         # schema definitions + validate functions
  audit_collisions.py                                # collision-set computation + declared-resolution check
scripts/extract_bot_behaviour_full.sh                # docx → full-fidelity markdown
tests/test_psychoed_content_integrity.py             # all Phase 1 CI checks
docs/superpowers/governance/2026-07-23-psychoed-signoff-packet.md
```

---

### Task 1: Full-fidelity source extraction (`bot_behaviour_full.md`)

The repo has NO `bot_behaviour_full.md` (verified 2026-07-23). The stripped `.txt` extraction loses every Word table, including all §0 trigger tables. Create the canonical full extraction.

**Files:**
- Create: `scripts/extract_bot_behaviour_full.sh`
- Create: `docs/superpowers/specs/bot-behaviour-oracle/bot_behaviour_full.md` (generated, committed)

**Interfaces:**
- Produces: `docs/superpowers/specs/bot-behaviour-oracle/bot_behaviour_full.md` — the ONLY permitted transcription source for Tasks 2–11; its SHA-256 recorded in the file header of every schema (`SOURCE_SHA`).

- [ ] **Step 1: Write the extraction script**

```bash
#!/usr/bin/env bash
# scripts/extract_bot_behaviour_full.sh — full-fidelity extraction of the BOT BEHAVIOUR clinician doc.
# Tables MUST survive (the §0 trigger tables are Word tables; the stripped .txt loses them —
# 2026-07-17 source-integrity rule). Requires pandoc.
set -euo pipefail
SRC="${1:?usage: extract_bot_behaviour_full.sh <path-to-BOT BEHAVIOUR.docx>}"
OUT="docs/superpowers/specs/bot-behaviour-oracle/bot_behaviour_full.md"
pandoc "$SRC" -f docx -t gfm --wrap=none -o "$OUT"
# Table-survival check: S2c's trigger table must appear as a pipe table.
grep -q '|' "$OUT" || { echo "FATAL: no tables survived extraction"; exit 1; }
grep -q 'Why does grief come in waves' "$OUT" || { echo "FATAL: S2c content missing"; exit 1; }
shasum -a 256 "$OUT"
```

- [ ] **Step 2: Run it against the docx**

Run: `bash scripts/extract_bot_behaviour_full.sh "/Users/knowledgebase/Downloads/BOT BEHAVIOUR.docx"`
Expected: SHA-256 line printed; no FATAL. If pandoc is missing: `brew install pandoc` first.

- [ ] **Step 3: Manually verify the six §0 trigger tables render as markdown tables**

Run: `grep -n -A2 "Trigger Words / Recognition" docs/superpowers/specs/bot-behaviour-oracle/bot_behaviour_full.md | head -40`
Expected: pipe-table rows (`| Type | Examples |`) after each §0 heading for 1f, 3c, 4b, 6d, 7c, S2c (and the in-flow categories). If any table collapsed to prose, STOP and fix extraction before proceeding — do not hand-reconstruct tables.

- [ ] **Step 4: Commit**

```bash
git add scripts/extract_bot_behaviour_full.sh docs/superpowers/specs/bot-behaviour-oracle/bot_behaviour_full.md
git commit -m "feat(psychoed): full-fidelity BOT BEHAVIOUR extraction with tables intact"
```

---

### Task 2: Schemas, validators, and the worked example block (`1f-b1`)

**Files:**
- Create: `scripts/psychoed_ingest/__init__.py` (empty)
- Create: `scripts/psychoed_ingest/schemas.py`
- Create: `data/psychoed/blocks/en/1f/1f-b1.json`
- Test: `tests/test_psychoed_content_integrity.py`

**Interfaces:**
- Produces: `validate_block(path) -> list[str]`, `validate_manifest(path) -> list[str]`, `validate_trigger_table(path) -> list[str]` (each returns a list of error strings, empty = valid); `iter_psychoed_files(kind) -> list[Path]` where kind ∈ {"block","manifest","trigger_table"}; `EM_DASHES = ("—", "–")`; `SOURCE_FILE = "docs/superpowers/specs/bot-behaviour-oracle/bot_behaviour_full.md"`. Tasks 3–12 depend on these exact names.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_psychoed_content_integrity.py
from pathlib import Path
import json, pytest
from scripts.psychoed_ingest import schemas

def _blocks():
    return sorted(Path("data/psychoed/blocks/en").rglob("*.json"))

def test_at_least_one_block_exists():
    assert _blocks(), "no psychoed blocks found"

@pytest.mark.parametrize("path", _blocks() or [Path("MISSING")])
def test_block_schema_valid(path):
    errs = schemas.validate_block(path)
    assert errs == [], f"{path}: {errs}"

@pytest.mark.parametrize("path", _blocks() or [Path("MISSING")])
def test_block_no_em_dashes(path):
    text = json.loads(path.read_text())["content"]
    for ch in schemas.EM_DASHES:
        assert ch not in text, f"{path}: em/en dash in served copy"

@pytest.mark.parametrize("path", _blocks() or [Path("MISSING")])
def test_block_source_citation(path):
    d = json.loads(path.read_text())
    assert d["psychoed"]["source_citation"]["file"] == schemas.SOURCE_FILE
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_psychoed_content_integrity.py -x -q`
Expected: FAIL (`ModuleNotFoundError: scripts.psychoed_ingest` or "no psychoed blocks found").

- [ ] **Step 3: Write the schema module**

```python
# scripts/psychoed_ingest/schemas.py
"""Validators for psychoed content-as-code artifacts (spec §3, 2026-07-23 design).
Hand-rolled (no new deps). Each validate_* returns [] when valid, else error strings."""
from pathlib import Path
import json

EM_DASHES = ("—", "–")
SOURCE_FILE = "docs/superpowers/specs/bot-behaviour-oracle/bot_behaviour_full.md"
CATEGORIES = ("1f", "3c", "4b", "6d", "7c", "s2c")
DELIVERY_SHAPES = ("menu_first", "answer_first")
ROW_ROUTES = ("standard", "direct_diagnostic", "formal_diagnosis")
FRAMINGS = ("personal", "abstract")

def _load(path: Path):
    return json.loads(Path(path).read_text())

def _req(d, keys, errs, prefix=""):
    for k in keys:
        if k not in d:
            errs.append(f"missing {prefix}{k}")

def validate_block(path) -> list[str]:
    errs: list[str] = []
    d = _load(path)
    _req(d, ("article_id", "language", "title", "content", "is_crisis_content", "psychoed"), errs)
    p = d.get("psychoed", {})
    _req(p, ("category", "article_family", "delivery_shape", "verbatim", "atomic",
             "menu_label", "source_citation"), errs, "psychoed.")
    if p.get("category") not in CATEGORIES:
        errs.append(f"bad category {p.get('category')}")
    if p.get("delivery_shape") not in DELIVERY_SHAPES:
        errs.append(f"bad delivery_shape {p.get('delivery_shape')}")
    if p.get("verbatim") is not True or p.get("atomic") is not True:
        errs.append("verbatim/atomic must be true")
    if p.get("source_citation", {}).get("file") != SOURCE_FILE:
        errs.append("source_citation.file must be the full extraction")
    if d.get("article_id") != Path(path).stem:
        errs.append("article_id != filename")
    return errs

def validate_manifest(path) -> list[str]:
    errs: list[str] = []
    d = _load(path)
    _req(d, ("category", "delivery_shape", "safety_weave", "framing_statement",
             "menu_offer", "check_in", "blocks", "bridge_map", "source_citation"), errs)
    if d.get("delivery_shape") not in DELIVERY_SHAPES:
        errs.append("bad delivery_shape")
    if not isinstance(d.get("safety_weave"), bool):
        errs.append("safety_weave must be bool")
    for b in d.get("bridge_map", []):
        _req(b, ("block_id", "skill_id", "offer"), errs, "bridge_map.")
        if b.get("offer") != "optional":
            errs.append("bridge offers are optional-not-automatic (spec §3.2)")
    for field in ("framing_statement", "menu_offer", "check_in"):
        for ch in EM_DASHES:
            if ch in d.get(field, ""):
                errs.append(f"em/en dash in {field}")
    return errs

def validate_trigger_table(path) -> list[str]:
    errs: list[str] = []
    d = _load(path)
    _req(d, ("category", "language", "rows", "source_citation"), errs)
    seen: set[str] = set()
    for r in d.get("rows", []):
        _req(r, ("row_id", "type", "framing", "route", "phrases"), errs, "row.")
        if r.get("framing") not in FRAMINGS:
            errs.append(f"{r.get('row_id')}: bad framing")
        if r.get("route") not in ROW_ROUTES:
            errs.append(f"{r.get('row_id')}: bad route")
        for ph in r.get("phrases", []):
            if ph.lower() in seen:
                errs.append(f"duplicate phrase within table: {ph}")
            seen.add(ph.lower())
    return errs

def iter_psychoed_files(kind: str) -> list[Path]:
    roots = {"block": "data/psychoed/blocks/en",
             "manifest": "data/psychoed/manifests",
             "trigger_table": "data/psychoed/trigger_tables/en"}
    return sorted(Path(roots[kind]).rglob("*.json"))
```

- [ ] **Step 4: Create the worked example block, transcribed from the full extraction**

Transcribe §1f content block 1 ("What is anxiety?") from `bot_behaviour_full.md` — the text below is the STRUCTURE; the `content` value MUST be the doc's own sentence(s), em-dash-scrubbed:

```json
{
  "article_id": "1f-b1",
  "language": "en",
  "title": "What is anxiety?",
  "content": "<VERBATIM §1f block-1 text from bot_behaviour_full.md, em-dashes replaced with commas/periods>",
  "is_crisis_content": false,
  "psychoed": {
    "category": "1f",
    "article_family": "understanding_anxiety",
    "delivery_shape": "menu_first",
    "verbatim": true,
    "atomic": true,
    "menu_label": "What is anxiety?",
    "source_citation": {
      "file": "docs/superpowers/specs/bot-behaviour-oracle/bot_behaviour_full.md",
      "section": "1f – UNDERSTANDING ANXIETY, Content per Topic, item 1"
    }
  }
}
```

(The placeholder marker above exists ONLY in this plan; committing a file containing `<VERBATIM` must fail — add this check now: in `validate_block`, append `errs.append("untranscribed placeholder")` when `"<VERBATIM" in d.get("content","")`.)

- [ ] **Step 5: Run tests to verify green**

Run: `uv run pytest tests/test_psychoed_content_integrity.py -q`
Expected: PASS (4 tests, 1 block discovered).

- [ ] **Step 6: Commit**

```bash
git add scripts/psychoed_ingest tests/test_psychoed_content_integrity.py data/psychoed/blocks/en/1f/1f-b1.json
git commit -m "feat(psychoed): content schemas + validators + worked 1f-b1 block"
```

---

### Task 3: §1f complete — 5 blocks, manifest, trigger table

**Files:**
- Create: `data/psychoed/blocks/en/1f/1f-b2.json` … `1f-b5.json`
- Create: `data/psychoed/manifests/1f.json`
- Create: `data/psychoed/trigger_tables/en/1f.json`
- Modify: `tests/test_psychoed_content_integrity.py` (add manifest/table parametrized tests + the coverage registry)

**Interfaces:**
- Consumes: `schemas.validate_manifest`, `schemas.validate_trigger_table`, `schemas.iter_psychoed_files`.
- Produces: `COVERAGE` dict in the test file — Tasks 4–8 extend it; Task 12 asserts it complete. Exact shape: `COVERAGE = {"1f": ["1f-b1","1f-b2","1f-b3","1f-b4","1f-b5"], ...}`.

- [ ] **Step 1: Add failing manifest/table/coverage tests**

```python
# append to tests/test_psychoed_content_integrity.py
COVERAGE = {
    "1f": ["1f-b1", "1f-b2", "1f-b3", "1f-b4", "1f-b5"],
}

def test_manifests_valid():
    paths = schemas.iter_psychoed_files("manifest")
    assert paths, "no manifests"
    for p in paths:
        assert schemas.validate_manifest(p) == [], p

def test_trigger_tables_valid():
    paths = schemas.iter_psychoed_files("trigger_table")
    assert paths, "no trigger tables"
    for p in paths:
        assert schemas.validate_trigger_table(p) == [], p

def test_coverage_registry_matches_disk():
    on_disk = {p.stem for p in schemas.iter_psychoed_files("block")}
    declared = {b for blocks in COVERAGE.values() for b in blocks}
    assert declared <= on_disk, f"declared but missing: {declared - on_disk}"
```

Run: `uv run pytest tests/test_psychoed_content_integrity.py -q` → Expected: FAIL (no manifests; 1f-b2..b5 missing).

- [ ] **Step 2: Transcribe blocks 1f-b2 … 1f-b5** (fight/flight/freeze; why physical symptoms; maintenance cycle; what is worry) — same JSON shape as `1f-b1`, `menu_label` = the doc's topic-menu wording, scrub em-dashes, cite section per block.

- [ ] **Step 3: Write the §1f manifest** (framing + menu-offer + check-in transcribed from §1f steps 1/2/4; bridge map per doc close):

```json
{
  "category": "1f",
  "delivery_shape": "menu_first",
  "safety_weave": false,
  "framing_statement": "<VERBATIM §1f step-1 Framing Statement, scrubbed>",
  "menu_offer": "<VERBATIM §1f step-2 Topic Menu, scrubbed>",
  "check_in": "<VERBATIM §1f step-4 Check-In / Close, scrubbed>",
  "blocks": ["1f-b1", "1f-b2", "1f-b3", "1f-b4", "1f-b5"],
  "bridge_map": [
    {"block_id": "1f-b4", "skill_id": "worry_tree", "offer": "optional"},
    {"block_id": "1f-b2", "skill_id": "box_breathing", "offer": "optional"}
  ],
  "guards": ["acute_distress", "diagnosis_guard", "crisis_override"],
  "source_citation": {"file": "docs/superpowers/specs/bot-behaviour-oracle/bot_behaviour_full.md", "section": "1f – UNDERSTANDING ANXIETY"}
}
```

Verify `worry_tree` and `box_breathing` are the exact `skill_ids.py` registry IDs before committing (`grep -n "worry\|box" src/sage_poc/skill_ids.py`); if the registry spells them differently, use the registry spelling (it is canonical).

- [ ] **Step 4: Write the §1f trigger table** — every §0 row from the full extraction's 1f table, with `type` = the doc's Type column value, `framing`/`route` per spec §3.3/§5.5 (1f's rows are abstract/standard unless the doc row is a why-do-I phrasing; formal diagnosis rows → `formal_diagnosis`).

- [ ] **Step 5: Run tests green, then commit**

Run: `uv run pytest tests/test_psychoed_content_integrity.py -q` → Expected: PASS.

```bash
git add data/psychoed tests/test_psychoed_content_integrity.py
git commit -m "feat(psychoed): §1f complete — 5 blocks, manifest, trigger table"
```

---

### Task 4: §3c complete — 7 blocks, manifest (weave ON), trigger table (diagnostic row split)

**Files:** `data/psychoed/blocks/en/3c/3c-b1..b7.json`, `data/psychoed/manifests/3c.json`, `data/psychoed/trigger_tables/en/3c.json`; modify test `COVERAGE`.

**Interfaces:** Consumes Task 2 validators; extends `COVERAGE["3c"]`.

- [ ] **Step 1:** Extend `COVERAGE` with `"3c": ["3c-b1".."3c-b7"]`; run tests → FAIL (missing files).
- [ ] **Step 2:** Transcribe the 7 blocks (bio-psycho-social; snap-out-of-it; motivation/energy; numb/empty (anhedonia); sadness vs. depression; no-reason; seeking help), `delivery_shape: "answer_first"`, `article_family: "understanding_depression"`.
- [ ] **Step 3:** Manifest with `"safety_weave": true` and §3c's framing (it carries the built-in can't-diagnose disclosure — transcribe as-is, that's the `direct_diagnostic` route's disclaimer home, spec §5.5).
- [ ] **Step 4:** Trigger table: the doc's "Direct diagnostic questions" rows ("I think I might be depressed", "Is this depression or just stress?") get `route: "direct_diagnostic"`; formal rows ("do I have depression") get `route: "formal_diagnosis"`; personally-framed why-rows get `framing: "personal"`. **"Why do I feel numb?" stays in this table** — the collision is resolved in Task 10's collision table, not by removing rows.
- [ ] **Step 5:** Tests green; commit `feat(psychoed): §3c complete with weave + diagnostic row split`.

---

### Task 5: §4b complete — 7 blocks, manifest, trigger table

Same pattern as Task 4. Blocks: why emotions; what emotions signal; intensity differences; getting triggered; body-before-thought; responding vs. reacting; shutting down. `article_family: "understanding_emotions"`, `safety_weave: false`, bridge: `{"block_id": "4b-b6", "skill_id": "<registry id for box_breathing/grounding per doc's route-to-1a note>", "offer": "optional"}`. Trigger rows are dominated by personally-framed why-questions → `framing: "personal"`. Tests green; commit `feat(psychoed): §4b complete`.

---

### Task 6: §6d complete — 6 blocks, manifest, trigger table

Blocks: what is assertiveness; four styles; why patterns develop; building the skill; boundaries; culture. `article_family: "understanding_assertiveness"`. The culture block (`6d-b6`) is transcribed like every other block — no cultural_overrides string reuse (spec §3.6). Tests green; commit `feat(psychoed): §6d complete`.

---

### Task 7: §7c complete — 7 blocks, manifest, trigger table

Blocks: starting conversations; friends as adult; deepening; maintaining; awkwardness; belonging; family. `article_family: "how_do_i_connect"`. Bridge: `{"block_id": "7c-b7", "skill_id": "<registry id for the 6c rehearse/draft skill>", "offer": "optional"}` — resolve the exact skill ID from `skill_ids.py` (the doc's 6c hand-off). Tests green; commit `feat(psychoed): §7c complete (ruled amendment: answer-first KB category)`.

---

### Task 8: S2c complete — 8 blocks (one with block_guard), manifest (weave ON), trigger table

- [ ] **Step 1:** Extend `COVERAGE["s2c"]` (8 IDs); FAIL run.
- [ ] **Step 2:** Transcribe 8 blocks. `s2c-b8` ("How long does grief last?") carries the per-block guard:

```json
"block_guard": {
  "id": "prolonged_grief_support_note",
  "behavior": "append_support_note_no_diagnosis_naming",
  "note": "<VERBATIM the block's own closing support sentence from the doc, scrubbed>"
}
```

- [ ] **Step 3:** Manifest `safety_weave: true`. Add to the manifest a top-level `"flip_gate_note": "S2c serve OFF until reunification-ideation lexicon lands (spec §5.7); independent P0 clock"` so the gate travels with the artifact.
- [ ] **Step 4:** Trigger table; "Why do I feel numb?" appears here too (`framing: "personal"`), collision declared in Task 10.
- [ ] **Step 5:** Add sibling-contrast test (F5 pre-seed):

```python
def test_block_guard_only_on_s2c_b8():
    guarded = [p.stem for p in schemas.iter_psychoed_files("block")
               if "block_guard" in json.loads(p.read_text())["psychoed"]]
    assert guarded == ["s2c-b8"]
```

Tests green; commit `feat(psychoed): S2c complete — 8 blocks, weave ON, prolonged-grief block guard, flip-gate note`.

---

### Task 9: Shared single-sourced scripts + single-source CI check

**Files:** `data/psychoed/shared/shared_scripts.en.json`; modify test file.

**Interfaces:** Produces `shared_scripts.en.json` with EXACT keys `diagnosis_guard_stage1`, `diagnosis_guard_stage2`, `safety_weave_script`, `human_referral_close` — Phase 2's constants module loads these keys verbatim.

- [ ] **Step 1:** Failing test:

```python
def test_shared_scripts_present_and_single_sourced():
    d = json.loads(Path("data/psychoed/shared/shared_scripts.en.json").read_text())
    assert set(d["scripts"].keys()) == {"diagnosis_guard_stage1", "diagnosis_guard_stage2",
                                        "safety_weave_script", "human_referral_close"}
    # Single-source: no shared-script sentence may appear inside any block/manifest (#321 class).
    corpus = " ".join(p.read_text() for p in schemas.iter_psychoed_files("block"))
    corpus += " ".join(p.read_text() for p in schemas.iter_psychoed_files("manifest"))
    for name, text in d["scripts"].items():
        probe = text[:60]
        assert probe not in corpus, f"{name} duplicated into content ({probe!r})"
```

- [ ] **Step 2:** Transcribe the four scripts from the doc (§1f guard section for both diagnosis stages; §3c step-3 for the weave; the doc's human-referral close), scrub, cite. Note in the file: `"status": "ratified-source-pending-packet-signature"`.
- [ ] **Step 3:** Tests green. If a §3c framing sentence collides with the weave probe, the block/manifest keeps a POINTER (`"uses_shared": ["safety_weave_script"]`), never the text.
- [ ] **Step 4:** Commit `feat(psychoed): shared scripts single-sourced (#321 pattern) + CI check`.

---

### Task 10: Collision audit script — TDD against the known "numb" collision

**Files:** `scripts/psychoed_ingest/audit_collisions.py`, `data/psychoed/collisions/collision_table.json`; modify test file.

**Interfaces:** Produces `compute_collisions() -> dict[str, list[str]]` (normalized phrase → categories, only entries with ≥2 categories) and `undeclared_collisions() -> list[str]`; Phase 3's F2 fixtures read `collision_table.json` entries: `{"phrase", "categories", "resolution": {"context_signal", "context_winner", "default_winner"}, "safe_before_disambiguation": true}`.

- [ ] **Step 1: Write the audit module**

```python
# scripts/psychoed_ingest/audit_collisions.py
"""Cross-category trigger collision audit (spec §5.2). CI fails on undeclared collisions."""
import json, re
from pathlib import Path
from scripts.psychoed_ingest import schemas

COLLISION_TABLE = Path("data/psychoed/collisions/collision_table.json")

def _norm(p: str) -> str:
    return re.sub(r"[^\w\s']", "", p.lower()).strip()

def compute_collisions() -> dict[str, list[str]]:
    seen: dict[str, set[str]] = {}
    for t in schemas.iter_psychoed_files("trigger_table"):
        d = json.loads(t.read_text())
        for row in d["rows"]:
            for ph in row["phrases"]:
                seen.setdefault(_norm(ph), set()).add(d["category"])
    return {p: sorted(c) for p, c in seen.items() if len(c) > 1}

def undeclared_collisions() -> list[str]:
    declared = set()
    if COLLISION_TABLE.exists():
        declared = {_norm(e["phrase"]) for e in json.loads(COLLISION_TABLE.read_text())["collisions"]}
    return sorted(p for p in compute_collisions() if p not in declared)
```

- [ ] **Step 2: Failing test — the known collision must be CAUGHT first**

```python
def test_no_undeclared_collisions():
    from scripts.psychoed_ingest import audit_collisions
    assert audit_collisions.undeclared_collisions() == []
```

Run: `uv run pytest tests/test_psychoed_content_integrity.py::test_no_undeclared_collisions -q`
Expected: FAIL listing `why do i feel numb` (3c + s2c). If it does NOT fail, the trigger tables were transcribed wrong — stop and check Task 4/8.

- [ ] **Step 3: Declare the resolution (spec §5.2 verbatim rationale included)**

```json
{
  "note": "Deterministic collision resolutions. Mechanisms allowed: declared session context, scripted clarifying question. NEVER embedding-similarity tie-break. Safe-before-disambiguated: both phrasings personally framed, both categories carry the weave, fail-to-personal means the safety check fires on either branch.",
  "collisions": [
    {
      "phrase": "Why do I feel numb?",
      "categories": ["3c", "s2c"],
      "resolution": {
        "context_signal": "grief_disclosure_or_recent_s2_pathway",
        "context_winner": "s2c",
        "default_winner": "3c"
      },
      "safe_before_disambiguation": true
    }
  ]
}
```

Plus every other collision the audit surfaces (the audit finds the full set — declare each; if a resolution is not obvious from the doc, add it with `"resolution": {"pending": "clinician"}` and list it in the packet's open questions; the test accepts declared-pending, the FLIP gate does not).

- [ ] **Step 4:** Tests green; commit `feat(psychoed): collision audit CI + declared collision table (numb → 3c default, s2c on grief context)`.

---

### Task 11: PSY-WEAVE-1 draft data (EN)

**Files:** `data/psychoed/weave/psy_weave_1.en.json`; modify test file.

**Interfaces:** Produces keys `clear_negative_patterns` (list of normalized regex strings), `contradiction_markers` (list of strings), `status`, `version`. Phase 2's evaluator consumes exactly these keys; Phase 3's F4 fixtures pin them.

- [ ] **Step 1:** Failing test:

```python
def test_weave_data_shape_and_fail_closed_examples():
    d = json.loads(Path("data/psychoed/weave/psy_weave_1.en.json").read_text())
    assert d["status"] == "draft-pending-clinician"
    assert d["clear_negative_patterns"] and d["contradiction_markers"]
    import re
    def is_clear_negative(reply: str) -> bool:
        norm = re.sub(r"[^\w\s']", "", reply.lower()).strip()
        if any(m in norm for m in d["contradiction_markers"]):
            return False
        return any(re.fullmatch(p, norm) for p in d["clear_negative_patterns"])
    # natural clear negatives MUST pass (spec §6.1 false-crisis cost)
    for ok in ["No", "no, nothing like that", "No, alhamdulillah", "no I haven't, why?"]:
        assert is_clear_negative(ok), ok
    # everything else fails closed
    for bad in ["kind of", "sometimes", "not really but...", "no, but sometimes",
                "actually, what is anxiety?"]:
        assert not is_clear_negative(bad), bad
```

- [ ] **Step 2:** Author the draft data to satisfy exactly those examples:

```json
{
  "version": "0.1.0-draft",
  "status": "draft-pending-clinician",
  "design_extension_flag": "deflection_to_crisis_is_design_added_must_be_ratified_by_name",
  "clear_negative_patterns": [
    "no", "no nothing like that", "no not at all", "no alhamdulillah",
    "no i haven't( why)?", "no never", "nothing like that"
  ],
  "contradiction_markers": ["but", "sometimes", "kind of", "maybe", "a little", "not really"]
}
```

(Patterns are drafts for clinician review — the packet asks clinical to ratify/extend them; the test pins the fail-closed semantics, not the final list.)

- [ ] **Step 3:** Tests green; commit `feat(psychoed): PSY-WEAVE-1 draft data, fail-closed semantics pinned`.

---

### Task 12: Full-coverage completeness gate

**Files:** modify `tests/test_psychoed_content_integrity.py`.

- [ ] **Step 1:** Add the by-name completeness test (spec §3.4 map, all 40 + 18):

```python
FULL_MAP = {
    "1f": 5, "3c": 7, "4b": 7, "6d": 6, "7c": 7, "s2c": 8,
}

def test_full_coverage_by_name():
    for cat, n in FULL_MAP.items():
        blocks = COVERAGE.get(cat, [])
        assert len(blocks) == n, f"{cat}: {len(blocks)}/{n} blocks declared"
        expected = [f"{cat}-b{i}" for i in range(1, n + 1)]
        assert blocks == expected, f"{cat}: IDs must be {expected}"
    manifests = {p.stem for p in schemas.iter_psychoed_files("manifest")}
    tables = {p.stem for p in schemas.iter_psychoed_files("trigger_table")}
    assert manifests == set(FULL_MAP), f"manifests: {manifests}"
    assert tables == set(FULL_MAP), f"trigger tables: {tables}"

def test_manifest_scripts_complete():
    for p in schemas.iter_psychoed_files("manifest"):
        d = json.loads(p.read_text())
        for f in ("framing_statement", "menu_offer", "check_in"):
            assert d[f].strip() and "<VERBATIM" not in d[f], f"{p.stem}.{f} untranscribed"
```

- [ ] **Step 2:** Run the WHOLE suite: `uv run pytest tests/test_psychoed_content_integrity.py -q` → Expected: PASS, ~20 tests. Any failure = a transcription gap; fix the content, never the test.
- [ ] **Step 3:** Commit `test(psychoed): full-coverage completeness gate (40 blocks + 18 scripts by name)`.

---

### Task 13: Sign-off packet assembly

**Files:** Create `docs/superpowers/governance/2026-07-23-psychoed-signoff-packet.md`.

- [ ] **Step 1:** Generate the doc→artifact diff material: for each of the 6 categories, a section listing every block ID + title, and the em-dash scrub diff produced by:

Run: `for f in data/psychoed/blocks/en/*/*.json; do python3 -c "import json,sys; d=json.load(open('$f')); print('##', d['article_id']); print(d['content'])"; done > /tmp/psychoed_artifact_dump.txt` — then diff against the corresponding `bot_behaviour_full.md` passages per block, embedding each diff hunk in the packet.

- [ ] **Step 2:** Write the packet with EXACTLY these ask sections (spec §9, all by name):
  1. Blocks & scripts ratification (40 + 18, enumerated, with scrub diffs)
  2. Manifests: delivery shapes, weave scopes (§3c + S2c ON — confirm scope), bridge maps, per-block guard (`s2c-b8`)
  3. Trigger tables + collision table (incl. any `pending: clinician` resolutions)
  4. PSY-WEAVE-1 data — **deflection→crisis presented BY NAME as a design-added extension** (doc's branch is binary); ratify or edit the negative patterns + contradiction markers
  5. Diagnosis-guard row-split mapping (direct_diagnostic vs formal_diagnosis row assignments per table)
  6. Framing-row mappings (safety-rule governance — sign-off required for future edits)
  7. Classifier A structural-signal thresholds (proposal: fragmentation + numeric self-report; clinical sets values)
  8. §7c ruled amendment (reclassified answer-first KB category; supersedes provisional interpersonal_effectiveness match)
  9. Surface-2 `kb_ref` additions list
  10. **AR validator naming — first domino for the entire AR chain; the AR clock does not start until named**
  11. **F1 naturalistic-recall acceptance bar — clinical sets it (per category or global, their call); §7.3 flip precondition dangles without it**
  12. Open questions (anything flagged `pending: clinician` during Tasks 3–11)

- [ ] **Step 3:** Commit `docs(psychoed): clinician sign-off packet — Lane-3 clock starts`.

---

### Task 14: Phase 2 handoff notes (binding requirements carried forward)

**Files:** Create `docs/superpowers/plans/2026-07-23-psychoed-phase2-handoff-notes.md`.

- [ ] **Step 1:** Write the notes file with these verbatim requirements (each cites its spec section):
  - **Rule-6 carry-forward evaluation mechanic (review addition 2):** carry-forward writes per-article-family `prior_exposure`; step-policy rule 6 evaluates per-skill. The skip works ONLY if, for a given skill, rule 6's condition reads the counter of the family its `kb_ref` points to — i.e. the evaluation is `prior_exposure[family_of(skill.kb_ref)] >= threshold`, not `prior_exposure[skill_id]`. Wire rule 6 against the `kb_ref`-resolved family counter or it reads a counter that never increments (spec §4.4 + schema extension 7).
  - Mechanism-A retirement: each category flip retires its consult-set entry in the same change (spec §0).
  - State channel keys, exact list (spec §4.2) — declare before build, `check_state_channels.py` + graph test.
  - PSY-WEAVE-1 precedence: evaluates before resolver matching on weave-pending turns (spec §2.1 step 1).
  - Node-8 hash-mismatch failure path: block → re-serve pinned → neutral referral on fetch-fail; never emit unverified (spec §6.2).
  - Shared-scripts constants module loads `shared_scripts.en.json` keys verbatim (Task 9 interface).
- [ ] **Step 2:** Commit `docs(psychoed): phase-2 handoff notes (rule-6 kb_ref-family mechanic et al.)`.

---

## Self-Review (performed at write time)

- **Spec coverage:** §3.1–3.6 → Tasks 2–9; §5.2 → Task 10; §6.1 data → Task 11; full-coverage rule → Task 12; §9 packet incl. F1-bar + AR-validator asks → Task 13; review-addition 2 → Task 14. AR artifacts (§3.7) are deliberately absent: blocked on validator naming (first domino), listed as packet ask 10 — not a plan gap. Phases 2–4 are separate plans by scope ruling.
- **Placeholder scan:** the two `<VERBATIM …>` markers are transcription directives (content must come from the ratified doc, not this plan) and are guarded by the Task 2 Step 4 validator check — committing an untranscribed file fails CI.
- **Type consistency:** `validate_block/manifest/trigger_table`, `iter_psychoed_files`, `COVERAGE`, `FULL_MAP`, `compute_collisions/undeclared_collisions`, weave keys — cross-checked across Tasks 2/3/10/11/12.
