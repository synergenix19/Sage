# Signer's Brief — Native-Arabic (Khaleeji) Shadow-Measure (Tier 0)

**One page for the clinician and DPO sign-off round.** Companion to PR [#140](https://github.com/synergenix19/Sage/pull/140) and the pre-registration (`2026-07-07-native-arabic-register-preregistration.md`). Code SHA under review: `a4f7f0a`.

## What this is (in one sentence)
A **measurement**: on Arabic turns, behind a **default-OFF flag**, the system generates a *second* reply directly in Gulf Arabic (Khaleeji) **purely to score it** — it is **never shown to a user** — so we can find out whether a native-Arabic model would beat today's English-then-translate output on register (naturalness) and latency, before deciding whether to build that path.

## What the flag does / does not do
- **Does:** on Arabic turns, runs one extra native-Khaleeji generation *alongside* the normal reply, logs it for offline rating.
- **Does NOT:** change what any user sees. The served reply is the existing English-then-translate output, byte-for-byte. All existing safety and cultural gates run exactly as today. Verified by construction + tests.
- **Reversible:** default OFF; time-boxed pilot window with a **committed flag-off date**; flip off = zero behaviour change.

## What data lands, and where
The shadow reply and its measurement metadata are written **only** to a dedicated restricted table **`shadow_register_eval`** — never to the user-facing app, the served response, or the general session store.
- **Contents:** native Arabic shadow text, the user's message (English), active clinical flags, prompt hash, exemplar version, generation latency.
- **Protection:** RLS **`ENABLE`+`FORCE`** with **all `anon`/`authenticated` grants revoked** (migration `010`) — reachable only by the service role and authorised analysis. Same restricted-retention class as other clinical-text audit.
- Served-arm latency (`freeflow_gen_ms`, `translate_out_ms`) is recorded on the existing `session_audit` row (no new data surface).

## What each signer is deciding
**Clinician:**
- [ ] The **register rubric** anchor wording (1–5; 4.0 = KPI) in pre-reg §3 is clinically sound for judging Khaleeji naturalness.
- [ ] The **Khaleeji few-shot exemplars** (`khaleeji_shadow_exemplars.json`) are therapeutically appropriate in tone (Cardinal Rule 2), and the **seed-set** everyday-distress inputs are acceptable (no fabricated crisis phrasing; one death-wish-adjacent item already excluded).

**DPO:**
- [ ] **Acknowledge** that restricted clinical text (native Arabic replies + English user message) is persisted to **`shadow_register_eval`** under the RLS posture above, for the pilot window only.
- [ ] The **flag-off date** is committed and acceptable for the retention window.

## Why the numbers can be trusted (design safeguards the signers are relying on)
- **Blinded, dual-arm rating:** ≥2 Gulf-native raters, arm identity withheld, inter-rater agreement reported. No cherry-picking — the comparison is pre-registered.
- **Honest latency:** the two served-arm stages are timed independently (not the inflated total), so the delta isn't biased toward "native looks faster."
- **Timeouts counted, not dropped:** slow shadow generations are recorded as censored observations, so the latency figure isn't optimistically skewed.
- **Coverage reported:** turns that can't be paired are counted and reported (no silent drops).

## Dependency note
Enablement is **gated behind the `session_audit` write-exposure remediation ([#137](https://github.com/synergenix19/Sage/issues/137))** — a live, pre-existing issue that outranks this feature. That is being chased with the cdai PO separately; the flag does not flip until it lands.

---
_Nothing in this pilot alters the live product. It produces three numbers — register delta, latency delta, gate-fire rate — that feed the Tier-1 decision on whether to build native Arabic generation._
