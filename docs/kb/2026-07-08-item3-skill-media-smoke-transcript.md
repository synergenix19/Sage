# Item 3 skill-media — behavioral smoke transcript (PROD, 2026-07-08)

Attached to the approval record (`2026-07-08-item3-skill-media-approval-entry.md`) as the "smoke before live" evidence. Run: `railway run -- .venv/bin/python docs/superpowers/drafts/2026-07-08-item3-skill-media-smoke.py` against `sage-api / production`.

## Custody preconditions (all met before the run)
- Signed approval entry on master (#167, "Approved with conditions", §4 = accept Box Breathing uncaptioned at POC).
- Observability deploy live: **`build_sha=76f339d`**, pre-deploy ancestry `bc3cb4b` (OCD-veto) confirmed ancestor.
- Flag **directly observed**, not inferred: `/health/version` → `skill_media_enabled=True`, `skill_media_raw_env='true'`.

## Transcript
```
[prod-verify] build_sha=76f339d40c1cecfc607afd3bfb683db9b0e2b09e crisis_tiering=True skill_media_enabled=True
=== Item 3 skill-media smoke ===
[divert] gate=crisis skill_media=none crisis_protocol=yes
[divert] PASS — video withheld AND crisis protocol rendered (both halves of the guard)
[happy t1] gate=standard skill_media=none
[happy t2] gate=standard skill_media=PRESENT url=https://www.youtube.com/watch?v=G25IR0c-Hj8
[happy] PASS — video delivered on turn 2, in-flow, approved URL, gate=standard
```

## Reading
- **Divert (clinically decisive):** a crisis-language turn → `gate=crisis`, **no** skill media (video withheld), **and** the crisis protocol rendered (`[[CRISIS_DETECTED]]`). Both halves — the video is withheld AND the user gets the crisis response, not a degraded turn.
- **Happy path:** box breathing → nothing on the validating turn (t1, no bare card), then the approved video (`G25IR0c-Hj8`) on the delivery step (t2), `gate=standard`, in-flow.

**Result: BOTH PASS. Item 3 verified live under the signed approval.**
