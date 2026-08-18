# KB Corpus Refresh (19 Clinician-Approved Articles) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the EN knowledge-corpus content with the 19 clinician-approved article rewrites (docx in `~/Downloads/English/` = source of truth), preserving all existing article IDs, keeping every CI corpus-integrity invariant green, and closing the corpus crisis-number single-source gap as a side effect.

**Architecture:** Doc sections are allocated onto the **existing** article IDs (no deletions, no AR orphans; one new ID `emotions-001`). Approved text + approved redlines are assembled into per-article plain-text "masters"; a mechanical script converts masters → corpus JSON. AR pair files get a `source_url`/`citation` sync only (content untouched — AR content refresh is a separate clinician-gated lane). A new CI guard pins "no hardcoded helpline numbers in corpus content."

**Tech Stack:** Python 3.12 (stdlib only for scripts), pytest, existing `sage_poc.knowledge.ingestion` chunker, macOS `textutil` for docx extraction.

## Global Constraints

- **Source of truth:** the 19 docx files, as amended ONLY by clinician-approved redline items in `~/Documents/Sage/Sage_KB_Editorial_Redlines_2026-08-18.md`. No other wording changes, ever. Declined redline items ship with the original wording.
- **Gate:** Tasks 4–10 DO NOT START until the user confirms which redline items were approved. Tasks 1–3 (worktree, docx extraction, guard test) are wording-independent and may run before the gate; Task 2 Step 2 (master assembly) is gated.
- **No deletions:** every existing `article_id` in `data/knowledge_corpus/en/` keeps a JSON file. Depression family (`depression-001..003`) is untouched.
- **Crisis articles** (`crisis-001..004`): `is_crisis_content: true` (single-chunk). All other articles `false`.
- **AR files:** only `source_url` and `citation` may change. `content`, `title`, `is_crisis_content`, `requires_clinical_review` are untouched.
- **Placeholder markers** (`TBD`, `TODO`, `[CLINICAL`, `[CONTENT AUTHOR`, `[same as EN`) must not appear in any output file (CI-enforced for AR; treat as binding for EN too).
- **British spelling** throughout content (matches corpus).
- **Worktree:** all edits happen in a fresh dedicated worktree (standing rule; bare `git stash`/`pop` is banned in this repo).
- **Commits:** one commit per source docx (atomic revert per clinical unit), plus separate commits for the guard test, constants, and AR sync.
- **Merge ≠ deploy, but merge arms deploy:** corpus auto-syncs to prod on next deploy startup (`sync_corpus`, content-hash delete+reinsert). Deploy/permission stays with the user (standing rule).
- **JSON style:** `json.dumps(..., indent=2, ensure_ascii=False)` + trailing newline, matching existing corpus files.

## Section → Article Allocation Table (normative)

Single-target docs — entire body (all sections, headings included) becomes that article's `content`:

| docx | article_id | title (final) |
|---|---|---|
| assertiveness | assertiveness-001 | What is assertiveness? |
| breathing | breathing-001 | What is breathwork, and how does it work? |
| grief | grief-001 | Understanding grief and loss |
| grounding | grounding-001 | Grounding techniques explained |
| mental health in arab culture | gulf-001 | How does culture shape the way mental health is understood in the Gulf? |
| mindfulness | mindfulness-001 | What is mindfulness? |
| self-compassion | self-compassion-001 | What is self-compassion? |
| sleep | sleep-001 | What is sleep, and why do we need it? |
| therapy | therapy-001 | What is therapy, and how does it work? |
| trauma | trauma-001 | What is trauma? |
| values | values-001 | What are personal values and why do they matter? |
| mental health | wellbeing-001 | What is mental health? |
| emotions | **emotions-001 (NEW)** | What are emotions? |

Multi-target docs — sections allocated by heading (headings quoted post-redline):

