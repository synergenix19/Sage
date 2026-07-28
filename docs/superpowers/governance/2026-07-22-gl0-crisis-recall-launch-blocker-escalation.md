# GL-0 crisis recall — the LAUNCH BLOCKER · re-escalation to PO (2026-07-22)

**Reframed, correctly: this is not "the platform's largest measurement debt." It is the blocker on external
launch, with a measured recall less than half the required floor.** Everything else in the bot-behaviour
alignment program is downstream of, or parallel to, this — the ingestion plan says so explicitly (§1: "the
pilot's critical path is GL-0 crisis recall, not this plan").

## The number
| population | measured recall | required | gap |
|---|---|---|---|
| Crisis (CRADLE composite) | **~37%** | ≥95% (fail-closed) | −58pp |
| Self-harm | **~18%** | ≥95% | −77pp |
| (S3 passive-SI CPU path | 88.9% | — | context) |

**≥95% is a fail-closed bar for opening to NEW external pilot users. No signature waives it.** Sub-half-floor
crisis recall means a real fraction of suicidal/self-harm disclosures are not caught at Node-1 today.

## Why it is stalled — and it is a single human decision
GL-0 requires **S2/MARBERT + a validated bilingual eval** (the S1→S2 escalation, the same shape medical/HR
take from keyword→semantic). S2/MARBERT is at a **data-readiness gate**, and the gating decision is **Exp 4.2
(the MARBERT eval), waiting on the PO** (`2026-07-13-exp42-marbert-eval-po-relay.md`). It has not moved. The
build plan exists (`2026-06-14-s2-marbert-build-plan.md`); it is gated on the eval, which is gated on the PO.

## The ask (PO — this is the launch gate, not a research nicety)
▢ **Schedule Exp 4.2 (MARBERT bilingual eval)** — it is the single decision between the platform and a crisis
recall number that can clear the ≥95% external-launch bar. Every day it waits, external launch stays blocked
and sub-half-floor crisis recall stays live for existing users.  ▢ scheduled: ____  ▢ edit: ____

## The companion number that must never be papered over
**AR conformance is 0/180 — UNMEASURED.** The latest bot-behaviour conformance figure (EN **10/36** strictly-
conform, full prod config, noise-floor characterized — supersedes the earlier 8/36, which was a config artifact;
see `2026-07-28-conformance-variance-characterization-1f687c57.md`) is **English-only**; no ratified Khaleeji
corpus exists. In a Gulf-Arabic-first product, quoting the EN figure without the AR-unmeasured caveat is an
inflated-and-unverified number. Building the AR corpus (Probe #1) is a parallel dependency the PO/clinical
roadmap should schedule alongside — the EN number cannot stand in for the product's actual (Arabic-first)
population.

## Third launch-relevant item — the §6a/§6b coercive-control guard is implemented NOWHERE
This is not a measurement gap like the two above; it is a **live, measured behavioural gap** on the surface
that opens to users. The BOT BEHAVIOUR document mandates a coercive-control / unsafe-reaction guard (§6a/§6b):
a discloser of coercive control must be routed to relationship-safety resources, **not** coached in
assertiveness (§6a line 943 is explicit that assertiveness coaching in an unsafe dynamic can increase risk).
**Production does not implement it.** What catches abuse today is CF-005 `domestic_situation`, which catches
explicit **physical-abuse** phrasing and **misses coercive control** — the presentation class §6a's own
recognition table centers on. E7 was built to close this, was enabled on prod 2026-07-22, **fired on ZERO
naturalistic coercive-control cases** (it matches 19 verbatim §6a sentences by substring; real users
paraphrase), and was reverted same-session. So:
- The demonstrated **iatrogenic case is live**: a "controlling boyfriend" discloser is coached the DESC
  assertiveness method — the exact §6a failure mode — with no flag and no referral.
- The fix is a **real detection tier** (semantic, or clinician-authored paraphrase patterns) with a
  **naturalistic** recall number, its own clinical sign-off — not a flag flip.
- This belongs on the launch board **alongside GL-0 and AR**, not filed as "E7 held OFF." It is the same class
  as GL-0 (a mandated safety route with sub-floor real-language recall), scoped to IPV/coercive-control.

Records: `2026-07-22-e7-premise-correction-to-vee.md`, `2026-07-22-e7-ipv-live-gap-escalation.md`
(⛔ POST-ENABLE OUTCOME), `project_e7_verbatim_match_gap` (memory). Same detection-architecture class as
Clinical-Flag Detection Gap #65.

## Records
GL-0 designation (2026-07-04-bot-behaviour-ingestion-plan.md §1); Exp 4.2 relay
(2026-07-13-exp42-marbert-eval-po-relay.md); S2 build plan (2026-06-14-s2-marbert-build-plan.md); conformance
v4 (2026-07-17-bot-behaviour-conformance-matrix-v4-fullgraph-b4d5001a.md).
