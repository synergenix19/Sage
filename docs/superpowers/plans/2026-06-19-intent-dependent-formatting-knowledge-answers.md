# Spec — Intent-Dependent Formatting for Knowledge Answers (L4)

**Date:** 2026-06-19 · **Verified against codebase 2026-06-19** (file:line citations inline).
**Origin:** Abby competitive analysis §5.1 (`Docs/abby-analysis/2026-06-19-abby-system-prompt-reverse-engineering.md`). The only non-regressive borrow from Abby: info/psychoeducation answers read better with *light* structure, while Sage's plain-prose calm voice is correct for emotional turns.
**Scope:** Engineering-layer change in the **L4 knowledge composer block.** Does **not** touch `L0_persona` (clinical-authored, approved v2.2.0).
**Companion work:** KB / "further reading" design (Node 6 `knowledge_retrieve`, `knowledge_passages` in state).

> **Verification summary (what changed after reading the real code):** three claims in the first draft were wrong — (a) the outgoing turn is **not** sanitized (only history is); (b) `knowledge_passages` is written by **Node 6 only**, not the `knowledge_lookup` tool; (c) `info_request` routes to `knowledge_retrieve` **even with an active skill**, which makes the `active_skill_id` guard **load-bearing, not redundant.** All corrected below.

---

## 1. Problem

`L0_persona` v2.2.0 mandates, for **every** turn (`always_include: true`, `src/sage_poc/prompts/templates/L0_persona.json`):
> "FORMAT: Write in plain prose. … No emojis, no markdown."

Right for emotional support; it also flattens `info_request` / Ask-module / knowledge answers where short labeled points are more scannable. We want light structure **only** on grounded info answers.

## 2. Verified enforcement chain (why structure is not actively blocked)

| Layer | Code | What it does to outgoing format | Blocks lists/line-breaks? |
|---|---|---|---|
| **L0 prompt** | `L0_persona` v2.2.0 (system role) | *Instructs* model: plain prose, no markdown/emoji | **This is the only real suppressor** |
| **`_sanitize_assistant_turn`** | `composer.py:29`, **called only at `composer.py:430`** | Strips `**`/`*`/`—`/emoji — **but only on CONVERSATION HISTORY (`m["content"]`), NOT the outgoing turn** | No (and never sees the live response) |
| **`_FORMAT_VIOLATIONS`** | `output_gate.py:29`, used at `:412` | **Log-only** `findall` (warns; no retry, no rewrite) on `—`/`**`/emoji | No |

**Two consequences:**
1. **Nothing strips the live response.** Lists/newlines we permit will reach the user intact — good. But stray `**bold**`/emoji from the model would *also* reach the user un-stripped (only logged). So the directive must firmly forbid bold/asterisks/emoji/em-dash, and T5 must verify the model complies.
2. **The only thing currently suppressing structure is the L0 *system-role* instruction.** That drives the precedence risk in §3.3.

> **Architecture deviation (not a quirk — Gap 1 from review).** v7 §5.5 / §5.6.2 define `output_gate` as the deterministic "safety net" that applies ALL rules post-generation via "string/pattern checks + transformations." A format guarantee resting on prompt-adherence + log-only telemetry is therefore a **deviation from the stated enforcement model**, and this spec *increases* exposure by granting structure permission (raising the odds of stray `**`/emoji reaching the user un-stripped). The architecturally correct fix is a **deterministic `output_gate` transform** that strips bold/asterisk/em-dash/emoji while preserving newlines + numbered lists (**T6**). Since DEV-B resolved (GPT-primary, 2026-06-20) the model prior is no longer retrainable in-house, this gate is now the *primary* style guarantee, so T6 is a **precondition of merge-enable** (see §4), not a fast-follow after it.
>
> **Side finding (surface to L0 owner regardless):** the `L0_persona` v2.0.0 draft note claims "ENFORCEMENT … `_sanitize_assistant_turn` (dashes/markdown/emoji)" guards output. Code shows it runs on **history only** (`composer.py:430`). A wrong enforcement note inside a clinically-approved file is worth correcting on its own, independent of this spec.