| docx | article_id | sections (in doc order) |
|---|---|---|
| anxiety | anxiety-001 "What is anxiety?" | "What is anxiety?", "Isn't anxiety just overthinking?", "Why do I feel anxious for no reason?" |
| anxiety | anxiety-002 "How anxiety affects the body" | "How anxiety affects the body.", "Why does my mind keep jumping to worst case scenarios?" |
| anxiety | anxiety-003 "Anxiety vs worry: what's the difference" | "Anxiety vs worry: what's the difference.", "When should I get help for anxiety?" |
| CBT | cbt-001 "What is CBT?" | "What is CBT?", "Isn't CBT just \"positive thinking\"?", "Why do my thoughts, feelings and behaviours feed into each other?", "What does a thought record actually look like?", "CBT vs talking therapy: what is the difference?", "Why would CBT help if I can't point to what's wrong?" |
| CBT | cbt-002 "How CBT sessions work in practice" | "How CBT sessions work in practice." |
| coping | coping-001 "What are coping strategies?" | "What are coping strategies?", "Isn't coping just \"pushing through\" or distraction?", "Why does the same strategy work for one person and not the other?", "Healthy coping vs avoidance: what's the difference?", "Why do I reach for unhelpful coping habits without deciding to?", "How do I build a coping strategy that actually fits me?" |
| coping | coping-002 "Problem-focused vs emotion-focused coping" | "Problem-focused vs emotion-focused coping." |
| crisis | crisis-001 "What to do in a mental health crisis" | opening section (under the doc title) |
| crisis | crisis-002 "UAE mental health crisis resources" | "UAE mental health crisis resources." |
| crisis | crisis-003 "Supporting someone in crisis" | "Supporting someone in crisis." |
| crisis | crisis-004 "Self-harm: understanding and getting help" | "Self-harm: understanding and getting help." |
| stress | stress-001 "What is stress? Acute and chronic" | "What is stress? Acute and chronic.", "Isn't stress just a mindset problem?", "Stress vs anxiety: what's the difference.", "Why do I feel stressed when nothing's changed?", "When does stress become a problem I need help with?" |
| stress | stress-002 "How stress affects the body and mind" | "How stress affects the body and mind.", "Why do I feel constantly on edge?" |
| relationships | relationships-001 "Relationships and mental health" | "Relationships and mental health.", "Isn't it selfish to prioritise my own mental health in a relationship?", "Why do relationship problems affect my mood and sleep so much?", "Healthy conflict vs harmful conflict: what's the difference?", "Why do the same arguments keep happening in my family?", "When should a relationship or family involve outside support?" |
| relationships | relationships-002 "Communication in families: a Gulf perspective" | "Communication in families: a Gulf perspective." |

Every article in a family carries the **same** `source_url` and `citation` (the doc supplies one of each). Multi-target member titles stay as the existing corpus titles (shown above). If a redline item affecting an allocated heading was declined, use the doc's original heading verbatim.

**Coverage check (must hold at Task 4):** masters produced = 28 (13 single-target + 15 family members). EN corpus after refresh = 31 files (30 existing + emotions-001).

---

### Task 1: Worktree and branch setup

**Files:** none (environment)

**Interfaces:**
- Produces: worktree at `~/Documents/Sage/sage-poc-kbrefresh-wt` on branch `feat/kb-corpus-refresh-2026-08`, used by every later task.

- [ ] **Step 1: Create the worktree** (dedicated fresh worktree per standing rule; sage-poc branches push as-is, no `cdai/` prefix)

```bash
cd ~/Documents/Sage/sage-poc
git fetch origin
git worktree add ../sage-poc-kbrefresh-wt -b feat/kb-corpus-refresh-2026-08 origin/master
```

- [ ] **Step 2: Verify baseline is green before touching anything**

