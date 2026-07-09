# Sibling-Pathways Enrichment — DRAFT for clinician + PO (replicating the §3a/BA fix for §1e, §6b, §6c, §7c)

**Purpose:** the recall-concentration disclosure (`2026-07-08-recall-concentration-disclosure.md`) named five pathways beyond §3a that share the suppressed cluster: §7b (fixed with BA), and the four here — **§1e Anticipatory anxiety, §6b Boundary/hard conversation, §6c Rehearse/draft a message, §7c How do I connect**. This packet replicates the BA template (3 bins, per-phrase provenance, rendered `semantic_description` edit) so the clinician touchpoint is a trim, not from-scratch authoring.

**Provenance tags:** `SPEC` = pinned BOT BEHAVIOUR oracle **spec_version_sha=56fde86**, cited by §id (never line numbers); `AUDIT` = Layer-1 suppressed utterance (oracle map + `layer1_trigger_corpus.jsonl`); `NEW` = net-new candidate for clinician confirm.

**Live matcher of record:** prod `sage-api-production-3328`, master **7f2b30d** (this branch is off `4acecf8`; diagnosis run against prod on 2026-07-09). Fixtures live at `tests/fixtures/routing_eval/{anticipatory_anxiety_1e,boundary_conversation_6b,rehearse_message_6c,how_to_connect_7c}_paraphrases.jsonl`.

---

## ⚠️ CRITICAL FINDING FIRST — these siblings do NOT fail the way BA failed

