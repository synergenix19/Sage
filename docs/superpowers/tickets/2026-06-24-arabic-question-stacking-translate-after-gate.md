# Ticket: Arabic replies can stack two questions (`؟ … ؟`) — symptom of translate-after-gate

**Filed:** 2026-06-24 · **Source:** prod UI functional test of the D3/D4/D5 tone release (`chat.biosight.ai`)
**Status:** open · **Type:** follow-up (guardrail-adjacent, not cosmetic) · **Not a regression**
**Related but DISTINCT:** `2026-06-24-language-router-arabic-overtrigger.md` — same `؟`/EN↔AR surface, **different layer and different fix**. That one is the **language router** (which language to answer in) and is a small shippable fix now; **this one** is gate-ordering / translate-after-gate and is resolved only by **native-Arabic generation** (a roadmap item). Do not bundle them.

## Symptom
On a normal Khaleeji-Arabic distress turn, Sage replied with **two** question marks in one message
(`…أخبرني أكثر عن نومك؟ … أو الاثنين؟`). The English equivalent of the same scenario passed the
one-question discipline with **exactly one** question. Live example captured 2026-06-24 (session
`/chat?new=3`, signed in as rohansarda@gmail.com).

## Root cause — ordering, not a missing strip
The question-discipline gate runs on the **English** text, and translation to Khaleeji happens
**after** it:
- `src/sage_poc/nodes/output_gate.py:467` — `_limit_to_one_question(response_en)` (gate on English)
- `src/sage_poc/nodes/output_gate.py:501` — `async_translate_to_arabic(response_en)` (translate, after the gate)

The English text the gate approves contains one interrogative; the translator can render that single
English question as **two Arabic interrogatives**, downstream of the gate, which never re-inspects it.
This is the **same translate-after-gate architecture** that produced the original Arabic-tone user
feedback — not a new defect, and **not introduced by the D3/D4/D5 release** (R1/T1 only made the gate
`؟`-aware for the case where the model emits Arabic *directly* into `response_en`; it did not and could
not change the mainline gate-then-translate path).

## Do NOT "just add a second `؟`-strip after translation"
The tempting one-liner — a post-translation `؟`-counting pass — is a **trap**. It post-edits
already-translated Khaleeji, risking ungrammatical output or stripping the wrong clause (Arabic
question structure does not map one-to-one onto English clause boundaries). Reject that fix.

## Defensible fix — native Arabic generation (already on the roadmap)
Resolve by generating Arabic natively so the discipline gate runs on the **text that actually ships**,
not on an English pre-image that is later re-shaped. See the decision record:
`docs/SageAI_architecture_current.md` (English-first → translate-at-output_gate is the documented root
cause of Arabic tone issues) and the D3/D4/D5 spec §16/§17
(`docs/superpowers/specs/2026-06-24-conversational-style-d3-d4-d5-design.md`). Native Arabic generation
is gated on a crisis-recall regression and Health Data Law 2/2019 in-country-processing residency.
**This finding is the most concrete live evidence to date for that roadmap item** — it should
strengthen the native-Arabic case, not compete with it as a standalone patch.
Interim mitigation (a guarded post-translation pass, carefully scoped) should be considered **only if
this recurs at volume** before native generation lands.

## Blast radius & severity (governs priority)
- **Does NOT touch the crisis path.** Crisis responses are hardcoded, not LLM-translated; verified this
  release — EN crisis card correct in UI, AR crisis correct via API smoke. Out of scope here.
- **Open question that sets severity (please check before prioritising):** does the double-`؟` ever
  land on a turn that matters clinically — specifically at **high `emotional_intensity`**, where
  "ask one question at a time" is a MIND-SAFE **therapeutic guardrail**, not just a tone preference?
  Stacking two questions onto a distressed Khaleeji-speaking user is a **mild guardrail miss**, not
  cosmetic. Prioritise by clinical exposure (does it co-occur with high intensity / acute states),
  not by how it reads in a demo.

## Acceptance (when addressed via native generation)
A high-intensity Khaleeji turn yields **at most one `؟`**, with the discipline enforced on the shipped
Arabic text. Add an EN+AR question-count assertion to the output-gate suite at that point.
