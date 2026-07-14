# ESC-2026-07-14 — Skill-suppression authority is a missing abstraction (v7 architectural review)

**Class:** Architecture (v7 deviation, Absolute Rule 1) — not a bug; a missing layer that produces bugs
**Minted:** 2026-07-14 · verified against `master` `ea50e45`
**Route to:** Architecture owner (NOT clinical lead — this is a v7 structural question, not a clinical one)
**Related:** Spec `2026-07-14-bot-behaviour-routing-conformance-design.md` §3.3 · B1 PR #315 · F6 PR #318 · escalation `2026-07-14-medical-redflag-override-absent` (rev. 2)

---

## 1. The finding

**A deterministic signal that overrides the skill layer has no shared mechanism. Every instance is a per-node bolt-on.** There is no single place in the codebase that answers, for a given signal: *does it have authority over the skill layer, what does it suppress, what does it clear, what is its precedence rank, and how is it audited.* Each coupling is hand-wired, independently, with its own semantics.

This is not a maintenance concern. It is the mechanism by which a fifth `medical_response`-style bug ships without anyone noticing — because there is no one place where the question is answered once.

## 2. Evidence — four instances, one missing abstraction

| # | Instance | Where | The bespoke authority |
|---|---|---|---|
| 1 | psychotic-referral redirect | `_route_after_intent` | a hand-wired `if` forcing `skill_select` (psychotic_referral auto-selects) |
| 2 | Routing-SF-2 / v7.2 prepass | `_route_after_intent` | two hand-wired `if`s pulling high-intensity / keyword-matched `general_chat` into `skill_select` |
| 3 | F6 venting suppression (PR #318) | `_route_after_intent` | a hand-wired `if` routing venting to `freeflow` — a *new* signal→authority coupling, added because PI-VI-001 detected venting but **had no authority** to stop the skill layer |
| 4 | B1 `medical_response` skill-clear (PR #315) | `medical_response` node | a terminal that had to be *reminded* (in final review) to clear `active_skill_id`/`active_step_id`/`offered_skill_ids` — or a coping skill resumes after a medical referral |

Instances 3 and 4 are the same bug in two nodes: **detection without authority over the skill layer.** F6 gives a signal routing authority by bolting on a branch; B1's terminal forgot to clear the skill lifecycle because nothing *makes* a skill-overriding decision declare what it clears. Neither is auditable as a member of a class, because there is no class.

## 3. Why it compounds — the trajectory is 37 bolt-ons

BOT BEHAVIOUR is explicit: **every one of its 34 categories carries a "Guard — Do Not Present This Pathway If" block.** Suppression is not a special case in that document — it is a **universal layer** sitting above skill matching (spec §3.3 already names this). The codebase has no representation of that layer.

So the current trajectory is **~37 bespoke branches** in `_route_after_intent` (and terminal nodes), each with:
- its own precedence semantics (does it beat crisis? beat SF-2? beat another guard?),
- its own decision about what to clear (and B1 proves that decision is silently omissible),
- no shared audit record ("a suppression fired, here is which signal and what it withheld"),
- no single review surface where "signal → authority" is checked as a class.

Four bolt-ons already disagree on structure (three are routing `if`s, one is a node return). Thirty-seven will not converge on their own.

## 4. The missing abstraction

A deterministic signal that overrides the skill layer needs **one mechanism**, evaluated in **one place**, that declares for each signal:

```
signal            (the deterministic detector: venting, medical red-flag, psychotic, guard-X…)
→ authority       (does it override the skill layer, and at what precedence rank)
→ suppresses      (route to presence / route to terminal / withhold offer)
→ clears          (active_skill_id, active_step_id, offered_skill_ids — declared, not omissible)
→ audit record    (one row: which signal fired, what it withheld, its precedence)
```

With this, F6 is a table entry, not a branch. B1's skill-clear is a property of the mechanism, not a thing a node can forget. A fifth guard is a row someone reviews against the same five columns. The 34 BOT BEHAVIOUR guards become data in one registry, not 34 more `if`s.

**Design it to cover two objects, not one.** There is a sibling shape: **delivery suppression** (S1b's timing rule — *don't hand over the sleep-hygiene resource at night; brief tips now, full resource by day*). That is not skill suppression — the skill is selected; what's withheld is the *delivery/rendering* of a resource, conditionally. Same "signal → authority → withhold → precedence" shape, **different object** (a delivery decision, not a selection decision). If the abstraction is designed for skill-suppression only, delivery suppression becomes bolt-on #38 in six months. The mechanism should model *what* is being suppressed (selection vs delivery) as a field, so both ride it.

## 5. Why this is a v7 deviation (Absolute Rule 1)

It does **not contradict** the v7 spec — it reveals the spec is **silent where it needed to speak.** The Rules Service defines a **`skill_matching`** rule category (how a matched skill *enters*). There is **no `skill_suppression` category** — no representation of a signal that says *do not present a skill here, and clear what's active.* Skill suppression is currently implemented as the **absence** of matching, per-node, ad hoc.

**And v7 already suppresses in four other places, none unified — which is the real tell.** The living arch doc shows suppression re-implemented ad hoc across the system: `crisis_suppress` and `false_positive_exclusions` (safety rule actions that suppress crisis flags), the `escalating_distress` flag *"suppressed when a skill is active AND engagement ≥ 5"* (arch doc §, a hardcoded condition), and the planned `emotions_disclosed` field to *"make the suppression concrete"* (still blocked on a clinical decision about *permanent within-thread vs transient* suppression — exactly the "what does it clear / how long" question the abstraction answers). Suppression is not a new concept in v7; it is a **recurring one that has never been named as a class.** Skill suppression (F6) is the fifth ad-hoc instance. That silence is the gap, and closing it is an architectural decision that needs the owner's sign-off, not an incremental code change.

## 6. Ask

1. **Ratify or amend the abstraction** in §4 as the v7 representation of skill-suppression authority (a `skill_suppression` Rules-Service category + a single evaluation point + a declared-clears contract + an audit row).
2. **Decide the migration**: F6 (#318) and B1's skill-clear (#315) ship as bolt-ons now (both flag-gated / reviewed); the abstraction is where they and the 34 BOT BEHAVIOUR guards converge, so the per-node instances are retired onto it rather than multiplied.
3. **Scope of what this ruling gates (corrected — it is NOT the whole feature queue):**
   - **Gated by the ruling:** F5's **ceiling** ("route to human support" — at ceiling no skill is offered and the turn redirects: signal → authority → suppress → redirect, the same mechanism as F6) and **all 34 category Guards** (each is suppression by definition). Component #2 of conformance — the largest single chunk — is this.
   - **NOT gated:** **P0b `delivery_format`** governs how an *already-selected* skill is rendered — entirely downstream of selection, zero contact with suppression authority (schema field + executor read + renderer). **Proceed independently.** **F5 band logic** (mild/moderate/high → which skill, menu vs no-menu) and **step-up/step-down** are `skill_matching` / `step_policy` / `escalation_matrix` — selecting or transitioning differently is not suppressing. **Proceed independently.**
   
   This ruling **outranks the queue for *architectural review*** — not because it is urgent (nothing is on fire), but because it is the only architectural finding in the investigation; the rest are bugs. A design decision made now costs one review; made after 37 bolt-ons, it costs a rewrite.

---

## Appendix — related process finding (small, cheap, keeps paying)

**Plan-artifact drift, caught three times by between-task review:** B1 Task 3 (`state.get("message_en")` would break the AR path), B1 Task 4 (hand-built audit dict vs `write_session_audit(state)`), F6 Task 2 Step 4 (guard un-scoped on intent → over-suppression). In each, the plan's own **sample code** carried a bug the review caught before it shipped. The plans are being written from a *model* of the code rather than the code, and between-task review is the only thing standing between that and production. **Cheap fix:** verify sample code against the actual tree before a plan is committed. It is not a substitute for review, but it removes a recurring, predictable class of review finding.
