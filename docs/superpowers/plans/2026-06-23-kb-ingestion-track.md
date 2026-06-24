# KB Ingestion Track — Internal Vetted Content + External "Further Reading" Links

**Plan date:** 2026-06-23
**Owner:** TBD (engineering lead + clinical content lead — co-owned)
**Status:** PLAN — not started. Workstream B (external links) is **gated** on the policy in §B.0 being clinically signed off *before* any code.
**Relates to:**
- `2026-06-19-intent-dependent-formatting-knowledge-answers.md` (L4 light-structure — the render surface these answers land in)
- `Docs/abby-analysis/2026-06-19-abby-system-prompt-reverse-engineering.md` §5.1, §8 (competitive evidence + allowlist seed)
- `docs/SageAI_architecture_current.md` (Node 6 `knowledge_retrieve`, closed-RAG contract)

---

## 0. Why this track, and the one design decision that drives it

Sage answers info questions through **Node 6 `knowledge_retrieve`** — a *closed* RAG over the `knowledge_articles` pgvector table. If nothing is retrieved, it **abstains** (`knowledge_abstain=True`); it does **not** let the model free-associate clinical content. That abstain is by design and is Sage's core safety differentiator. Today the corpus is a thin sample, so real user info questions frequently hit abstain — which reads to a user as "it doesn't even know what anxiety is."

Two ways to close that gap:

### Option 1 — Grow the closed corpus + add vetted external "further reading" (CHOSEN)
Ingest clinician-vetted internal content (so Sage answers in *its own voice* from evidence it owns), and *optionally* append a small set of **pre-vetted, allowlisted, verified-at-serve-time** external links for users who want to read further. The model never invents a source or a URL; it only ever surfaces links that already passed review and still resolve.

### Option 2 — Let the model answer info questions from its general knowledge (CONSIDERED, REJECTED)
This is precisely what Abby does (`webSearch:false` default → GPT answers from parametric knowledge; see abby-analysis §2, §3b). It removes abstain and "feels" more capable. **Rejected because:**
1. **Unverifiable clinical content.** Abby's own citations are fabricated and drift run-to-run (abby-analysis §3b). When it *does* emit clickable URLs (§8b Run 2), they are model-generated and **unverified — 2 of 5 were dead 404s, only 1 confirmed live**. We would be shipping clinical claims, and links, with no provenance and no review.
2. **No clinical sign-off surface.** A parametric answer can't be reviewed before a user sees it; our governance model requires clinician-gated content.
3. **PDPL / safety exposure.** An ungated generative answer on a mental-health topic, in a regulated UAE pilot, with no human in the authoring loop, is not defensible.
4. **It dissolves the abstain invariant** that the whole crisis/safety architecture leans on.

> **Deviation-log entry (record this):** `DEV-2026-06-23-D — "Option 2 (model answers info_request from general/parametric knowledge, Abby-style) considered and REJECTED."` Rationale = §0 above. Closed-RAG abstain remains the contract; the gap is closed by corpus growth (Workstream A) + vetted external links (Workstream B), never by relaxing abstain.

---

## What already exists (do not rebuild)

The retrieval + ingestion spine is in place — these workstreams are **content + a thin link-surfacing layer**, not new infrastructure:

| Component | File | What it already does |
|---|---|---|
| Ingestion | `src/sage_poc/knowledge/ingestion.py` | `ingest_article()` validates schema, chunks (crisis content never split), embeds, upserts. **Required fields already include `source_url` and `is_crisis_content`.** Bilingual `-en`/`-ar` pairing enforced via `check_bilingual_pairing()`. |
| Schema | `knowledge_articles` table | `article_id, language, chunk_text, chunk_embedding, chunk_tsv, is_crisis_content, source_title, source_url, citation_metadata` (JSONB `{title, source_url, citation}`). |
| Retrieval | `src/sage_poc/knowledge/postgres_repository.py` | Hybrid vector+FTS RRF (`k=60`), abstain-on-empty. `KNOWLEDGE_ABSTAIN_THRESHOLD=0.0` — recalibrate once corpus ≥ 10 articles. |
| Node | `src/sage_poc/nodes/knowledge_retrieve.py` | Node 6; Arabic uses `raw_message` for FTS, English uses `message_en`; returns passages + abstain flag. |
| Render | L4 knowledge block + T6 strip (L4 plan) | Where answers + (future) further-reading land; light structure already permitted on knowledge answers. |

