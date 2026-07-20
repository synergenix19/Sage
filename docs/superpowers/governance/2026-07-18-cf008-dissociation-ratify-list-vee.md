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

## Ruling 1 — MECHANISM: §1c context-guard, not a CF-008 keyword extension
Rec: **implement the §1c anxiety-pathway guard as a deterministic check** (a §1c utterance carrying
derealization/dissociation signs → escalate to referral), NOT extend CF-008. Two doc-aligned reasons:
(1) CF-008 is the §HR-11 list verbatim — its value is that it audits 1:1 against the source; extending it
buries §1c phrases in the §HR rule. (2) A flat keyword can't read context, and the phrase's meaning here
IS contextual (primary dissociation vs a panic symptom) — the guard can condition on the §1c anxiety
context, a keyword can't. Same routing outcome, doc-faithful, better mechanism. CF-008 extension = fallback.
→ ☐ approve §1c guard (rec)  ☐ prefer CF-008 extension  ☐ discuss

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

## Implementation consequence of each mechanism (so you see the cost)
- **§1c guard (rec):** anxiety-track guard + a small deterministic anxiety-referral; NO CF-008 change, NO
  safety-manifest re-sign. Both-direction fixtures: derealization → anxiety referral; pure-panic → skill.
- **CF-008 extension (fallback):** signed safety-rule change + manifest re-sign; routes to HR terminal
  (heavier); same both-direction fixtures.

No code until you rule 1–3. Then: build Part A → gate → RE-MEASURE §1c → design Part B (the veto) on the
updated matrix. The panic-derealization conflict is filed as DQ-3 so the losing side gets corrected in the source.
