# Clinician touchpoint — Vee — §1c derealization: mechanism, terminal, and a doc-vs-design conflict

This is Part A of the §1c crisis-over-escalation fix. Your Ruling 1 (2026-07-18) sent the dissociation
family to referral, not grounding — correct. Before any code, three things the enumeration surfaced that
your ruling needs to resolve, because the specific routing is clinical content and there's a doc-vs-design
contradiction underneath it. Recommendations below are aligned to the BOT BEHAVIOUR document.

## What the doc actually says (verified)
- "Everything feels unreal" and "I feel disconnected from my body" are in the **§1c High-anxiety Fear
  list** — NOT in the §HR dissociation-11 list. CF-008 is the §HR-11 list VERBATIM; these two are not in it.
- The **§1c anxiety guard (L151, verbatim):** *"There are signs of dissociation, panic attack with
  derealization, trauma flashback, or psychosis-like content — grounding/mindfulness exercises can
  sometimes intensify these states; escalate to referral rather than presenting the standard tools."*
- The §HR dissociation-11 list is DIFFERENT, more clinical phrasing ("I lose chunks of time", "I feel
  completely numb and absent", "I don't know where I am sometimes") — a heavier register than §1c "feels unreal".

## Ruling 1 — MECHANISM: a NEW Node-1 clinical flag routed at the safety altitude (doc + architecture)
Rec: **add a new derealization clinical-flag rule at Node 1 (safety_check, reading RAW input per the
language contract), SEPARATE from CF-008, and route it at the SAFETY altitude — before intent_route.**
NOT extend CF-008, NOT a post-intent guard. Why this is the aligned answer on BOTH axes:
- **Doc:** CF-008 is the §HR-11 list verbatim (1:1 auditable against source); a new flag keeps that intact.
- **Architecture:** deterministic clinical-flag detection lives at Node 1 (`clinical_flag_patterns.json`,
  raw input). And the §1c over-escalation is the SAME bug HR-1 Stage 2 fixed — a safety-class disposition
  routed BELOW `intent_route`, so the LLM classifies a turn it has "no clinical business classifying"
  (arch doc line 118, the HR routing-altitude correction). Routing the flag at the safety altitude means
  the LLM never sees the derealization turn → the §1c crisis-FP is fixed by ALTITUDE, and this CLOSES the
  live Cardinal-Rule-4 violation deterministically (same as HR-1), rather than papering it with a
  probabilistic guard. A flat keyword also can't read context (primary dissociation vs panic symptom) —
  a Node-1 rule + precedence can.
→ ☐ approve new Node-1 flag @ safety altitude (rec)  ☐ prefer CF-008 extension  ☐ discuss

## Ruling 2 — TERMINAL: the softer anxiety-track referral, NOT the HR terminal
In Ruling 1 you said "HR referral." On the doc: these phrases are §1c (anxiety), and the §1c guard says
"escalate to referral" — the **anxiety-pathway professional referral** (warm "escalate to professional
support", external 5-4-3-2-1 as a brief stabiliser). The **HR terminal** is a different thing (the
distress-question + standardized supportive message, for the §HR-11 triggers). Rec: **route §1c-derealization
to the anxiety-track referral, and RESERVE the HR terminal for the §HR-11 list.** (Eng note: this softer
referral exists today only as LLM-discretionary skill guard text — the same discretion that failed here —
so making it deterministic is a small build; that is the scope, not free.)
→ ☐ anxiety-track referral (rec)  ☐ HR terminal  ☐ edit

## Ruling 3 — DOC-vs-DESIGN CONFLICT you must not sign around: panic-WITH-derealization
The HR-1 design carries a control: *"panic-derealization ('everything felt unreal during the panic
attack') routes per §1c, NOT HR."* But the **doc's §1c guard (quoted above) lists "panic attack with
derealization" among the presentations that escalate to REFERRAL** — not standard tools. So the design
control (→ §1c skill) and the doc (→ referral) are OPPOSED, and the design control is the one without doc
backing. They reconcile ONLY if the design's "§1c" means the anxiety-track referral, not a grounding skill.
Rec: **panic-with-derealization → anxiety-track referral (doc wins); correct the design control to say
"→ §1c anxiety referral", not "§1c skill".** If you instead intend it to get grounding, the DOC needs a
correction — either way the losing side gets a correction note (DQ-3). Which governs?
→ ☐ referral, doc wins (rec)  ☐ grounding skill, correct the doc  ☐ edit

## Ruling 4 — confirm the clean split (so the fixtures are right)
- §1c pure panic, NO derealization ("can't breathe", "racing heart", "out of control") → grounding skill
  (this is the ONLY §1c→skill case; it's Part B's veto target).
- §1c derealization / panic-with-derealization → anxiety-track referral (Rulings 2/3).
- §HR-11 clinical dissociation triggers → HR terminal (unchanged).
→ ☐ confirm split  ☐ edit

## Architecture consequence of your TERMINAL choice (Ruling 2) — the two are coupled
The graph has a SAFETY-EXIT TERMINAL CLASS (crisis > medical > hr, precedence-ranked, pre-intent
altitude). Its bypass of the output_gate is licensed by TEMPLATED (deterministic) copy, NOT by being
safety-related (arch doc §2.1.1) — any terminal with runtime-GENERATED copy forfeits the bypass. So:
- **If you route derealization to a referral with STANDARDIZED copy** (the doc's warm "escalate to
  professional support" message), it fits the class as a lightweight terminal at precedence rank 4
  (below crisis/medical/hr — the softer tier), pre-intent, templated. This is the cleanest arch fit and
  it's the mechanism that closes the Rule-4 violation. It needs a small clinician-authored standardized
  message (does not exist deterministically today — only as LLM skill-guard text).
- **If you route it to the existing HR terminal**, that's heavier (distress-question + 2-3 turn protocol)
  and semantically wrong for anxiety-derealization (the §HR-11 register), and it over-elevates severity.
- Either way: NO CF-008 change (new flag), so NO §HR manifest re-sign of CF-008; the new flag itself is a
  signed safety rule. Both-direction fixtures: derealization → referral; pure-panic → skill.

No code until you rule 1–3. Then: build Part A (Node-1 flag + safety-altitude route + templated referral)
→ gate → RE-MEASURE §1c → design Part B (the veto for pure-panic residual) on the updated matrix. The
panic-derealization conflict is DQ-3 so the losing side gets corrected in the source.