**Key consequence:** every KB article *already carries a `source_url`*. The internal article's own canonical source is the most trustworthy "further reading" link we have — Workstream B's first and safest link tier is **the `source_url` of the very articles we retrieved**, not a separate web search.

---

## Workstream A — Internal vetted content (clinician-gated authoring → ingest)

**Goal:** grow `knowledge_articles` from sample to a pilot-credible bilingual corpus so common info questions retrieve instead of abstain — answered in Sage's voice, from evidence Sage owns and a clinician approved.

### A.1 Authoring pipeline (process, not code)
Define and document the content lifecycle: **draft → clinical review → approve → publish → ingest**. Each article is clinician-authored or clinician-reviewed before it can be ingested. Mirror the existing skill-authoring governance (`docs/SKILL_AUTHORING_CONVENTIONS.md`) so reviewers work in one idiom.

- Article unit = the existing ingestion schema (`article_id, language, title, source_url, citation, content, is_crisis_content`).
- **Bilingual is mandatory**: every `-en` ships with its `-ar` pair (`check_bilingual_pairing` already warns; promote to a hard gate in the publish step). Arabic is authored/reviewed by an Arabic clinical reviewer — **not** machine-translated from English (consistent with L0 no-Arabic-coercion and the dialect work).
- `source_url` + `citation` per article point to the **authoritative primary source** the content is grounded in (this is the link Workstream B surfaces first).

### A.2 Initial topic set (pilot priority)
Seed the topics real users hit first and that today abstain. Candidate first batch (clinical to confirm/extend):
anxiety, panic attacks, low mood / depression basics, sleep hygiene, stress, grounding, breathing techniques, CBT (what it is), what Sage is / scope, when to seek professional help. Each as a bilingual pair.

### A.3 Recalibrate retrieval once corpus ≥ 10 articles
`KNOWLEDGE_ABSTAIN_THRESHOLD` is `0.0` (POC: abstain only on literal zero match). Once ≥ 10 articles, run `scripts/calibrate_retrieval_threshold.py` (per the in-code TODO) and set a real threshold so near-miss retrievals abstain rather than surface a weak passage. Add the BGE-reranker-v2-m3 pass noted in `postgres_repository.py` when corpus > 100.

### A.4 Crisis content stays single-chunk + Node 1 authoritative
`is_crisis_content=true` articles are never chunked (already enforced). Crisis info is **second-line** to Node 1's deterministic crisis path (UAE 800 46342 / 999) — KB never overrides it. (See §B.0 crisis-exclusion for the link side.)

### A.5 Translation track — REQUIRED clinical-faithfulness gate (do not skip)
Producing the `-ar` pair of an already-approved `-en` article is **translation, not authoring** — the clinical decision was made when the English was approved. That keeps it on the code-review side **only if the translation is a faithful rendering** (no adaptation, no reworded clinical instruction, no changed example). The boundary is real: a Khaleeji cultural adaptation, a "may"→"should" drift, or a reordered technique instruction turns it back into **new clinical content** that needs full authoring sign-off.

**The trap:** "faithful" is itself a clinical judgment. A non-clinical translator can produce a faithful-*sounding* MSA rendering that drifts on a clinical nuance, and the RAG+L4 path will retrieve and render the drifted version exactly as confidently as a correct one. **Retrieval/render tests prove the content flows; they do NOT prove it is clinically faithful.** (Same distinction as "structure renders" vs "register is right" from the T4 saga — an English reader structurally cannot catch an Arabic faithfulness drift.)

**Required gate for every translated pair, baked into the pattern (not appended after):**
1. Engineering produces the faithful translation + verifies schema / pairing / retrieval.
2. **A qualified Arabic clinical reviewer grades the translation for clinical faithfulness** before it is treated as approved-in-Arabic. This is a *required* step, not a flag-for-later.
3. The PR states which gate applies (faithful translation vs adaptation) so the reviewer knows.

**Hard carve-out — trauma and `crisis-*` (any `is_crisis_content=true`) do NOT use this track.** They go through the **same clinical authorship gate as original crisis content**, not "translated by engineering, verified by retrieval." A faithfulness drift in a breathing article is a quality bug; in a crisis/trauma article it is a safety event, in exactly the content class where the architecture is most deterministic *because* the stakes are highest. Do not let the smooth ingestion pipeline set the pace for these.