## 2.5 Cross-language evidence (Abby live probe, 2026-06-20)

How Abby handles this across languages, captured live (`Docs/abby-analysis/`):
- **Single `chatLanguage` flag drives ~90 languages.** The send envelope carries `chatLanguage` (from a profile/selector, default `en`); the same server-side prompt + GPT-4o answers in that language. **No content-based auto-detect:** Arabic input with an English selector returns *English* ("since you prefer English"). Sage's `detect_language` is already better here.
- **Identical markdown structure regardless of language.** Native Arabic (`chatLanguage:"ar"`) produced the same `### N. **header**` + bullet structure as English, in **MSA** (formal register — consistent with "psychoeducation = formal MSA").
- **Arabic quality tells:** English bleed-through (untranslated "even", Latin technical terms and citations inline), and it uses `**`/`—`/`###` — exactly the tokens Sage's gate targets. **Implication for this spec:** (1) light structure in Arabic is feasible and renders, so permitting it is reasonable; (2) but the forbid-tokens and RTL rendering must be **tested in Arabic, not assumed** (Abby did *not* honour any such forbid); (3) the T6 deterministic strip must operate correctly on Arabic — `—`→`, ` and stray `**` around Arabic text, including RTL — so T6 needs an Arabic test too.

## 3. Design

### 3.1 Gating signal (verified against state + routing)
```
allow_light_structure = (
    bool(state.get("knowledge_passages"))                 # see (a)
    and not state.get("active_skill_id")                  # see (b) — LOAD-BEARING
    and state.get("crisis_state", "none") == "none"       # see (c)
)
```
- **(a)** `knowledge_passages` (`state.py:64`) is written by **Node 6 `knowledge_retrieve` only** (`nodes/knowledge_retrieve.py:31,45`; init `server_helpers.py:184`). The `knowledge_lookup` *tool* does **not** write it (`freeflow_respond` has no writer — confirmed). So this fires for **Node-6 `info_request` answers only**, never for mid-conversation tool-lookups. That is desirable scoping: tool-lookups are woven into emotional/skill turns and should stay prose. *(NB: the composer comment at `composer.py:820` says "Node 6 retrieval or knowledge_lookup tool result in state" — that comment is misleading; the tool path does not populate this field.)*
- **(b) LOAD-BEARING.** `_route_after_skill_select` (`graph.py:228-235`) routes `info_request` → `knowledge_retrieve` **regardless of `active_skill_id`** (skill is preserved across the turn). So `knowledge_passages` **can** co-occur with an active skill (a mid-skill info detour). Without this guard, a user mid-CBT-exercise who asks a definition would get a jarring bulleted list. The guard keeps mid-skill turns in prose. (Earlier draft wrongly called this redundant.)
- **(c)** Active crisis never reaches Node 6 — `safety_check` routes it to `crisis_response → END` (`graph.py:272`). So this guard only affects `monitoring`/`resolved` aftercare turns that *do* pass through Node 6; suppressing structure there is a deliberate gentle-during-aftercare choice.
- **Abstain** needs no separate guard: `bool(knowledge_passages)` is False on abstain (empty passages), and `_build_l4_knowledge_block` already returns the abstain instruction via an early branch (`composer.py:308-313`) before any structure directive.

### 3.2 Where the permission text lives (template-driven)
`_build_l4_knowledge_block(passages, abstain, variant)` (`composer.py:303`) renders `L4_knowledge.json` via `tmpl.content.format(passages=...)`. The template (v1.0.0, **`approved_by: null`** — never formally signed off, so lower-stakes to edit than L0) exposes only `{passages}`.