Run: `cd ~/Documents/Sage/sage-poc-kbrefresh-wt && .venv/bin/python -m pytest ../sage-poc/tests/test_corpus_integrity.py -q 2>/dev/null || python3 -m pytest tests/test_corpus_integrity.py -q`
(use the repo's normal venv; if the worktree has no venv, `python3 -m venv .venv && .venv/bin/pip install -e . pytest` first)
Expected: all corpus tests PASS.

---

### Task 2: Extract approved text and build per-article masters

**Files:**
- Create: `~/Documents/Sage/sage-poc-kbrefresh-wt/.kb_masters/<article_id>.txt` × 28 (NOT committed — add `.kb_masters/` to `.git/info/exclude`)

**Interfaces:**
- Produces: master files in the exact format Task 4's converter consumes:

```
title: <final title>
source_url: <URL>
citation: <academic reference text, no leading "Reference:" label>
is_crisis_content: <true|false>
---
<content: heading line, blank line, paragraph(s); blank line between sections>
```

- [ ] **Step 1: Re-extract the docx files** (source of truth; do not reuse any earlier session's temp files)

```bash
mkdir -p ~/Documents/Sage/sage-poc-kbrefresh-wt/.kb_masters/_raw
cd ~/Downloads/English
for f in *.docx; do /usr/bin/textutil -convert txt -output ~/Documents/Sage/sage-poc-kbrefresh-wt/.kb_masters/_raw/"${f%.docx}".txt "$f"; done
echo ".kb_masters/" >> ~/Documents/Sage/sage-poc-kbrefresh-wt/.git/info/exclude 2>/dev/null || true
```

(worktrees share `info/exclude` via the main repo — if the echo path fails, use `~/Documents/Sage/sage-poc/.git/info/exclude`.)

- [ ] **Step 2: Assemble masters.** For each row of the Allocation Table: copy the doc's body text for the allocated sections into `<article_id>.txt`, apply exactly the APPROVED redline items from `Sage_KB_Editorial_Redlines_2026-08-18.md` (R1–R27, per the user's approval list), strip the docx boilerplate lines ("Title", "Source link", "Reference", stray "." lines), and fill the four header fields. `source_url` = the URL from the doc's "Source" line (relationships: the NHS URL from R21 if approved); `citation` = the doc's "Reference" text (with R22–R25 as approved). `is_crisis_content: true` only for crisis-001..004.

- [ ] **Step 3: Verify master inventory and hygiene**

```bash
cd ~/Documents/Sage/sage-poc-kbrefresh-wt/.kb_masters
ls *.txt | wc -l                       # expect 28
grep -L "^title: " *.txt               # expect empty
grep -l -E "TBD|TODO|\[CLINICAL|\[CONTENT AUTHOR|\[same as EN" *.txt  # expect empty
grep -l "Source link\|^Reference$" *.txt   # expect empty (boilerplate stripped)
```

Expected: counts as annotated; any hit = fix the master before proceeding.

---

### Task 3: CI guard — no hardcoded helpline numbers in corpus content

**Files:**
- Modify: `tests/test_corpus_integrity.py` (append after `test_crisis_phrases_are_single_clause`)

**Interfaces:**
- Produces: `test_no_hardcoded_helpline_numbers_in_corpus` — Task 5 must make it pass; it pins the single-source outcome permanently.

- [ ] **Step 1: Write the failing test**

```python
# Phone-number patterns that must never be hardcoded in corpus content. Crisis
# numbers are single-sourced in config.CRISIS_CONFIG and served via the crisis
# card / {{crisis_*}} placeholder surfaces — corpus articles carry none.
# (2026-08 refresh decision: clinician-approved crisis articles are number-free.)
_HELPLINE_NUMBER_RE = __import__("re").compile(
    r"\b(?:800[\s-]?\d{3,6}|920\s?\d{3}|999|998|911|112)\b"
)


def test_no_hardcoded_helpline_numbers_in_corpus():
    violations = []
    for articles in (_en_articles(), _ar_articles()):
        for aid, art in articles.items():
            for m in _HELPLINE_NUMBER_RE.findall(art.get("content", "")):
                violations.append(f"{aid} ({art['language']}): {m!r}")
    assert not violations, (
        "Hardcoded helpline/emergency numbers in corpus content — crisis numbers "
        f"are single-sourced in config.CRISIS_CONFIG: {violations}"
    )
```

- [ ] **Step 2: Run it to verify it fails against the CURRENT corpus** (crisis-001/002 carry 920003 / 800-7342 today — that failure is the point)

Run: `python3 -m pytest tests/test_corpus_integrity.py::test_no_hardcoded_helpline_numbers_in_corpus -v`
Expected: FAIL listing `crisis-001` and `crisis-002` numbers.

- [ ] **Step 3: Do NOT commit yet.** This test commits together with the crisis-family content in Task 5 so no pushed commit is red (branch CI gates are strict). Record the observed failure output in the PR description instead.

---

### Task 4: Converter script and EN corpus generation

**Files:**
- Create: `~/Documents/Sage/sage-poc-kbrefresh-wt/.kb_masters/convert.py` (not committed — one-off)
- Modify: `data/knowledge_corpus/en/*.json` (27 regenerated + 1 new `emotions-001.json`)

**Interfaces:**
- Consumes: Task 2 master format.
- Produces: corpus JSONs with the exact existing field order: `article_id, language, title, source_url, citation, content, is_crisis_content`.

- [ ] **Step 1: Write the converter**

```python
#!/usr/bin/env python3
"""One-off: 2026-08 KB refresh — masters (.kb_masters/*.txt) -> corpus JSON."""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent   # worktree root
MASTERS = ROOT / ".kb_masters"
OUT = ROOT / "data" / "knowledge_corpus" / "en"

for m in sorted(MASTERS.glob("*.txt")):
    head, body = m.read_text().split("\n---\n", 1)
    meta = dict(line.split(": ", 1) for line in head.strip().splitlines())
    article = {
        "article_id": m.stem,
        "language": "en",
        "title": meta["title"].strip(),
        "source_url": meta["source_url"].strip(),
        "citation": meta["citation"].strip(),
        "content": body.strip(),
        "is_crisis_content": meta["is_crisis_content"].strip() == "true",
    }
    out = OUT / f"{m.stem}.json"
    out.write_text(json.dumps(article, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {out.name}  ({len(article['content'])} chars)")
```

- [ ] **Step 2: Run it and validate against the pipeline's own schema check**

```bash
cd ~/Documents/Sage/sage-poc-kbrefresh-wt
python3 .kb_masters/convert.py            # expect 28 "wrote ..." lines
python3 - <<'EOF'
import json, pathlib, sys
sys.path.insert(0, "src")
from sage_poc.knowledge.ingestion import validate_article_schema
for f in sorted(pathlib.Path("data/knowledge_corpus/en").glob("*.json")):
    validate_article_schema(json.loads(f.read_text()))
print("all EN articles schema-valid")
EOF
```

Expected: `all EN articles schema-valid`; `ls data/knowledge_corpus/en | wc -l` → 31.

- [ ] **Step 3: Spot-diff one family for sanity** — `git diff data/knowledge_corpus/en/anxiety-001.json` should show new content/source/citation, same field order, `ensure_ascii` preserved (Arabic-free EN files unaffected by the flag).

- [ ] **Step 4: Commit — one commit per source docx, non-crisis families first (18 commits)**

```bash
git add data/knowledge_corpus/en/anxiety-00{1,2,3}.json && git commit -m "content(kb): refresh anxiety family from clinician-approved 2026-08 article"
git add data/knowledge_corpus/en/cbt-00{1,2}.json && git commit -m "content(kb): refresh cbt family from clinician-approved 2026-08 article"
git add data/knowledge_corpus/en/coping-00{1,2}.json && git commit -m "content(kb): refresh coping family from clinician-approved 2026-08 article"
git add data/knowledge_corpus/en/stress-00{1,2}.json && git commit -m "content(kb): refresh stress family from clinician-approved 2026-08 article"
git add data/knowledge_corpus/en/relationships-00{1,2}.json && git commit -m "content(kb): refresh relationships family from clinician-approved 2026-08 article"
# then one commit each for: assertiveness, breathing, grief, grounding, gulf,
# mindfulness, self-compassion, sleep, therapy, trauma, values, wellbeing, emotions
# same message pattern; emotions uses "content(kb): add emotions-001 (new topic, clinician-approved 2026-08)"
# crisis-001..004 are NOT committed in this task — Task 5.
```

Append the standing trailer to every commit: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 5: Crisis family + number guard (single commit)

**Files:**
- Modify: `data/knowledge_corpus/en/crisis-00{1,2,3,4}.json` (already regenerated by Task 4's converter run)
- Modify: `tests/test_corpus_integrity.py` (Task 3's test)

**Interfaces:**
- Consumes: Task 3's `test_no_hardcoded_helpline_numbers_in_corpus`; Task 4's generated crisis JSONs.

- [ ] **Step 1: Verify the crisis articles are single-chunk and number-free**

```bash
python3 - <<'EOF'
import json, pathlib, sys
sys.path.insert(0, "src")
from sage_poc.knowledge.ingestion import chunk_text
for aid in ("crisis-001","crisis-002","crisis-003","crisis-004"):
    a = json.loads(pathlib.Path(f"data/knowledge_corpus/en/{aid}.json").read_text())
    assert a["is_crisis_content"] is True, aid
    assert len(chunk_text(a["content"], is_crisis_content=True)) == 1, aid
print("crisis articles: is_crisis_content=true, single-chunk")
EOF
```

- [ ] **Step 2: Run the guard test — now it must pass**

Run: `python3 -m pytest tests/test_corpus_integrity.py::test_no_hardcoded_helpline_numbers_in_corpus -v`
Expected: PASS.

- [ ] **Step 3: Commit content + guard together**

```bash
git add data/knowledge_corpus/en/crisis-00*.json tests/test_corpus_integrity.py
git commit -m "content(kb): refresh crisis family (clinician-approved, number-free) + CI guard pinning corpus helpline-number single-sourcing"
```

---

### Task 6: AR pair source/citation sync

**Files:**
- Modify: `data/knowledge_corpus/ar/*.json` — exactly these 18: anxiety-001..003, assertiveness-001, cbt-001, coping-001..002, grief-001, gulf-001, mindfulness-001, relationships-001..002, self-compassion-001, sleep-001, stress-001..002, values-001, wellbeing-001. (depression-001..003 untouched.)

**Interfaces:**
- Consumes: Task 4/5's EN JSONs.
- Produces: AR files whose `source_url`/`citation` equal their EN pair (CI: `test_ar_source_url_and_citation_match_en`).

- [ ] **Step 1: Run the sync (script, not hand-edits — only two fields may change)**

```bash
python3 - <<'EOF'
import json, pathlib
EN = pathlib.Path("data/knowledge_corpus/en"); AR = pathlib.Path("data/knowledge_corpus/ar")
changed = []
for arf in sorted(AR.glob("*.json")):
    enf = EN / arf.name
    if not enf.exists():
        raise SystemExit(f"orphan AR article: {arf.name}")   # should be impossible
    en, ar = json.loads(enf.read_text()), json.loads(arf.read_text())
    if ar["source_url"] != en["source_url"] or ar["citation"] != en["citation"]:
        ar["source_url"], ar["citation"] = en["source_url"], en["citation"]
        arf.write_text(json.dumps(ar, indent=2, ensure_ascii=False) + "\n")
        changed.append(arf.name)
print(f"synced {len(changed)}: {changed}")
EOF
```

Expected: `synced 18: [...]` — if the count differs, STOP and reconcile against the list above before committing.

- [ ] **Step 2: Verify AR content untouched** — `git diff --stat data/knowledge_corpus/ar/` shows small diffs only; `git diff data/knowledge_corpus/ar/ | grep '^[-+]' | grep -v 'source_url\|citation\|^[-+][-+]'` returns nothing.

- [ ] **Step 3: Commit**

```bash
git add data/knowledge_corpus/ar/
git commit -m "content(kb): sync AR pair source_url/citation to refreshed EN (content untouched; AR content refresh is a separate clinician-gated lane)"
```

---

### Task 7: corpus_constants updates

**Files:**
- Modify: `src/sage_poc/corpus_constants.py` (the `DEFERRED_AR` dict)

**Interfaces:**
- Produces: `DEFERRED_AR` containing `emotions-001`, not containing `cbt-001`; consumed by `test_every_en_article_is_paired_deferred_or_crisis_gated`.

- [ ] **Step 1: Edit `DEFERRED_AR`** — add and remove exactly:

```python
    "emotions-001":  "new topic in 2026-08 refresh; AR translation pending clinician-gated lane",
```

and delete the stale line `"cbt-001": "covered by psychoed skills and cbt_thought_record skill",` (its AR pair shipped and was graded PASSED 2026-08-12 — the dict's own comment says to remove entries when the pair ships).

- [ ] **Step 2: Run the pairing tests**

Run: `python3 -m pytest tests/test_corpus_integrity.py -q -k "paired or orphan or matches_en"`
Expected: PASS (emotions-001 deferred; cbt-001 satisfied by its real AR pair).

- [ ] **Step 3: Commit**

```bash
git add src/sage_poc/corpus_constants.py
git commit -m "chore(kb): DEFERRED_AR — add emotions-001, drop stale cbt-001 entry (AR pair shipped)"
```

---

### Task 8: Full verification pass

**Files:** none (verification only)

- [ ] **Step 1: Full corpus-integrity suite**

Run: `python3 -m pytest tests/test_corpus_integrity.py -q`
Expected: ALL PASS.

- [ ] **Step 2: Chunk preview over every changed article** (eyeball serving-shaped output — chunks are what users see as source passages)

```bash
python3 - <<'EOF'
import json, pathlib, sys
sys.path.insert(0, "src")
from sage_poc.knowledge.ingestion import chunk_text
for f in sorted(pathlib.Path("data/knowledge_corpus/en").glob("*.json")):
    a = json.loads(f.read_text())
    chunks = chunk_text(a["content"], is_crisis_content=a["is_crisis_content"])
    print(f"\n=== {a['article_id']}  ({len(chunks)} chunks)")
    for i, c in enumerate(chunks):
        print(f"  [{i}] {c[:110]}")
EOF
```

Expected: no chunk starts mid-heading; statement headings (with their R27 full stops) sit at chunk starts, not glued into a previous sentence. Any glued heading → fix the master's punctuation, re-run Task 4 Step 2 for that file, amend the family commit.

- [ ] **Step 3: Corpus audit script (imports the same constants)**

Run: `python3 scripts/audit_corpus.py`
Expected: clean exit; investigate any finding before proceeding.

- [ ] **Step 4: Repo-wide test suite** (corpus changes trigger the unit gate in CI since PR #47 — mirror it locally)

Run: `python3 -m pytest tests/ -q -x --ignore=tests/experiment_4_5`
Expected: PASS (or only pre-existing known-xfail items; anything new = stop and fix).

---

### Task 9: PR assembly

**Files:** none (git/GitHub)

- [ ] **Step 1: Push and open the PR**

```bash
git push -u origin feat/kb-corpus-refresh-2026-08
gh pr create --repo <owner>/sage-poc --title "KB corpus refresh: 19 clinician-approved articles (2026-08)" --body "<body per Step 2>"
```

- [ ] **Step 2: PR body must include:** (a) clinician approval statement + link/date for the 19 docs and the approved redline item list, **plus this sentence: "The number guard makes number-free corpus copy a machine-enforced editorial policy — no future corpus article can contain a helpline or emergency number (including 'call 999') without a deliberate CI change; the clinical team has been informed this is now CI-pinned, not convention."**; (b) the Task 3 Step 2 red-test output showing the OLD corpus failed the number guard (evidence the single-source gap existed and is now pinned); (c) the allocation table reference (this plan's path); (d) explicit note that AR content is deliberately stale pending the AR lane, with only source/citation synced — **v7 §5.3 assumes aligned pairs, so this divergence carries an owner and a clock (see Task 10 Step 4)**; (e) explicit note that merge arms deploy-time auto-sync — serving changes on next deploy, which the user schedules. End with the standing PR trailer.

- [ ] **Step 3: Master is PR-gated with the "Safety-surface unit tests" hard gate** — wait for green; no admin bypass (standing rule: flag, never use).

---

### Task 10: Post-merge / deploy checklist (user-owned trigger)

**Files:** none

- [ ] **Step 1: DO NOT deploy autonomously.** Per standing rule, prod push needs per-deploy permission. Surface to the user: "merged; corpus will auto-sync on next deploy — say the word."
- [ ] **Step 2: On the user-authorized deploy**, follow the existing deploy runbook (`scripts/deploy_prod.sh` from the deploy worktree; converge on behavior via `scripts/deploy_converge.sh`, never env-SHA).
- [ ] **Step 2a (BEFORE the deploy): capture the retrieval baseline.** Exp 4.5's pytest form is fully mocked, but its query corpus (`tests/experiment_4_5/query_corpus.py`, `QueryCase` list incl. `should_abstain` cases) is the probe set. Run it against the LIVE retrieval stack (same real-DB access pattern as `scripts/calibrate_knowledge_threshold.py`) and save per-query results (abstain?, top source_ids, top_similarity) to `docs/kb/2026-08-<dd>-retrieval-baseline-pre-refresh.jsonl`. This is the old-corpus baseline and cannot be captured after the sync.
- [ ] **Step 3: Live verification:** (a) server logs show `sync_corpus` reinserting the changed articles (content-hash mismatch path) and total article count 52 EN+AR files → expect chunk-count change vs the old 222; (b) one retrieval probe on an info_request turn returns a refreshed passage (new wording) with correct title + source URL on the source card; (c) crisis-card behavior unchanged (KB change must not touch it — regression-by-improvement rule: run one T2 crisis fixture end-to-end); (d) **retrieval regression compare:** re-run the Step 2a probe set post-sync and diff against baseline — investigate ANY of: abstain flips in either direction, expected-prefix hit drops, or a crisis-article source_id newly surfacing for a non-crisis/off-topic query (the abstain-threshold audit showed crisis content CAN surface off-topic; a full-corpus re-embed is exactly when that behavior shifts). Record the diff in the same docs/kb/ location.
- [ ] **Step 4: Record follow-ups** (report to the command session for the memory write — work sessions don't write memory): AR content refresh lane (18 stale-content pairs + emotions-001) queued for clinician **with a named owner and target date agreed with the user at merge time — the EN/AR wording divergence is live from deploy until that lane lands and must not sit unowned**; trauma-001/crisis AR still gated; graphify graph untouched (data-only change).

---

## Self-Review (completed at authoring)

- **Spec coverage:** 19 docs → 28 masters → 31 EN files: allocation table enumerates every doc and every existing ID; depression untouched; emotions added; AR sync scoped to the 18 paired files; redline gate is Global Constraint #2. Crisis number decision is implemented via approved-content + guard test.
- **Placeholder scan:** no TBD/TODO; all code blocks runnable as written; commit messages concrete.
- **Type consistency:** master format defined in Task 2 = format parsed in Task 4; guard test name identical in Tasks 3/5; worktree path constant across tasks.
- **Known judgment call surfaced:** section allocation for anxiety/stress families ("worst case scenarios" → anxiety-002; "constantly on edge" → stress-002) is editorial placement, not content change — flagged in the PR body for reviewer eyes.