**Status — `cbt-001-ar` (shipped 2026-06-23, live in prod):** faithful MSA translation of approved `en/cbt-001`, but graded **only by engineering self-assessment — clinical faithfulness NOT yet verified by a qualified Arabic clinical reviewer.** Action: get it graded promptly (it is live). Do not ship the remaining 9 EN-only pairs until this A.5 gate is part of the pattern. Register delta (MSA vs Khaleeji corpus) separately flagged for the content owner.

### A — deliverables
1. Content lifecycle doc (draft→review→approve→publish→ingest) + reviewer checklist.
2. Bilingual-pair publish gate (promote `check_bilingual_pairing` warning → hard error in the publish path).
3. First bilingual article batch (§A.2), clinically signed off.
4. ~~Threshold recalibration~~ — **superseded**: measured 2026-06-23, no single-score cutoff separates relevant from off-topic; real fix is the BGE-reranker (see the calibration audit + reranker scoping). Threshold stays `0.0`.
5. **A.5 clinical-faithfulness sign-off gate** wired into the translation pattern; `cbt-001-ar` graded; trauma/`crisis-*` routed to clinical authorship.

---

## Workstream B — External "further reading" links (allowlist, verified, opt-in, crisis-excluded)

**Goal:** after an internal-KB answer, *optionally* offer a few links for users who want to read further — surfacing **only pre-vetted, allowlisted URLs that resolve at serve time**. The model never emits a link. This is the deliberate inverse of Abby's mechanism (§B.4).

### B.0 POLICY FIRST — write and clinically sign off BEFORE any feature code
This is the gate. No link-surfacing code merges until this policy is approved:

1. **Allowlist is the only source of links.** A link may be shown only if its domain (and ideally exact URL) is on a reviewed allowlist. No model-generated URLs, ever. No open web search at serve time.
2. **Verified-at-serve-time.** Every candidate link must resolve (HTTP 200, not redirected off-domain) at the moment it is offered, or it is dropped silently. No dead links reach a user. This is the concrete lesson from §8b Run 2: Abby emitted 5 plausible-looking URLs and **2 were hard 404s, only 1 confirmed live** — credible-looking dead links presented as real. Note 403 (anti-bot) is ambiguous, not proof-of-dead; verification must distinguish 404/410 (drop) from 403/429 (treat as live-but-protected, since allowlisted domains are pre-trusted).
3. **Crisis exclusion (hard).** If `crisis_state != "none"` OR the turn touched the safety path OR an active skill carries a crisis/SI/DV/trauma contraindication → **no external links at all.** Further-reading is a calm-state, info-request-only affordance. Node 1 crisis resources are the only links on a crisis turn, and they are deterministic.
4. **Opt-in / bounded.** Links are an explicit, secondary block appended to an info answer (not injected into emotional/venting turns). Cap the count (e.g. ≤ 3). Default off for any turn that isn't a clean `info_request` with a non-abstain KB answer.
5. **Re-validation cadence.** The allowlist is re-checked on a schedule (proposal: monthly automated link-liveness sweep + quarterly clinical content re-review). A link that fails liveness is auto-quarantined pending review. Record cadence + owner.
6. **No commercial / no PII-leaking destinations.** Non-commercial, authoritative, no tracking-param injection. (Note Abby appends `?utm_source=abby.gg` to outbound links — we add **no** tracking params.)

### B.1 Link tiers (safest first)
- **Tier 0 — internal article `source_url`** (lowest risk): the authoritative source of the very article we just retrieved. Already in `citation_metadata.source_url`. Surfacing this requires *no new sourcing* — just render what we already vetted at ingest. **Ship this tier first.**
- **Tier 1 — curated allowlist** of authoritative orgs for topics where we want further reading beyond our own source. Seed roster from Abby's institutional set (validated as credible in §8) **plus UAE/Gulf-sovereign sources**:
  - Global: **NIMH**, **APA** (psychiatry.org — the one URL confirmed live in §8b), **Mayo Clinic**, **Harvard Health Publishing**, **ABCT**, **ADAA**, WHO, NHS (patient-info pages — use verified canonical URL; Abby's emitted path 404'd).
  - UAE / regional (REQUIRED — clinical + sovereignty to confirm exact pages): UAE National Program for Happiness & Wellbeing, Estijaba / SEHA, Dubai Health Authority mental-health pages, the 800 46342 (Estijaba) service page. These take precedence for a UAE pilot.