**Change:** add a new `{format_directive}` variable to `L4_knowledge` (default `""`), bump to **v1.1.0**, and have `_build_l4_knowledge_block` accept `allow_light_structure: bool` and pass the directive only when true. The directive (no em-dashes per repo rule):
> "For this informational answer you may organise the response as a few short, plainly worded points on separate lines or a simple numbered list when it improves clarity. Lead with a one sentence plain prose answer first. Do not use bold, asterisks, headings, emoji, or dashes. Keep the warm, plain Sage voice."

The abstain branch (returns before template render) leaves abstain answers in prose automatically.

### 3.3 Precedence risk + fallback (key open question)
L0's "no markdown" is **system role**; the L4 block is **user role** (`L4_knowledge.role: "user"`). Models generally weight system instructions above user-turn content, so the user-role permission **may not reliably override** L0. Two options:

- **Option A (try first):** keep the permission in the L4 user block (above). Lowest stakes, fully template-driven, zero change to system prompt. **Gate on T5 behavioural check.**
- **Option B (fallback if A doesn't override):** in `compose_prompt`, when `allow_light_structure`, append the one-line permission to `system_str` *after* the L0 content (engineering-layer injection; L0 *file* still untouched). More reliable override, slightly higher stakes (a quasi-persona instruction at system level → same clinical courtesy review).

Recommendation: build A, measure with T5; escalate to B only if A fails to produce structure. Do **not** make `L0_persona` itself conditional (it is static, `variables: []`, and clinically approved — changing it reopens sign-off, which this spec exists to avoid).

### 3.4 Further-reading block (companion, not this PR)
External links are composed/rendered as source chips, not model markdown, so they sit outside both the sanitizer and `_FORMAT_VIOLATIONS`. This spec covers body formatting only.

## 4. Tasks (TDD)

- [ ] **T1 — Template: add `{format_directive}`.** Edit `L4_knowledge.json` → add `{format_directive}` to `content` + `variables`, bump version 1.0.0→1.1.0. Test (`test_prompts_loader.py`): template loads, both vars resolve.
- [ ] **T2 — Composer: gate + pass-through.** `_build_l4_knowledge_block` gains `allow_light_structure: bool`; compute it in the L4 section of `compose_prompt` (`composer.py:820-827`) and pass through; inject the directive only when true. Tests (`test_prompts_composer.py`): (i) `knowledge_passages` present + no skill + crisis_state none → directive in user string; (ii) active_skill_id set → NO directive; (iii) crisis_state "monitoring" → NO directive; (iv) abstain (empty passages) → NO directive, abstain instruction still present.
- [ ] **T3 — Pin the sanitizer contract (regression guard).** Test that `_sanitize_assistant_turn` leaves a numbered/line-broken sample unchanged but still strips `**bold**`/`*italic*`/`—`/emoji — documents the contract this spec relies on. (Does **not** add output-turn sanitization; that is a separate decision — see §2 side finding.)
- [ ] **T4 — Bilingual behavioural gate (Option A validation, REQUIRED before merge-enable).** Do **not** certify on English alone (Phase-0 discipline in miniature). Run, at minimum:
  - **EN info_request** ("explain what anxiety is and why my body reacts") → prose-lead + light list, no bold/emoji/dash.
  - **EN emotional** ("I feel anxious for no reason") → plain prose, no list.
  - **AR info_request** (e.g. "اشرح لي ما هو القلق ولماذا يتفاعل جسمي") → (a) light list renders correctly **RTL**; (b) model **honours the forbid in Arabic** (no `**`/`—`/emoji — Abby did not); (c) **no English bleed-through** in the structured Arabic; (d) **MSA** register for the formal psychoeducation answer.
  - If the info answer stays prose (L0 system precedence wins) in either language, switch to Option B (§3.3) and re-run. Merge-enable only when **both languages** pass.
  - **Native reviewer (⚠️ UNASSIGNED — part of T4 definition-of-done, not optional):** the Arabic checks (MSA register, no English bleed-through, RTL correctness) cannot be self-graded by a non-Arabic-speaking engineer — the Abby probe proves the failure mode (untranslated "even", inline Latin terms) is invisible to an English reader. A named native MSA/Khaleeji reviewer must sign the AR case before T4 counts as passed. Same human dependency as the Phase-0 Khaleeji slice, in miniature.
- [ ] **T5 — (Optional) telemetry annotation.** Tag the `output_gate.py:412` violation log with `allow_light_structure` so structured knowledge answers are distinguishable from emotional-turn violations. Low priority.
- [ ] **T6 — Deterministic output_gate format-strip (PRECONDITION OF MERGE-ENABLE — load-bearing since DEV-B resolved 2026-06-20; owner: ⚠️ UNASSIGNED — gate condition NOT met until a name is recorded here).** Move the "no bold/asterisk/em-dash/emoji" guarantee from prompt-trust to a deterministic `output_gate` transform on the live response, aligning with v7 §5.5/§5.6.2. Strip `***`/`**`/`*`/`—`→`, `/emoji while **preserving** newlines and numbered/hyphen lists. Tests:
  - (i) `**bold**`/emoji/em-dash stripped from a sample;
  - (ii) numbered/line-broken list preserved;
  - (iii) **Arabic sample** — `—`→`, ` and stray `**` around Arabic stripped, RTL list preserved, no MSA corruption;
  - (iv) **FALSE-POSITIVE GUARD (required):** a response that quotes a knowledge passage legitimately containing `*` (citation/footnote marker) or `—` is **not** mangled — the strip must not corrupt cited content. Without this, we trade probabilistic markdown leakage for deterministic citation corruption.
  This closes the §2 deviation. **Sequencing changed by DEV-B (2026-06-20):** GPT-primary was decided, so the model prior is fixed and not retrainable in-house, which makes the Node 8 gate the *primary* style guarantee, not a backstop. T6 therefore **precedes** merge-enable of the structure permission, it is NOT a fast-follow after it — the permission grants the model markdown latitude exactly when only this gate can reliably strip it. Provenance: `docs/superpowers/escalations/2026-06-16-dev-b-gpt-primary-architecture.md`, resolved 2026-06-20 (GPT-primary for pilot + likely future via sovereign endpoints).

**Task order to merge-enable:** T1–T3 (done) → T4 bilingual gate (Option A→A/B) → **T6 (precondition)** → clinical courtesy review → merge-enable. T6 moved ahead of merge-enable; it is no longer the trailing step.

## 5. Risks & mitigations

- **System-role L0 overrides user-role permission (most likely failure).** Mitigation: Option B fallback; T4 is the decision gate. **Medium.**
- **Model adds `**bold**`/emoji given list permission, and it reaches the user un-stripped (§2).** Mitigation: directive forbids them (probabilistic) **and T6 deterministic output_gate strip (precondition of merge-enable, load-bearing since DEV-B)** makes the guarantee deterministic per v7 §5.5. Confirmed live that Abby does not self-forbid these even in Arabic, so prompt-trust alone is insufficient. **Resolved by T6, which now ships before the permission is enabled.**
- **Structure leaking into emotional/skill/aftercare turns.** Prevented by the three-part gate (§3.1), covered by T2 negative tests. **Low.**
- **Voice drift toward Abby's markdown wall.** Prevented by "no bold/headings/emoji + lead-with-prose." Deliberately lighter than Abby. **Low.**

## 6. Approval note

`L0_persona` untouched → no L0 re-sign-off (Option A). `L4_knowledge` is `approved_by: null` today, so editing it does not break an existing sign-off, but the directive still changes user-facing behaviour for a turn class → recommend a **clinical courtesy review** of the one-line directive (and, if Option B is used, of the system-level injection per v7 §5.6.3, which routes system-instruction changes through review) before prod enablement. Not a blocker to build behind the gate.

**Merge-enable gate — currently UNMET on two human assignments (record names here before flipping):**
1. ⚠️ **Native MSA/Khaleeji reviewer for T4's Arabic case — UNASSIGNED.** Part of T4 definition-of-done; without it T4 self-grades on the engineer's inability to detect the bleed-through/register failure it exists to catch.
2. ⚠️ **T6 deterministic-strip owner — UNASSIGNED.** Since DEV-B resolved (GPT-primary, 2026-06-20), T6 is **load-bearing and now gates merge-enable itself** — the Node 8 gate is the primary style guarantee, not a backstop — so this name gates the L4 feature shipping *at all*, not just a follow-on. An unnamed task that gates shipping is the thing most likely to silently slip. T6 also requires the **false-positive guard (test iv)** so the strip cannot corrupt cited `*`/`—`.

T1–T3 are pure engineering with no clinical/behavioural dependency → clear to build now. T4 is the stop point where Option A/B, clinical courtesy review, and the bilingual judgment converge. This is POC composer work on a track separate from the Phase-0 routing harness — no dependency or competition — so it proceeds in parallel.

## 7. RTL rendering — direction architecture, and a named limitation

T4 surfaced that the L4 structure (numbered lists) had **never rendered end-to-end** — the frontend `message-bubble` rendered raw text with no `dir` and collapsed whitespace, so lists flattened to run-on text (silently in EN, visibly RTL-jumbled in AR). Fix shipped in two halves:
- **Frontend** (cdai `6929fb3`, `a87f588`): `whitespace-pre-wrap` + direction. Direction is **authoritative from the backend** (`X-Sage-Direction`), `dir="auto"` only the fallback. Closes "edge A" (an Arabic answer whose lead opens on a Latin token like "CBT" resolves LTR under `dir="auto"`'s first-strong-character heuristic).
- **Backend** (sage-poc L4 branch `0f5ed6f`): `text_direction(detected_language)` → `X-Sage-Direction` header on every assistant turn.

### Error/timeout paths — investigated, benign (decided, not deferred)
`X-Sage-Direction` rides the normal `/chat` header dict, so the **error and timeout paths emit no header**. The initial worry was that a fallback turn (malformed/mixed-script output) is exactly the edge-A case and would silently revert to `dir="auto"`. **Tracing the actual code dissolves that premise:** the error/timeout paths yield a fixed marker `[[SERVER_ERROR]]` (`server.py` `_timeout_err`/`_err`), and on `SERVER_ERROR_SIGNAL` the frontend **removes the assistant bubble entirely and shows a fixed English error string** (`chat-interface.tsx:122-125`, "Sage is having trouble responding…"). So **no answer bubble is rendered on those paths** — there is nothing for direction to apply to, and edge A cannot manifest. Every *rendered* assistant answer (normal + crisis, both via the header-dict path) carries authoritative direction. **Decision: do not add an inert header to the error paths.** The guarantee is therefore: *authoritative direction on every rendered assistant answer; error/timeout render no answer bubble.*

**Forward-guard:** if the error/timeout rendering is ever changed to show a *localized message bubble* (instead of removing it + a fixed English string), that change MUST carry direction (emit the header on those paths, or derive it client-side from the rendered content's language) — otherwise it reopens edge A. Pin this with a test on whatever renders the localized error.

### T4 verification record (2026-06-22) — criterion 4 signed off (rendering/UX)
End-to-end through the **running app** (not a mockup): Arabic "CBT" turn → real cdai chat UI → Next `/api/chat` → live sage-poc backend → `X-Sage-Direction: rtl` (captured at the socket) → `chat-interface` → bubble rendered **`dir="rtl"`**, RTL, numbered list intact, Latin "CBT" embedded. Playwright e2e (`edge-a-rtl.spec.ts`, throwaway) asserted `dir==='rtl'` and screenshotted `edge-a-real-render.png`. Clinician graded content criteria 1–3 PASS (MSA register, no bleed-through, forbid honoured); rendering criterion 4 verified here. **Cross-repo deploy gate:** confirm BOTH the backend header and the frontend consumer are *live in production* before merge-enable — either alone leaves edge A broken for real users while all tests stay green.

---

*Spec only; verified against the live codebase. Implement via superpowers:test-driven-development task-by-task. No memory writes from this work session (coordinator rule).*