The BA §3a fix addressed **`keyword_rerank_veto → low_confidence_respond`**: a skill that *keyword-matched* was then scored below τ by the reranker (`_keyword_rerank_veto`) against its `semantic_description` and vetoed. The fix (enrich that skill's `semantic_description`) landed exactly where the reranker reads.

**Live diagnosis shows the four siblings fail through a DIFFERENT, two-stage mechanism.** For all 20 audit utterances:
- **Zero keyword matches** (confirmed against the live `match_skill_keywords`; positive controls like "I keep saying yes when I mean no" → assertive_communication still match, so the matcher is not broken).
- **Zero `keyword_rerank_veto` node-path segments.** There is no keyword match to veto.

Instead the suppression is:
- **Stage 1 — `intent_route` diverts before `skill_select` ever runs.** Many utterances are classified `general_chat` (→ `freeflow_respond`) or `info_request` (→ `knowledge_retrieve`). `skill_select`'s semantic matcher never sees them. **Enriching a `semantic_description` CANNOT fix these** — the skill matcher is never reached.
- **Stage 2 — `skill_select` runs but the bi-encoder scores below the offer threshold → `low_confidence_respond`.** This is a *bi-encoder miss*, not a veto. **Enriching `semantic_description` CAN help these** (raises the bi-encoder similarity), same lever as BA, different trigger.

**Implication for command/clinician:** the enrichment edits below are the right lever for the Stage-2 subset and are harmless (won't fire) for the Stage-1 subset. But a `semantic_description` edit **alone will not fully recover these pathways** — the dominant failure for §7c (and roughly half of §1e/§6b/§6c) is Stage-1 intent routing, which needs an `intent_route` change and/or KB coverage, out of scope for a description edit. This is flagged, not smoothed.

---

## Per-pathway LIVE diagnosis (prod 7f2b30d, 2026-07-09)

Legend: **G1** = Stage-1 diverted to `general_chat`/`freeflow` (skill_select never ran); **IR** = Stage-1 `info_request` → `knowledge_retrieve`; **G2** = reached `skill_select` then `low_confidence_respond` (bi-encoder miss); **OFFER** = `skill_select` made a skill offer. No utterance hit `keyword_rerank_veto`.

### §1e Anticipatory anxiety — target family [box_breathing (spec lead), worry_time, problem_solving_therapy]
| utterance | kw match | node path (tail) | class |
|---|---|---|---|
| I'm dreading a big event coming up | none | intent_route → freeflow_respond | G1 |
| I'm so anxious about my presentation tomorrow | none | intent_route → freeflow_respond | G1 |
| I'm terrified about what's coming | none | skill_select → default_offer → skill_offer_made (sem 0.7179) | OFFER (vague) |
| I have an interview next week and I'm sick with nerves about it | none | skill_select → low_confidence_respond | G2 |
| I keep dreading the thing that's coming up | none | intent_route → freeflow_respond | G1 |

3× G1, 1× G2, 1× vague offer. **No utterance keyword-matched; none reached a veto.**

### §6b Boundary setting / hard conversation — target assertive_communication (family also interpersonal_effectiveness)
| utterance | kw match | node path (tail) | class |
|---|---|---|---|
| I need to have a difficult conversation | none | intent_route → freeflow_respond | G1 |
| I need to set a boundary with someone | none | skill_select → default_offer → skill_offer_made (sem 0.75) | OFFER ✓ |
| I need to prepare for a hard talk | none | intent_route → freeflow_respond | G1 |
| there's a tough conversation I have to have and I don't know how | none | skill_select → low_confidence_respond | G2 |
| I need to tell someone to stop crossing a line | none | intent_route → freeflow_respond | G1 |

"set a boundary with someone" **already routes** — its offer body surfaced *both* "Asking for what you need" (interpersonal_effectiveness) and "Speaking up practice" (assertive_communication), matching the oracle family. 3× G1, 1× G2, 1× already-routing.

### §6c Rehearse / draft a message — target assertive_communication
| utterance | kw match | node path (tail) | class |
|---|---|---|---|
| Can you help me word a message | none | intent_route → freeflow_respond | G1 |
| I need to draft a text to someone | none | intent_route → freeflow_respond | G1 |
| Help me rehearse what to say | none | skill_select → low_confidence_respond | G2 |
| I want to practice what I'll write to them before I send it | none | skill_select → low_confidence_respond | G2 |
| help me phrase an email I'm nervous to send | none | intent_route → freeflow_respond | G1 |

3× G1, 2× G2, 0 offers.

### §7c How do I connect — target UNRESOLVED (family [psychoed_anxiety, assertive_communication]; neither fits)
| utterance | kw match | node path (tail) | class |
|---|---|---|---|
| How do I make friends? | none | skill_select → knowledge_retrieve → freeflow | IR |
| How do I meet new people | none | intent_route → freeflow_respond | G1 |
| How do I build deeper relationships | none | skill_select → knowledge_retrieve → freeflow | IR |
| I want tips on how to make friends as an adult | none | skill_select → knowledge_retrieve → freeflow | IR |
| how do I get better at connecting with people | none | skill_select → knowledge_retrieve → freeflow | IR |

4× IR (info_request → KB retrieval), 1× G1. **§7c never routes to a skill at all** — it is classified `info_request` and sent to knowledge retrieval. §7c is a *psychoed* category in the spec ("more how-to than most"), so `info_request → KB` may be the intended disposition IF the KB carries connection content. A `semantic_description` enrichment on any skill will NOT change `info_request` routing. **§7c is primarily an intent-classification + KB-coverage question, not a skill-description enrichment.**

---

## Bin drafts (clinical content — provenanced)

### §1e Anticipatory anxiety
**Bin (a) — ROUTE (calm the body before a specific dreaded upcoming event):**
| phrase | provenance |
|---|---|
| I'm dreading a big event coming up | AUDIT / SPEC §1e (event-specific dread) |
| I'm so anxious about my presentation tomorrow | AUDIT / SPEC §1e |
| I have an interview next week and I'm sick with nerves about it | AUDIT / SPEC §1e |
| the exam is coming up and I'm freaking out | SPEC §1e |
| I'm anxious about the flight next week | SPEC §1e |
| the deadline is stressing me out | SPEC §1e |
| I have this big appointment coming up | SPEC §1e |

**Bin (b) — STAY ABSTAIN / route elsewhere (spec §1e Guard):**
| phrase | why excluded | provenance |
|---|---|---|
| general free-floating worry with no specific event ("I worry about everything") | §1e guard: route to §1d Worry Loops / general anxiety, not anticipatory | SPEC §1e guard |
| dread tied to a distressing outcome with self-harm/crisis content | universal crisis override, exit immediately | SPEC §1e guard |
| "I'm thinking about cancelling / I can't go through with it" (avoidance) | SPEC lists as §1e avoidance signal, but avoidance can shade into panic-disorder territory — clinician call whether plain BA-style activation or anxiety route | SPEC §1e (avoidance signals) |

**Bin (c) — CLINICIAN'S CALL — includes the mandated WHICH-SKILL question:**
| question | tension |
|---|---|
| **WHICH skill carries the §1e recognition clause?** | SPEC §1e sequences **Box Breathing first** → Worry Tree (worry_time) → Problem Solving (problem_solving_therapy). box_breathing is the spec's offer-first, so the fixture provisionally targets it. BUT box_breathing is a *shared calming skill* with a 4-line description; prepending anticipatory-event language risks pulling general/moderate anxiety (§1a–§1c) into box_breathing. worry_time / problem_solving_therapy are more specific to the "sort what's actionable" half. **Recommend: clinician rules whether the clause lands on box_breathing (spec-faithful, over-pull risk) or on worry_time/problem_solving_therapy (narrower).** |
| "I'm terrified about what's coming" | vague, no named event — live sometimes offers, sometimes probes. BA-style route or presence/clarify? |

### §6b Boundary / hard conversation  → assertive_communication
**Bin (a) — ROUTE:**
| phrase | provenance |
|---|---|
| I need to have a difficult conversation | AUDIT / SPEC §6b (general conversation prep) |
| I need to prepare for a hard talk / a conversation | AUDIT / SPEC §6b |
| there's a tough conversation I have to have and I don't know how | AUDIT / SPEC §6b |
| I need to set a boundary / tell them no / tell them to stop | SPEC §6b (boundary-specific) — note "set a boundary with someone" already routes |
| I need to tell someone to stop crossing a line | AUDIT / SPEC §6b |
| I need to stand up for myself / give someone feedback | SPEC §6b (standing up / feedback) |
| I need to address a problem at work / speak to my boss / talk to my partner | SPEC §6b (specific context) |

**Bin (b) — STAY ABSTAIN / route elsewhere (spec §6b Guard):**
| phrase | why excluded | provenance |
|---|---|---|
| fear of retaliation / an unsafe or controlling dynamic (not ordinary nervousness) | §6b guard → §6a recognition + relationship-safety resources, NOT generic prep | SPEC §6b guard |
| serious workplace/legal matter (harassment, discrimination, disciplinary) | §6b guard → point to HR/legal, not conversation coaching | SPEC §6b guard |
| significant anticipatory anxiety about the conversation itself | §6b guard → offer §1e calming skill first | SPEC §6b guard |

**Bin (c) — CLINICIAN'S CALL:**
| question | tension |
|---|---|
| assertive_communication vs interpersonal_effectiveness as the primary | oracle family lists interpersonal_effectiveness first for §6b; live "set a boundary" offers both. One enriched assertive_communication description is proposed (below) — confirm assertive_communication is the intended primary, or whether interpersonal_effectiveness should also carry the clause. |

### §6c Rehearse / draft a message  → assertive_communication
**Bin (a) — ROUTE:**
| phrase | provenance |
|---|---|
| Can you help me word a message / how should I phrase this | AUDIT / SPEC §6c (wording help) |
| I need to draft a text / a reply / help me draft this | AUDIT / SPEC §6c (what to send) |
| Help me rehearse what to say / can we practise / mock conversation | AUDIT / SPEC §6c (practice / rehearsal) |
| I want to practice what I'll write before I send it | AUDIT / SPEC §6c |
| help me phrase an email I'm nervous to send | AUDIT / SPEC §6c |

**Bin (b) — STAY ABSTAIN / route elsewhere (spec §6c Guard):**
| phrase | why excluded | provenance |
|---|---|---|
| drafting a bold message toward someone who might react unsafely | §6c guard → §6a recognition + safety resources | SPEC §6c guard |
| message written in anger / while highly activated (can't be unsent) | §6c guard → suggest a pause (§1a) before finalizing | SPEC §6c guard |
| formal workplace complaint / legal / safety content | §6c guard → point to proper channel | SPEC §6c guard |

**Bin (c) — CLINICIAN'S CALL:**
| question | tension |
|---|---|
| **Do §6b and §6c collapse to ONE assertive_communication edit?** | YES per this diagnosis — spec §6c skill is "Role-Play OR Draft the Message (Assertive Communication)"; oracle family for both is {assertive_communication, interpersonal_effectiveness}; live "set a boundary" already offers the shared pair. One recognition clause covering hard-conversation prep AND message drafting/rehearsal covers both §6b and §6c. **Confirm the collapse.** |

### §7c How do I connect  → UNRESOLVED
**Bin (a) — candidate ROUTE (IF a skill is wanted at all):**
| phrase | provenance |
|---|---|
| How do I make friends / meet new people / build relationships / connect with people | AUDIT / SPEC §7c (how-to / practical) |
| I want deeper / closer relationships, to feel more connected, to belong | SPEC §7c (goals / desires) |
| I don't know how to start conversations / struggle to connect / feel awkward around people | SPEC §7c (specific struggles) |
| I want to improve my social skills / be more confident socially | SPEC §7c (confidence / skills) |

**Bin (b) — STAY ABSTAIN / route elsewhere:**
| phrase | why excluded | provenance |
|---|---|---|
| loneliness as raw need for company/presence ("I feel lonely", "I don't want to be alone right now") | that is §7a presence_only, NOT §7c how-to | SPEC §7a |
| active withdrawal pattern the person wants to reverse ("I've been isolating myself and want to stop") | that is §7b → behavioral_activation (already fixed) | SPEC §7b |

**Bin (c) — CLINICIAN'S CALL — includes the mandated WHICH-SKILL question:**
| question | tension |
|---|---|
| **WHICH skill (if any) for §7c?** | oracle family = [psychoed_anxiety, assertive_communication]; neither fits — psychoed_anxiety is anxiety mechanisms; assertive_communication is boundaries/refusal. interpersonal_effectiveness is DBT for *existing* relationships (GIVE/FAST/DEAR MAN), not *making new* friends, so it also fits imperfectly. §7c fixture provisionally targets interpersonal_effectiveness as least-bad, flagged. |
| **Is a skill even the right disposition?** | §7c is a *psychoed how-to* category. Live routes it `info_request → knowledge_retrieve`. If the KB carries "how to make friends / deepen relationships" content, `info_request → KB` may be the correct disposition and NO skill edit is needed. **If not, this is a KB-content gap and/or an intent_route decision, NOT a `semantic_description` enrichment.** Recommend: clinician + PO decide (i) KB-article vs skill, and (ii) if skill, which. |

---

## Rendered `semantic_description` edits (CMS rule: third-person, no first-person pronouns; recognition clause PREPENDED)

### Edit 1 — assertive_communication (covers §6b AND §6c — ONE edit)
**Rationale:** current description is 100% technique/protocol (DESC, Wolpe, Smith) with zero presentation language for "difficult conversation / draft a message / rehearse". The recognition clause covers bin (a) of both §6b and §6c.

**OLD:**
> Assertiveness training protocol. DESC formula: Describe, Express, Specify, Consequence. Assertive communication technique. Passive versus assertive versus aggressive communication styles. Communication assertiveness training. Assertive self-expression. Setting limits. Saying no with clarity. The art of the assertive request. Interpersonal effectiveness skills. DESC communication formula application. Wolpe assertiveness training. Assertive boundary-setting protocol. Role-play rehearsal for assertive communication. Communication style identification and training. Expressing needs directly. The no-guilt assertive refusal technique. Smith assertive communication protocol.

**PROPOSED NEW (prepended clause in **bold**):**
> **Assertive communication for preparing a difficult or hard conversation, setting a boundary with someone, telling someone to stop crossing a line, addressing a problem with a partner, family member, or at work, standing up for oneself, giving feedback, or asking for what one needs; and for wording, drafting, or rehearsing a message, text, or email, or practising what to say before sending or saying it.** Assertiveness training protocol. DESC formula: Describe, Express, Specify, Consequence. Assertive communication technique. Passive versus assertive versus aggressive communication styles. Communication assertiveness training. Assertive self-expression. Setting limits. Saying no with clarity. The art of the assertive request. Interpersonal effectiveness skills. DESC communication formula application. Wolpe assertiveness training. Assertive boundary-setting protocol. Role-play rehearsal for assertive communication. Communication style identification and training. Expressing needs directly. The no-guilt assertive refusal technique. Smith assertive communication protocol.

### Edit 2 — box_breathing (§1e) — PROVISIONAL, pending bin-(c) which-skill ruling
**Rationale:** spec §1e leads with Box Breathing. Clause covers bin (a). **Hold pending clinician ruling on over-pull risk** (see §1e bin (c)) — if the clause instead belongs on worry_time or problem_solving_therapy, this edit is discarded and rendered there.

**OLD:**
> Box breathing: four-count inhale, four-count hold, four-count exhale, four-count hold. Square breathing. Paced breathing exercise. Walk me through the four-count breathing cycle.

**PROPOSED NEW (prepended clause in **bold**):**
> **Box breathing to calm the body before a specific dreaded upcoming event: dread or anxiety about a presentation, interview, exam, flight, appointment, or deadline that is coming up, feeling sick with nerves ahead of it, counting down to a date that is making things worse.** Box breathing: four-count inhale, four-count hold, four-count exhale, four-count hold. Square breathing. Paced breathing exercise. Walk me through the four-count breathing cycle.

### Edit 3 — §7c — NO edit proposed
No `semantic_description` edit is proposed for §7c. The live failure is Stage-1 `info_request` routing to KB, which no skill description changes. A candidate interpersonal_effectiveness clause could be drafted, but only after the clinician+PO rule (i) skill-vs-KB and (ii) which skill. Drafting one now would encode a contested call. **Deferred to bin (c).**

---

## Mechanism note (engineering, not clinical)
- `_keyword_rerank_veto` scores `(utterance, skill.semantic_description)` — NOT `target_presentations`. So enrichment must land in `semantic_description`, same as BA. **Confirmed by the BA fix commit `8079caa`.**
- BUT the siblings' dominant failure is UPSTREAM of the reranker: `intent_route` sending utterances to `general_chat`/`freeflow` (Stage 1) or `info_request`/`knowledge_retrieve`. **A `semantic_description` edit only affects utterances that reach `skill_select` and land in `low_confidence_respond` (Stage 2).** It is necessary-not-sufficient for these pathways.
- τ is not touched by any edit here. Per the model-promotion / semantic-threshold rules, any `semantic_description` edit requires re-running `calibrate_threshold.py` and confirming no in_scope/id_oos regression before ship — same gate as BA.

## Language coverage — EN-only, AR explicitly deferred
This draft is **EN-only** (the audit corpus was EN). assertive_communication and box_breathing already carry some AR `target_presentations`, but this enrichment adds **no AR recognition phrases**. The AR counterpart is **filed with the Arabic follow-up track** (`2026-07-07-arabic-reranker-tau-followup.md`), not shipped silently EN-only. Recorded so the fix does not widen the EN/AR asymmetry without a note.

## The clinician + PO ask
1. **§1e which-skill (bin c):** box_breathing (spec-faithful, over-pull risk) vs worry_time/problem_solving_therapy for the recognition clause.
2. **§6b/§6c collapse (bin c):** confirm one assertive_communication edit covers both; confirm assertive_communication is the primary (vs interpersonal_effectiveness).
3. **§7c disposition (bin c):** skill vs KB-article; if skill, which one (none fit cleanly). Likely an intent_route/KB decision, not an enrichment.
4. Confirm bin (a) routes and bin (b) stay-abstain for each pathway.

## Honest coverage limits (do not smooth over)
- **The BA "keyword_rerank_veto" premise does not hold for these four siblings** — zero keyword matches, zero vetoes. The suppression is intent-routing + bi-encoder miss.
- A `semantic_description` edit **cannot recover the Stage-1 (`general_chat`/`info_request`) utterances** — ~3/5 of §1e, §6b, §6c and ~5/5 of §7c. Full recovery needs an `intent_route` change and/or KB coverage, out of scope for this packet.
- §1e and §7c `expected_route` values in the fixtures are **provisional** pending the bin-(c) rulings.
- Diagnosis is single-shot per utterance against a stateful graph; vague utterances (e.g. "terrified about what's coming") showed run-to-run variation (offer vs probe). Treated as borderline, not definitive.
- No calibration re-run performed (work session, no ship). The edits are drafts; `calibrate_threshold.py` + gate are prerequisites before any deploy.

---

# COMMAND CURATION (2026-07-09) — the TWO-PART fix, probe-validated

The drafter's finding (siblings ≠ BA; two-stage failure) was verified before committing this packet — a candidate trigger wired on a branch, the Stage-1 utterances re-traced. **Result (τ_en = −6.0843):**

| pathway | utterance | Stage-1 trigger fires? | reranker vs CURRENT desc | reranker vs ENRICHED desc |
|---|---|---|---|---|
| §6b | "I need to have a difficult conversation" | **HIT** → reaches skill_select | veto (−7.31) | **ACCEPT** (−2.23) |
| §6b | "tough conversation… don't know how" | HIT | veto (−7.58) | ACCEPT (−3.54) |
| §6c | "word a message" | HIT | veto (−7.75) | ACCEPT (−3.77) |
| §6c | "draft a text to someone" | HIT | veto (−7.29) | ACCEPT (−3.00) |
| §1e | "dreading a big event" | HIT | veto (**−11.05**) | ACCEPT (−2.82) |
| §1e | "nervous about my presentation" | HIT | veto (−11.04) | ACCEPT (−3.54) |

**Proven:** (1) the trigger recovers Stage-1 — all reach skill_select; (2) the trigger ALONE is insufficient — the reranker vetoes all six against the current description; (3) trigger + enrichment recovers all six. The fix is genuinely **two edits on the same skill JSON**: `target_presentations` (the trigger surface, = bin (a) phrases) **and** the `semantic_description` recognition clause. Neither alone suffices.

## Condition 1 — the TRIGGERS are clinical content, and their false-positive direction is sharper than BA's
`target_presentations` are deterministic **substring** matches feeding the Node-2 pre-pass (hint-not-hijack: they route TO skill_select; the semantic tiers still adjudicate — that's the architectural safety net, the gate is what proves it held). So each trigger set gets the three-bin treatment (bins above), with one added rule: **prefer specific multi-word triggers** ("difficult conversation", "dreading a big event") over bare single words ("conversation", "dreading") — a bare substring over-pulls (e.g. "dreading" alone catches anticipatory-grief or general dread the presentation doesn't fit). The clinician confirms the trigger phrasings, not just the description bins.

## Per-pathway fix shape
- **§6b + §6c → ONE `assertive_communication` edit** (confirmed collapse): triggers (difficult/tough/hard conversation, set a boundary, word/draft/rehearse a message, phrase an email) + one prepended recognition clause. Reranker flips cleanly (−7s → −2 to −4).
- **§1e → box_breathing PROVISIONAL** ⚠️: current score **−11** (box_breathing is a poor native match for anticipatory dread) means the clause must work hard to clear τ → highest over-pull risk into general §1a–c anxiety. **This is why the which-skill call matters** — worry_time / problem_solving_therapy may be the better home (narrower, less shared). Clinician rules before this one ships.

## Condition 2 — §7c is a DISPOSITION decision, three explicit options (do not leave unclassified)
"How do I make friends" → `info_request → knowledge_retrieve` (4/5). No skill-description edit changes this. The clinician picks ONE:
- **(a) KB-article, served well through the existing info_request path** — content work, NO routing change. (Likely correct if the KB carries connection/social content.)
- **(b) A new or remapped skill** — an inventory question on the clinician's clock (no current skill fits: psychoed_anxiety is anxiety-ed; interpersonal_effectiveness is DBT for *existing* relationships).
- **(c) Current behaviour confirmed conformant → close it** — "how-to" info-seeking → KB is arguably the system working as designed.

## Condition 3 — the MECHANISM LEDGER (recorded in the Layer-1 conformance matrix)
Three suppression mechanisms, found by three investigations — the next suppressed pathway starts from "which mechanism?", not re-derivation:
1. **reranker-vs-description** (BA §3a, §7b) — keyword-matches, reranker vetoes vs `semantic_description`. Fix: enrich the description. *Per-skill content route scales here.*
2. **intent-route diversion** (§1e, §6b, §6c) — no keyword match → `intent_route` sends to general_chat before skill_select. Fix: `target_presentations` trigger (Node-2 pre-pass) + description enrichment. *Requires the trigger surface maintained per-presentation — the toil #209 flagged; this is #209's sharpened answer.*
3. **info_request classification** (§7c) — classified info-seeking → KB, never a skill route. Fix: a disposition decision (KB / skill / conformant), not a description edit.

## Gate discipline (unchanged, mandatory)
Both the trigger and description edits change the routing surface → **calibrate_threshold.py after the edits** (not optional — new keywords + new description shift scores), full signed gate on the expanded corpus (harm-0, id_oos ≥ 0.906, wrong-route no-regress) + the **per-pathway floor**, then probe pair (the sibling utterance → its skill; a deliberately-excluded bin-(b) phrase → stays out) + live UX read. EN-only; AR filed to the Arabic track.

## The clinician ask (batched — one sitting, four pathways)
1. **§6b/§6c** — confirm the assertive_communication triggers (bin a) + deliberately-excluded (bin b) + the rendered description clause. One edit, two pathways.
2. **§1e** — rule the **which-skill** (box_breathing vs worry_time/problem_solving_therapy) BEFORE confirming its triggers/clause (the −11 over-pull risk rides on this).
3. **§7c** — pick option (a) / (b) / (c).
4. Confirm the trigger phrasings are specific enough (multi-word) to control substring false-positives.
