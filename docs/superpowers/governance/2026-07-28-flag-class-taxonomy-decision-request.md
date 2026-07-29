# Decision Request — Flag Class Taxonomy: Fail-Closed Defaults (Follow-up 2)

Date: 2026-07-28. Raised per reviewer approval, with the reviewer's two-class
taxonomy. Origin: parity incident (a safety guard defaulting OFF made every naively
parameterized instrument measure a guard-less system; second occurrence).
Owner for decision: eng lead + clinical lead JOINTLY (routing behavior on safety
guards is not a single-signer item). DPIA evidence set item ("prefer safety over
capability").

## The taxonomy (proposed, per review)

- **Safety-class:** default ON, fail closed. Disabling requires an explicit env
  override PLUS a recorded rationale. Missing or unparseable value resolves ON.
- **Feature-class:** default OFF, fail closed in the other direction. Missing value
  resolves OFF.

Both are fail-closed; they differ in which state is closed. Run 1 of the §1a
characterization got exactly this difference wrong.

## Proposed register (the ask: confirm/correct every class assignment)

| Flag | Proposed class | Note |
|---|---|---|
| SAGE_MEDICAL_REDFLAG_GUARD | safety | E1-E7 approval: ON is intended prod state |
| SAGE_CRISIS_TIERING | safety | currently defaults ON (raw_env null in prod readback) |
| SAGE_HIGH_RISK_DETECTION | safety | HR-1 Stage 1 live |
| SAGE_HR_NEUTRALITY_GATE | safety | pairs with HIGH_RISK_DETECTION |
| SAGE_VENTING_SUPPRESSION | safety | needs confirm: suppression semantics |
| SAGE_ROUTE_PRECEDENCE | safety | precedence ordering of safety routes |
| SAGE_D1_SCREEN | safety (PRESUMED, ruling 2026-07-28) | screens on risk content → gates harm; clinical sign-off decides whether current behavior is safe ON |
| SAGE_D1_SCREEN_SHADOW | feature | shadow measurement only |
| SAGE_IPV_PREEMPTION | safety (PRESUMED, ruling 2026-07-28) | preempts on risk content; currently false in prod (reverted stream); clinical sign-off decides |
| SAGE_INFO_REQUEST_CONSULT | feature, **signed_value=true** (Vee B1 2026-07-23) | psychoed Mechanism-A. **RULING RECORD 2026-07-29:** off-drift observed in prod 2026-07-28 (93bd5abf/PR#370 deploy window); time-boxed record hunt found NO recorded rationale on master → **Step 2b fired** (unexplained drift, not a decision; signed state is standing truth). Restored true + owner-ratified (D1 GO + D2 RATIFY, 09013f19 deploy) before the ruling round-trip completed; readback-confirmed serving true. Evidence: pins-deploy-record (PR#378), 2026-07-29 ledger. First live case for the signed_value deploy-gate fast-follow |
| SAGE_HIGH_RISK_TERMINAL | safety (PRESUMED, ruling 2026-07-28) | terminates on risk content; clinical sign-off decides |
| SAGE_D5_ACUITY_GATE | feature (parked) | inert by decision |
| SAGE_SKILL_OFFER_COOLDOWN | feature | |
| SAGE_NATIVE_ARABIC_SHADOW | feature | shadow only, never served |
| SAGE_SKILL_MEDIA_ENABLED | feature | server response-header layer |
| SAGE_EMBED_CACHE | feature (perf) | |
| SAGE_AUDIT_LOG | **safety (RULED 2026-07-28)** | arguably not a flag at all: the runtime audit trail is a compliance commitment (PDPL traceability, right-to-object), not a feature, and every register row's evidentiary value depends on it. If it remains a flag operationally: default ON, recorded-rationale required for any OFF, and an OFF state must be LOUDLY visible in /health/version |
| SAGE_MODALITY_REQUEST_ROUTING (planned) | feature | re-plan draft |
| SAGE_AUDIT_CLASSIFIER_PROVENANCE (in flight) | **safety on activation** (ruling 2026-07-28) | new audit surface; dark period is STAGED ROLLOUT, not a feature-class default. Must be ON before the Phase 0 baseline runs — an unrecorded-provenance baseline fails the signed instrument-parity rule |

Register to be completed mechanically: the parity runner's config regex enumerates
every `SAGE_*` getenv; any flag absent from this table fails the register check
(same pattern as signed_clinical_fields).

## Rulings received (2026-07-28)

- Taxonomy ENDORSED. `SAGE_AUDIT_LOG` ruled safety-class (see row). D1_SCREEN /
  IPV_PREEMPTION / HIGH_RISK_TERMINAL: architectural PRESUMPTION safety-class
  (anything that screens, preempts, or terminates on risk content gates harm);
  whether each guard's CURRENT behavior is safe to have ON is a clinical ruling —
  presumption stated, clinical sign-off decides. **Deadline rule:** these three must
  not sit unresolved past the taxonomy's sign-off — an undecided safety flag is de
  facto feature-class, which is the failure mode this taxonomy exists to prevent.

## Asks (remaining)

1. Ratify the two-class taxonomy (endorsed; formal joint sign-off pending).
2. Clinical rulings on D1_SCREEN / IPV_PREEMPTION / HIGH_RISK_TERMINAL current
   behavior, before taxonomy sign-off completes; confirm the rest.
3. Approve implementation shape: class lives next to the flag definition in
   `config.py`; a CI check asserts every flag declares a class and that
   safety-class defaults are ON; the disable-override rationale is a required
   field the check greps for.
4. Note the interim hazard while defaults remain as-is: every local instrument runs
   guard-less unless follow-up 1's helper is used; follow-up 1 is therefore the
   containment for this window.