- **Tier 2 — videos / communities:** Abby also surfaces YouTube/TED and Reddit/forums (§8a). **Defer / likely reject for pilot** — community links (Reddit, forums) are unvettable and unsafe for a clinical product; video links need per-video clinical review. Record as out-of-scope for pilot unless clinical explicitly wants a vetted-video allowlist.

### B.2 Mechanism (engineering, gated on B.0)
- A `further_reading` resolver that, given the retrieved `knowledge_passages` + the allowlist, returns ≤ N `{title, url}` items: Tier 0 source_urls of retrieved articles first, then topic-matched Tier 1 allowlist entries.
- **Liveness check at serve time** (cached with short TTL to avoid latency hit; drop on failure).
- Hard guard: returns `[]` whenever the §B.0.3 crisis-exclusion predicate is true. Unit-test that predicate directly (parallels the contraindication-firing-gap concern — a behavioural test, not just a config).
- Render as a distinct, secondary "Further reading" block under the L4 answer (RTL-correct in Arabic via the existing `X-Sage-Direction` header; links themselves are LTR URLs but the block label/framing follows answer direction).

### B.3 Allowlist as data + review trail
Store the allowlist as a reviewed data file (domain, allowed-URL or pattern, topic tags, reviewer, review date, last-liveness-check). Treat edits like skill content: clinical sign-off + a governance entry (no silent allowlist edits — cf. the unaudited-keyword-changes lesson).

### B.4 What we are explicitly borrowing vs. rejecting from Abby
- **Borrow:** the three-channel Discover product idea (articles primarily); the institutional roster as an allowlist seed; the opt-in-tool posture (links are a deliberate affordance, not default).
- **Reject:** model-*emitted* URLs (§8b Run 2 — 2/5 dead); open serve-time web search as the link source; community/forum links for a clinical product; outbound tracking params; links on crisis/emotional turns. Also note the **new allowlist candidates surfaced in Run 2**: ADAA (Anxiety & Depression Association of America) and the NHS UK patient-info pages are credible Tier-1 additions — but add the *verified canonical* URL, since Abby's emitted NHS path 404'd.

### B — deliverables
1. **`B.0` policy doc, clinically signed off** (the gate — blocks everything below).
2. Allowlist data file + review trail (§B.3), starting with Tier 0 + UAE Tier 1.
3. `further_reading` resolver with crisis-exclusion guard + serve-time liveness check (§B.2).
4. Behavioural tests: crisis-exclusion returns `[]`; abstain answer surfaces no links; dead link dropped; cap enforced; RTL block render.
5. Re-validation job (link-liveness sweep) + documented cadence/owner (§B.0.5).

---

## Sequencing

1. **A first, B.0 in parallel.** Grow the corpus (A) — that alone removes most abstains and is pure clinician-gated content, no new risk surface. Simultaneously draft + sign off the B.0 policy.
2. **B Tier 0 next** (surface retrieved articles' own `source_url`) — highest-value, lowest-risk link tier, no new sourcing.
3. **B Tier 1 (UAE-first allowlist)** after policy sign-off.
4. Tier 2 (videos/communities) deferred — revisit post-pilot only if clinical wants it.

## Open governance items (relay to command session — not written to memory from here)
- `DEV-2026-06-23-D` — Option 2 rejected (see §0). Land in the consolidated deviation register alongside `DEV-2026-06-19-C`.
- v7 §5.4 Falcon→GPT-primary reconciliation (separate, already tracked) — note that GPT-primary makes the closed-RAG abstain + Node 8 gate the *primary* content-integrity guarantee, which is exactly why Option 2 is rejected.
- Owner-confirmation: A and B are co-owned (engineering + clinical content lead); assign named owners.
- Phase-0 owner: witnessed-restore notice still to be relayed (carried over).

---

*Plan authored by work session. Per repo memory-coordinator rule (CLAUDE.md), no memory writes from here — governance items above are surfaced in-conversation for the command session to reconcile.*
