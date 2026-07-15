# Probe design requirements (from the 7/36 texture) — lock before building

The conformance re-run (7/36 strict, 47% utterance-level, prod 5b33a0e) isn't just a number; its
texture dictates how the probe must be structured. Capture these BEFORE authoring cases.

## 1. Adjudicate the psychoed cluster AS A CLUSTER (not 6 verdicts)
§1f, §3c, §4a, §6d, §7c, S2c are all 0/5, all the SAME failure: bare-affect/informational utterance
-> intent_route `general_chat` gate -> freeflow, BEFORE skill_select runs. That is plausibly **one
routing decision** (informational intent -> freeflow) overriding six prescribed psychoed skills, not
six independent skill-matching gaps. If so, one fix (an intent-route rule / a psychoed intent class)
moves all six.
- **Probe requirement:** put a **shared hypothesis field** on all six categories' cases:
  `"general_chat gate is wrong for psychoed intent: yes/no"`. The result must read as ONE verdict on
  the cluster, not six. Do NOT pre-build the fix — the probe confirms the label first.

## 2. HR / psychosis 0/5 = highest-severity clinical-packet row
Prescribed `professional_referral`, observed `self_help_skill` — a **safety miss** (high-risk
psychosis getting a coping skill instead of a referral). This is the known psychotic-referral gap.
Flag it as the **top-severity row** in the clinical packet, not a probe-partial.

## 3. S2a grief needs F6-coverage attention
F6 is proven working (§3d venting 5/5, §7a loneliness 5/5). But S2a grief is 0/5 — some grief
phrasings still get a skill imposed (prescribed presence). F6's keyword/route coverage of **S2a
specifically** is the probe's job to characterize (is it a phrasing F6 doesn't detect, or a
different route?).

## 4. AR corpus = native Khaleeji for the LIVE mechanisms (NOT "translate the EN corpus")
The AR column is UNMEASURED (0 AR utterances). The AR corpus has a defined worklist — native
Khaleeji utterances (clinician-authored or validated, MT does not qualify) for:
- the four-descriptor **medical red-flag** phrases in Gulf Arabic (B1's AR exposure);
- **PI-VI-001's Khaleeji keywords** (F6's AR path — finally tested end-to-end);
- the **SK-AR-\*** unsigned rules' trigger phrases (ties to the #270 triage — unsigned AR safety);
- the **0/5 categories** above, in AR.

## Provenance standard (now permanent)
Every probe/measurement result carries: **SHA + distance-from-master + resolved flag state +
instrument health (LLM 402/failure count)**. The last was added after a 25%-credit-exhausted run
nearly shipped a false number. SHA+flags alone is not enough.
