# Design Spec — Sentence-Buffered Response Streaming (v7-compliant)

**Date:** 2026-06-23
**Status:** Design approved (brainstorming). Implementation NOT started.
**Scope:** Replace the current fake streaming with real, progressive, **sentence-granularity** streaming of assistant responses, while preserving every Node 8 (output_gate) guarantee of the v7 contract.
**Flagged per Absolute Rule 1:** this is an architectural deviation from v7 §4 / §5.5 / §13.1. It ships only under the four guardrail conditions and the per-rule promotion gate recorded below.

---

## 1. Motivation

Today's "streaming" is **fake**: `server.py` runs the entire graph via `graph.ainvoke` (buffered), obtains the complete `response`, then chunks that finished text out token-by-token (`_stream_tokens`). The first byte therefore arrives only **after** the whole turn completes (~15–30s). `freeflow_respond` uses `llm.ainvoke`, not `astream`.

Real streaming improves **time-to-first-paint** to ~2–4s and makes a slow-but-valid turn render progressively instead of appearing as a stall/failure.

### 1.1 Latency caveat (must be stated to the client)

Streaming fixes **time-to-first-paint**, **not total latency**. It must **not** be reported against the CRISP-DM **<3s p95 total-response** KPI.

- In the **POC**, the 15–30s total is driven by **OpenAI `gpt-4o` + multiple sequential LLM calls per turn (classifier, responder, banned-opener retry, translation) + cross-region DB (SFO API ↔ Mumbai Supabase)**.
- In the **production target**, total latency is a **Falcon-34B (Node 7) inference** problem.

Both are Node-7 total-latency concerns, separate from first-paint. Streaming masks total latency perceptually; it does not meet the p95 KPI. The **banned-opener retry (~21% of casual turns)** delaying first paint is the correct, load-bearing cost and **stays**.

---

## 2. Approach — Sentence-Buffered Streaming Pipeline (chosen)

Generate via `astream`; accumulate tokens into **sentences**; run the output_gate **per sentence** as each completes; emit each sentence only after it passes its gates. Sentence granularity (not a token typewriter) is **required**, not a preference — Arabic translate-back and question-discipline need complete sentences (Condition 4).

