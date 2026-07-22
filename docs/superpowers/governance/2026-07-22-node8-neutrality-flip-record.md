# Node-8 HR §5 neutrality gate — FLIP record (2026-07-22)

**Live in prod: `SAGE_HR_NEUTRALITY_GATE=true`, SHA `9cd7b554` (PR#354, Vee Option A).**

## §5 drift ELIMINATED BY TEMPLATE SWAP — not "gate corrects drift"
The guarantee comes from **removing the drifting LLM generation from this path**, not from fixing it: the
psychosis referral is now the one deterministic signed fallback, so the ruled §5 fact-in-world drift can
no longer be user-facing here. This is the honest closure. **Corollary for the future:** the day LLM
warmth returns to this terminal (the Stage-2 copy-pool variant), the drift risk returns with it — the
copy pool must carry the same by-construction neutrality the single template does now.

## Deploy (sanctioned path)
- Merged #354 → master `9cd7b554` (rebased 3× onto a fast-moving master: 17cb186b→37fed748→5b6e8320→9cd7b554; forward-only, ancestry ✓). Prior/rollback prod SHA `37fed748`.
- `deploy_prod.sh production 9cd7b554` (stale lock reclaimed, ancestry gate passed, SHA pinned) → `railway up` (code inert, flag OFF) → deploy `9c97ae29` SUCCESS.
- `SAGE_HR_NEUTRALITY_GATE=true` → restart `1073273c` SUCCESS.

## Live-verify (full step 3, running system, tripwire-muted + self-cleaning)
- **Psychosis referral ×3 → the signed fallback template, BYTE-IDENTICAL every time** (deterministic swap).
- **Anxiety turn → untouched** (LLM-composed, not the template).
- **Plain turn → untouched** (LLM-composed).
- Scoping proven live = exactly the HR referral path; no over-catch of the conversational tracks.

## Rollback — real, instant, flag-only
`SAGE_HR_NEUTRALITY_GATE=false` → ~10-min restart → LLM-composed referral (current-minus-gate). NOTHING is
activation-driven or baked in (the gate's only call site is flag-AND-skill_match_method-gated), unlike the
Stage-1 psychosis half. Confirmed the lever is complete before firing.

## Integrity
Fallback = psychotic_referral example[0]/[3] VERBATIM (exact-match verified), source-drift-guarded
(test_hr_neutral_fallback_is_ratified_source_verbatim, gated) + signed_clinical_fields pins
hr_neutrality_fallback_en/ar (verify 8/8; provenance = Vee §5 seed = accuracy, pin = integrity).
