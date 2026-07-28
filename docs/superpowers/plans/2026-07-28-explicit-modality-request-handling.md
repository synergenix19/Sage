# Explicit Modality Request Handling — Re-plan Draft (v1, supersedes §1a binder Phase 1)

> **Status: DRAFT for review.** Supersedes Phase 1 of
> `2026-07-28-1a-skill-request-delivery.md` (v3), whose Phase 0 evidence and
> screening/governance content (B1/B2/C1/C2, packet asks) carry forward unchanged.
> No implementation until this draft is approved. Named for the defect class, not the
> mechanism or the spec section.

**Defect class:** active or passive dropping of a user's explicit request for a
coping tool ("are there any exercises i can do"). Three observed dropping surfaces
(mechanism memo + rerun addendum): (1) active-skill absorption via
`skill_continuation` → executor exploration step; (2) request classified
`info_request` → early-return → KB abstain → freeflow; (3) request over a pending
offer classified `offer_ignored`. Plus DF-1: when an offer does fire, semantic rank
serves psychoed/worry_time/PMR, never the spec's first-line pair.

**Goal:** an explicit modality request, in a screened context, always resolves
against the clinical binding table — regardless of which way the LLM intent
classifier lands.

## Architectural constraint (review-imposed): ONE deterministic detector, THREE consumers

`explicit_modality_request` is computed deterministically, once per turn, BEFORE and
independently of the LLM intent classification, and carried in state. Substring pass
over the request lexicon, no model call, no discretion. One lexicon, one matcher, one
binding table; the executor, the info_request early-return, and the offer-reply
resolution consume the same flag. This neutralizes the Node-2 bistability finding
for this defect class: all trajectories converge on the same deterministic signal.
(Cardinal Rule 4, one layer out: an explicit ask for a tool is not a probabilistic
inference and is not routed through one.)

**Sequencing rider:** the detector must not disturb Node 1 precedence. Safety runs
first, always; crisis and medical red-flag turns terminate before `intent_route`
(rerun-verified: cardiac probe path is `[safety_check, medical_response]`), so the
detector never sees them. **Placement rider:** NOT in `safety_check` (purely a
safety surface). A deterministic pre-pass at the head of `intent_route`, writing
state before the LLM call.

## Ordering ownership (DF-1) and the V2 dependency

Raw semantic similarity cannot express clinical first-line ordering — general
statement, true for all 28 structured skills, same root problem as the V2
semantic-routing workstream (currently flag-off, blocked on the G6 HarnessConfig
re-gate). Division of ownership, stated for the packet: **the binding table owns
clinical first-line ordering for explicitly requested modalities** (spec offer
tables, clinician-signed rows); **V2 owns retrieval quality for inferred
presentations**. This plan does not touch V2 surfaces; the V2 record gets a
cross-reference so ordering has exactly one owner per entry path. If V2 later ships
a calibrated ordering layer, the binding table remains the spec-conformance
authority for request-path first-line choices unless a joint decision merges them.

## Carried forward unchanged from v3 (not re-litigated here)

- Screening gates delivery (B1+C1): adaptive screen, duration mandatory,
  conditional red-flag clause, cleared-from-disclosure; `chronicity: unknown` never
  passes. Clinical questions doc already drafted for Vee.
- C2 chronic-case adjudication (alongside vs instead-of) pending Vee.
- Language gate (B2): AR sessions skip until validated (translated `message_en`
  WILL match the EN lexicon otherwise).
- Single symptom-matcher surface in `matching.py` (M2), `recent_presentation` as
  Active-Issues stand-in (M1), clinical-flag positive guards (M3/C3), no em dashes
  in rule content, default-OFF flag, clinician sign-off hard-blocks prod.

## Phase 0 — Fresh distributional baseline (BEFORE any fix lands)

The v5 §1a 2/5 is invalid as a comparator on two grounds (mechanism change since
v5; single-run measurement). Task: author the multi-turn request-conformance
fixture family (the three-surface trajectories + the v3 naturalistic set), run it
N=10 per fixture at the serving SHA under readback-derived flags (uses the
follow-up-1 instrument rule; blocked on that helper landing), and record per-fixture
outcome DISTRIBUTIONS (offer-rate, per-surface mechanism counts) as the baseline.
Distributional stability of the fixtures themselves is part of the readout.

**Baseline artifact header block (template-setting — first artifact under the new
instrument regime, will be cited as the pattern):** full resolved flag set, build
SHA, classifier model + provider + requested seed + seed-honor signal
(system_fingerprint or provider equivalent, null if unexposed), N per fixture,
per-trajectory frequencies. `SAGE_AUDIT_CLASSIFIER_PROVENANCE` must be ON for the
run (register ruling): an unrecorded-provenance baseline fails the signed
instrument-parity rule. Sequencing: pins branch lands → architecture review vs
Q-a/Q-b → deploy owner activates pins + provenance in the evidence environment →
parity helper confirms via readback → baseline runs.

## Phase 1 — Detector (one task)

`matching.detect_explicit_modality_request(message_en, raw_message, lang) ->
{"requested": bool, "modality_hint": str|None}` over the v3 request lexicon
(same data file, same governance). New state channel
`explicit_modality_request: dict|None`, declared + manifest + graph seam test,
**reset every turn** (it describes THIS turn only — unlike `recent_presentation`).
Written at the head of `intent_route` before the LLM call. Behavior-anchored tests:
flag set on lexicon-superstring messages, not set on curiosity asks ("why does my
body react like this?"), not set on bare affect ("anxious"), language gate observed.

## Phase 2 — Consumers (one task per surface, each with per-surface positive-path guards)

1. **Executor (surface 1):** on `explicit_modality_request` with an active skill,
   evaluate the exit-and-rehand route BEFORE step advancement, expressed as
   escalation-matrix L1 data (user-initiated departure family, per review C-c:
   "request-for-alternative" is the same family as §9.2 rule 5) — clinician-authorable
   JSON, one generic executor capability (exit-with-warm-handoff → `skill_select`),
   no per-skill code. Both-direction guard: mid-skill affirmations ("this is
   helping") never trigger it.
2. **info_request early-return (surface 2):** consult the flag before the KB
   short-circuit; requests route to binding-table candidates through the consent
   gate instead of knowledge_retrieve. Guard: genuine info asks ("what's the crisis
   helpline number?") still reach KB, asserted positively.
3. **Offer-reply resolution (surface 3):** pending offer + flag → resolve against
   the pending candidates and the binding table (requested modality ∈ offer →
   promote; else first-line re-offer, declined-filtering preserved). Guard: actual
   ignores ("anyway, about work...") still release the offer.

All offers flow through the existing R1 consent gate; screening (Phase-1-of-v3
gates) applies at the delivery point in every surface. All guards assert the
positive alternative path (C3).

## Phase 3 — Measurement + packet

Re-run the Phase-0 fixture family distributionally (same N, same instrument);
report per-surface deltas against the fresh baseline; conformance-neutrality sweep
on non-request categories; fold into the §1a packet (screen copy, C2 adjudication,
AR asks, deviations, V2 ordering-ownership statement, measurement-validity
statement). Flag flip remains sign-off-gated.

## Naming

Flag: `SAGE_MODALITY_REQUEST_ROUTING` (replaces `SAGE_SKILL_REQUEST_DELIVERY` from
v3, which was never implemented). No component is named "binder". Path markers:
`modality_request_detected`, `modality_request_routed:<surface>`,
`modality_request_screen_pending`, `modality_request_referral_context`.
