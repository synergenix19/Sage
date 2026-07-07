# Source-Card Affordance Labels — Implementation Spec — 2026-07-07

**Goal:** give the `X-Sage-Sources` cards a labelled lead-in ("Further reading" / "Watch" / mixed), type-aware, so KB sources stop appearing abruptly after the reply. **Scope: the frontend affordance layer (cdai) + one backend test assertion.** No prompt, no LLM-content, no backend behavior change.

**Approved (2026-07-07) with five conditions, all folded in below.** Core principle (ratified): the label is a **deterministic frontend string keyed on the header's actual card `type` values** — never a model-written lead-in. The model doesn't know the cards exist (they come from the backend header), so a generated lead-in can mislabel; a header-keyed label cannot. Same principle as the turn-aware bridge: deterministic affordance out of the probabilistic layer.

## 1. The label — type-keyed, one line, above the cards
Keyed on the set of `type` values in the parsed `X-Sage-Sources` list:

| Card mix | EN | Register | AR key (PLACEHOLDER — see Condition 1) |
|---|---|---|---|
| all `article` | "Further reading" | — | `sources.label.reading` |
| all `video` | "Watch" | — | `sources.label.watch` |
| `article` + `video` | "Learn more" | — | `sources.label.mixed` |

(Mixed = "Learn more" — type-agnostic for a read+watch mix; "Further reading" would be odd over a video, and the video card's play affordance already signals type. Registry makes this a one-line revision.)

- Rendered as a real `<h3>` (or `role="heading"`) above the card list — not a styled `<div>` — so it is a semantic landmark for screen readers.
- "Further reading," **never "Sources"** (clinical/citation register) and never "Recommended" (implies clinical endorsement). Endorsement-implication was flagged as a clinical-tone judgment — see Condition 2.

## 2. Cards
- **Article:** existing title + subtle article icon + source/publication sub-label (from `citation`). Meaningful title only — never a bare "Source" link (best practice: avoid vague labels).
- **Video:** thumbnail + **play affordance** + duration (a "watch" affordance, not a bare link). **KB-only boundary (Lane 2):** only *retrieved-knowledge* videos ride this channel; skill-step media is the separate `X-Sage-Skill-Media` channel (Item 3, deferred/approval-gated) and must not render here.
- Cap 3 visible (matches `_sources_header`'s 3-cap = L4 evidence budget); collapse any remainder behind "See more."

## 3. Visual hierarchy — the bridge stays primary (Condition 4)
Order: reply prose → **triage question (primary next action)** → labelled cards (secondary, subdued, below). This is a **design constraint, not a preference**: the turn-aware close just shipped depends on the triage question being the primary invitation; if the cards visually dominate, the UI undercuts the close. The cards are the *leave-the-conversation, self-serve reading* affordance; the question is the *stay-and-talk* affordance.
- a11y pass: label = real heading; cards = semantic `<ul>`/`<li>`; **RTL mirroring** (icons, chevrons, card alignment flip in Arabic); **≥44px tap targets**; visible focus states; left-border/subtle-shading to separate the reading block from the reply.

## 4. Arabic — HARD GATE, placeholder keys only (Condition 1)
The EN strings ship; the **AR strings do NOT ship from this spec.** Arabic copy must be authored + reviewed by a **native Emirati speaker in a real RTL context** (v7 quality-checklist requirement) — the reversed/garbled AR in the original recommendation table is exactly the RTL-authoring artifact this guards against.
- **Register decision — RATIFIED-PENDING-NATIVE-REVIEW (2026-07-07): neutral/MSA-leaning.** A section heading over resource cards is UI chrome, same register class as button labels and settings copy (Khaleeji = conversational surfaces, MSA = formal content, per the UI language rule); MSA-leaning also keeps the labels dialect-neutral for the broader GCC audience. The native Emirati reviewer **may overrule with rationale** (e.g. judging a warmer colloquial label better serves the therapeutic-rapport UI principle) — but they start from MSA-leaning as the recorded position, not an open question.
- Spec ships `sources.label.*` **placeholder keys**; the AR values land only after native review, entered via the copy registry with the sign-off line.

## 5. Governance — proportionate, but traceable (Condition 2)
Not the L2-template workflow. But this is user-facing copy in a clinical-adjacent product, and the "Recommended vs Further reading" endorsement question is a clinical-tone judgment. Requirement: a **lightweight copy registry** — versioned locale files with **one sign-off line per string set (reviewer name + date)**. UI copy gets the same traceability spine as everything else at a fraction of the ceremony. No approval-less hardcoded strings.

## 6. Tests (the two new assertions)

**6a. Prose/affordance boundary — from BOTH sides (Condition 3).** The label is deterministic, but the model *sees the L4 passages*, so nothing stops generated prose from also saying "here are some articles below" / "these resources" / a source count — redundant with, or contradicting, the label. Add a **negative assertion to the full-graph eval class**: on a KB (info_request + retrieved-sources) turn, the generated prose **never references the card UI** — no "articles below," "these resources/links," "see the sources," or counts of sources. Enforces the boundary from the prose side, not just the frontend side. (Belongs with `2026-07-07-info_request-fullgraph-eval.py`'s class.)

**6b. Safety-path suppression pin (Condition 5) — the one backend assertion.** Already structurally enforced: `server.py:_SOURCE_ALLOWED_GATE_PATHS = frozenset({"standard"})`, default-deny, and `_sources_header` returns `None` otherwise. Add a **pin** so a future edit can't silently widen it onto a safety path: assert `_sources_header({...gate_path: "crisis"...}) is None`, same for `scope_refusal` and `jailbreak`, and assert the allowlist stays `{"standard"}`. "Further reading" on a crisis-adjacent turn would violate the crisis-UX rules; this locks it out.

## 7. Already-correct, do not re-solve
- **Abstain:** no retrieval → no header → no cards, no label (cosine-abstain gate). No change.
- **Audit-traceability:** sources are a subset of `knowledge_passages` (audit-traceable to the turn's retrieval). No change.

## 8. Out of scope
Skill-step videos (`X-Sage-Skill-Media`, deferred/approval-gated); any prompt/LLM change; backend behavior beyond the 6b pin. Video **captions / Arabic subtitles** are a **KB-content-pipeline prerequisite** (flagged back to content, not built here) — a play button that passes tap-target checks over inaccessible media still fails WCAG in spirit.

## Build packaging
Frontend PR (cdai): label component + type-keyed copy (EN + placeholder AR keys) + video-card affordance + a11y/RTL + the 6a prose-boundary assertion in the shared eval class. Backend micro-PR (sage-poc): the 6b allowlist pin. AR strings land as a follow-up after native review (Condition 1) via the copy registry (Condition 2).