Rejected alternatives:
- **Token typewriter + post-hoc correction** — makes the gate best-effort (cannot un-send a streamed banned opener; AR translation can't go token-by-token). Breaks "cultural rules applied at output_gate (not optional)" + Cardinal Rule 4.
- **Two-phase (instant safe opener + full reply)** — doesn't stream the substance; a trick.

### 2.1 Architecture & portability

- Transport: **SSE**.
- The sentence buffer + gate lives at the **Node 7 → Node 8 boundary** (`freeflow_respond` → `output_gate` → user). `freeflow_respond` switches from `llm.ainvoke` to the existing astream primitive (`resilience/__init__.py:253`, `llm.astream`).
- **No graph topology change** — still the 8 nodes, same `freeflow_respond → output_gate → user` path. Maps cleanly to Azure UAE North with no rewrite.
- During POC, AR translate-back may use an external translation API (no data-sovereignty requirement now). The Node 7→8 boundary is identical when Falcon/MARBERT move in-region.

---

## 3. The four guardrail conditions (deviation guardrails)

1. **Gate-rule partitioning is mandatory and exhaustive.** Every output_gate rule is classified **per-sentence** (safe to stream after gating) or **whole-response** (held to end-of-turn / buffered). *An unclassified rule is a safety hole and does not stream.*
2. **One audit record per turn (§13.1).** The single traceable record (path, skill, step, prompt hash, model version, retrieval IDs, cultural rules applied, latency) is **assembled and written at turn close**, never fragmented per sentence.
3. **Streaming DISABLED on crisis and escalation paths.** Node 1 → crisis_protocol and L3/L4 escalations render as **complete, pre-validated scripts** with helpline one-tap (UI/UX rule 5, Cardinal Rule 4). Streaming applies only to Nodes 3 and 7 on **safe** paths.
4. **Arabic granularity is sentence-level by necessity.** detect → translate → process → translate-back requires complete sentences; this is why token-level is impossible. Per-sentence translation latency on AR turns is accepted.

---

## 4. Replacement-rule class decision (the hard case)

CUO-ID-001 (identity/impersonation substitution) is **not unique** — it is one instance of a **class**: whole-response-replacement rules that can fire on **generated** content:
- identity / impersonation substitution (CUO-ID-001),
- unprompted diagnosis / scope leakage,
- jailbreak compliance.

`scope_refusal` is "non-streamed (whole script)" **only** when the violation is caught at **routing (Node 2/4) before** freeflow generates. A scope violation the model **volunteers mid-generation** lands in the exact same place as CUO-ID-001: partial emit, cannot retract. The decision is therefore made **for the class**, not per rule.

### 4.1 Decision rule (safety-first, auditability-first)

- **Default = (b) buffer.** Unclassified replacement rules **do not stream**. Freeflow turns **buffer** until a rule is proven promotable. **Streaming is opt-in per rule, not opt-out.**
- **Promote a rule to (a) substitute-remainder-and-halt** only when the audit proves **both**:
  1. it is a **deterministic pattern/string check** (v7 §5.5 — cultural rules are exactly this; impersonation is a lexical identity claim like "as your doctor…", very likely sentence-local), **and**
  2. its verdict is **computable from the current sentence plus the already-emitted-clean prefix, with zero dependence on un-emitted future sentences**.
- **Acceptance test for promotion:** the **gate-equivalence test** (streamed output == buffered output) passes for that rule, **plus** clinical/architectural sign-off (it changes substitution semantics).
- **Irreducibly whole-response rules stay (b)** AND are **pushed upstream**: route known scope/diagnosis/jailbreak intents to **scripts at Node 2/4** before freeflow ever streams. This shrinks the buffered set to **model-volunteered** violations only (rare on safe paths).

### 4.2 Why (a) is clinically defensible for impersonation

When CUO-ID-001 fires on sentence N, every prior **emitted** sentence already passed the **full** per-sentence gate (not just the identity check) — independently clean, non-impersonating, non-diagnostic. The canned correction **disclaims the false identity in the same turn** (satisfies persona-robustness, Intelligence Eval T-11). The user never receives an un-corrected impersonation. This is a defensible refinement of "replace whole response" → "correct from the violation point." **Write the sign-off treating CUO-ID-001 as an identity-robustness rule (L3-adjacent), not a generic cultural rule.**

### 4.3 Correctness guard on (a)

"Substitute-remainder-and-halt" is sound **only if** the canned correction reads coherently appended after the clean prefix, i.e. the clean prefix cannot be semantically poisoned by what follows. Concretely: if sentence 1 = "your symptoms sound serious" and sentence 2 = impersonation, sentence 1 must **already have failed the per-sentence scope/diagnosis check on its own**.

**Mandatory invariant:** the per-sentence gate runs **scope + diagnosis checks on every sentence**, independently. Otherwise the halt point can leave a standalone scope/diagnosis violation emitted.

---

## 5. Gate-rule partitioning (current classification — to be made exhaustive by the §7 audit)

| Output_gate operation | Class | Streaming behavior |
|---|---|---|
| Banned-opener detect + retry (`^`-anchored) | per-sentence | gate sentence 1; retry regenerates **before** any emit |
| T6 format-strip (`_strip_output_format`) | per-sentence | strip each sentence before emit (small token-pair buffer for `**`) |
| Question-discipline (`_limit_to_one_question`, `_strip_trailing_question`) | per-sentence + stateful holdback | emit first question, drop later question sentences |
| Per-sentence scope + diagnosis check | per-sentence (REQUIRED, §4.3) | every sentence, independently, before emit |
| Arabic translate-back (`async_translate_to_arabic`) | per-sentence | translate each EN sentence → emit AR (Condition 4) |
| `cultural_output` substitution / identity (CUO-ID-001 and class) | **(b) default → (a) on per-rule promotion** | §4 decision rule |
| `scope_refusal` / `jailbreak` hardcoded paths | non-streamed | whole pre-validated script (push upstream where possible) |
| Crisis / L3–L4 escalation | non-streamed (Condition 3) | complete pre-validated script + helpline one-tap |
| Session audit record | whole-turn, at close (Condition 2) | one record assembled at turn end |

---

## 6. Data flow

1. Routing (Nodes 1–2/4) decides path. **Crisis / escalation / scope / jailbreak / known-script intents → non-streamed** complete scripts (Condition 3; §4.1 upstream routing).
2. Safe freeflow path: `freeflow_respond` calls `llm.astream`; tokens accumulate into a sentence buffer.
3. On each completed sentence, the **per-sentence gate** runs: scope+diagnosis (§4.3), banned-opener (sentence 1), T6 strip, question-discipline holdback, promoted replacement-rule checks, then AR translate-back for AR turns.
4. A clean sentence is emitted over SSE. A sentence that trips a promoted replacement rule → emit the canned correction, **halt** the stream.
5. At turn close: assemble and write the **single** session_audit record (Condition 2), including `latency_ms` and `cultural rules applied`.

---

## 7. Implementation ordering — BLOCKING FIRST TASK

**Task 0 (blocking): full `cultural_output` rule-set audit.** Classify **every** rule as per-sentence-decomposable vs irreducibly-whole-response, against the §4.1 promotion criteria. **No streaming ships for any replacement rule until that rule passes the audit** (gate-equivalence + sign-off). Until a rule is promoted, its turns buffer (default (b)).

Subsequent tasks (sequenced in the implementation plan): astream wiring at Node 7; the sentence buffer/gate component; per-sentence gate (scope/diagnosis/banned-opener/T6/question-discipline); AR per-sentence translate-back; SSE transport + frontend consumption; non-streamed crisis/escalation path; one-record-per-turn audit assembly at close; upstream routing for known scope/diagnosis/jailbreak.

---

## 8. Error handling

- **Mid-stream LLM failure after partial emit:** cannot retract; emit a terminal error sentinel and mark the turn **degraded** (no silent truncation).
- **Banned-opener retry** happens **before** first emit, so regeneration is safe (nothing emitted yet).
- **Crisis/escalation** never enter the streaming path (Condition 3).
- **Promoted-rule halt** emits the canned correction as terminal content.

---

## 9. Testing

- **Gate-equivalence:** for every promoted rule and the overall pipeline, streamed output **==** buffered output for the same generated response. This is also the per-rule promotion acceptance test (§4.1).
- **Adversarial impersonation-mid-stream:** a response that impersonates at sentence N → user never receives an un-corrected impersonation; prior sentences were independently clean; canned correction emitted; halt.
- **Standalone-violation guard (§4.3):** a response with a scope/diagnosis violation in an early sentence fails that sentence's per-sentence check (never emitted as a standalone violation).
- **AR per-sentence translate-back fidelity.**
- **Crisis-path-not-streamed** assertion (Condition 3).
- **One audit record per turn** assertion (Condition 2).

---

## 10. Non-goals / out of scope

- Reducing **total** response latency (separate Node-7 generation/inference work: streaming, fewer sequential calls, region co-location, model choice). This spec is **first-paint only**.
- Token-by-token typewriter rendering (incompatible with the gate contract; §2).
- Native-Arabic generation (the pipeline keeps EN-generate → AR translate-back).

---

## 11. Open items requiring sign-off before/within implementation

- **Clinical/architectural sign-off** to promote each replacement rule from (b)→(a), treating CUO-ID-001 as an identity-robustness (L3-adjacent) rule (§4.2).
- Output of the **Task 0 cultural_output audit** (which rules are promotable).
- Confirmation that the per-sentence **scope + diagnosis** checks exist or are added (§4.3 invariant).
