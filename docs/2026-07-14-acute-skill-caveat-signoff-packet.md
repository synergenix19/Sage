# Clinician Sign-off Packet — Acute-Skill User-Facing Caveats (2026-07-14)

**Why this exists (clinical input, not a deploy footnote).** The SG-2 firing mechanism (PR #298) deterministically prepends a skill's `mandatory_caveat` to the user before the technique runs. It shipped for **dbt_tipp only**, because dbt_tipp was the one acute skill with an *authored user-facing caveat sentence*. An audit of the 7 sibling acute skills found **none has user-facing caveat copy** — only **model-facing `contraindications`** (directives to the AI, e.g. "Do NOT advance to exhale if…asthma"). Delivering those verbatim to a user is clinically wrong. So each skill needs a decision.

**The rule this packet follows:** a skill with no caveat is a **decision, not a gap**. For each skill: **tick** a cited proposal, **edit** it, **reject** it, or sign **NONE-NEEDED** (explicit — "no user-facing caveat required; contraindication is handled system-side"). Where the evidence base doesn't cleanly yield a single user-facing caveat, the proposal is left **BLANK** for the clinician to author or to rule referral-gate.

**Sourcing:** every proposal is transformed from the skill's existing model-facing `contraindications` (cited verbatim as evidence). Nothing here ships until signed. Route: same clinician channel as prior copy batches; PO relays. **Priority order = live exposure:** box_breathing first (most-routed acute skill, reachable now), then PMR, then the dissociation-sensitive set.

---

## 1. box_breathing — CITED PROPOSAL ⭐ (highest live impact: most-routed acute skill, reachable now)
**Evidence (model-facing, verbatim):** *"Do NOT advance to exhale if the user signals they are hyperventilating, cannot control their breath, or has flagged respiratory conditions, asthma, or a heart condition. Offer to skip the hold and go straight to a slow natural exhale."*
**Proposed user-facing caveat:** *"Before we start — if you have asthma, a breathing condition, or a heart condition, we'll keep this gentle and skip the breath-hold. Just let me know and we'll adjust."*
☑ **APPROVED — clinician yes, relayed by PO 2026-07-14; text as proposed, VERBATIM.** This is the primary sign-off record; box_breathing `mandatory_caveat` is set to this exact string and shipped under the safety exception (Ring-1 + 2.2 + firing test + driven transcript).

## 2. progressive_muscle_relaxation — CITED PROPOSAL
**Evidence (verbatim):** *"Do NOT instruct forceful tensing if the user discloses injury, significant chronic pain, arthritis, deep vein conditions, or recent surgery… Offer a modified approach: passive awareness… (awareness-only PMR)."*
**Proposed user-facing caveat:** *"Before we begin — if you have any injury, recent surgery, arthritis, chronic pain, or a circulation condition, tell me and we'll do this the gentle way, just noticing each muscle without tensing."*
☐ tick  ☐ edit: ____________  ☐ reject  ☐ none-needed

## 3. mindfulness_body_scan — CITED PROPOSAL (dissociation-sensitive — clinician wording judgment)
**Evidence (verbatim):** *"Do NOT proceed with body scan if the user discloses current dissociation, derealization, history of body-awareness triggering dissociation, or significant dizziness… Offer grounding alternatives."*
**Proposed user-facing caveat:** *"A body scan means paying close attention to physical sensations. If you're feeling detached or unreal right now, or that's something that tends to happen for you, let me know — we'll use a gentler, externally-focused grounding instead."*
☐ tick  ☐ edit: ____________  ☐ reject  ☐ none-needed
> Flag: overlaps SG-7 (dissociation/derealization contraindication). If SG-7 will own this as a referral-gate, sign **reject** here and defer to SG-7.

## 4. safe_place_visualization — CITED PROPOSAL (dissociation-sensitive)
**Evidence (verbatim):** *"Do NOT proceed if the user says they cannot imagine any safe place, that no place has ever felt safe, or that visualization consistently brings up threatening imagery… If the user reports feeling detached, unreal, floating… pause immediately."*
**Proposed user-facing caveat:** *"If picturing a calm place feels impossible right now, or imagining one brings up difficult images, tell me — there's no need to force it, we can just talk or try simple grounding instead."*
☐ tick  ☐ edit: ____________  ☐ reject  ☐ none-needed

## 5. mindfulness_meditation — BLANK (not a simple caveat — referral-triage; clinician to design)
**Evidence (verbatim):** *"For dissociation, derealization or depersonalization, an active trauma flashback, or psychosis-like content… do NOT present self-guided tools. Acknowledge warmly and escalate to professional support (a referral)."*
**Why blank:** the contraindication here is a **severity triage** (severe → referral; mild panic/rumination → redirect to grounding), not a single user-facing warning. A verbatim caveat would misrepresent it. Also: mindfulness_meditation is **routable-in-prod-while-unsigned** (separate open item). Clinician decision needed: (a) author a user-facing caveat for the *mild* branch only, and (b) confirm the severe branch is owned by the referral-gate / SG-7, not this mechanism.
☐ author caveat (mild branch): ____________  ☐ defer entirely to referral-gate/SG-7  ☐ none-needed

## 6. act_psychological_flexibility — BLANK (SI-screening gate, not a caveat)
**Evidence (verbatim):** *"Do NOT begin ACT if the user discloses profound hopelessness, passive SI, or acceptance framed as giving up… bridge to post_crisis_check_in or escalation."*
**Why blank:** this is a **passive-SI screening gate**, not a physical/technique caveat — it overlaps crisis detection and the passive-SI work, and a user-facing "caveat" would be inappropriate. Clinician decision: confirm this is owned by the SI-screening / crisis path (not this caveat mechanism).
☐ owned by SI-screening/crisis path (no caveat here)  ☐ author something: ____________  ☐ none-needed

## 7. stop_technique — NONE-NEEDED (proposed)
**Evidence (verbatim):** *"If emotional intensity is above 8, skip the frame and go directly to stop_pause or redirect to grounding."*
**Why none-needed:** the only contraindication is a **system-side intensity threshold** (ei>8 → reroute), with no physical/medical condition for the *user* to disclose. Proposed disposition: **no user-facing caveat**; the intensity gate is handled in routing.
☐ confirm none-needed  ☐ disagree, author one: ____________

---

**After sign-off:** ticked/edited caveats become each skill's `mandatory_caveat` (mechanical — the PR #298 mechanism already delivers it deterministically, EN + AR translate-out). Firing test + driven transcript per skill on landing. box_breathing is the priority pin (reachable + most-routed). None-needed/blank rulings are recorded so the "no caveat" state is an auditable decision.
