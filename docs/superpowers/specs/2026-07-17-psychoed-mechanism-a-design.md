# Psychoed Mechanism-A — instructional-skill consult before the info_request KB short-circuit — Design Spec

**Status:** approved to build (user directive 2026-07-17), scoped to **Mechanism A only** after the psychoed-cluster characterization REFUTED the single-mechanism hypothesis (see docs/2026-07-16 characterization; [[feedback_characterize_before_build]]). Branch `cdai/psychoed-mechanism-a` off master.

## Problem (characterized, not hypothesized)
23/30 psychoed presentations (§1f, §6d, §3c, S2c, §7c partial) classify as `info_request` — **and that classification is correct**: "why can't I sleep?" / "what is burnout?" *is* an information request. The bug is not the classifier; it is the router's downstream assumption that **`info_request → knowledge_retrieve` is always the right fulfillment**. `skill_select_node` short-circuits for info_request (skill_select.py:586-595), skipping its own keyword/semantic matching, and `_route_after_skill_select` force-routes to `knowledge_retrieve` (graph.py:345-346) → freeflow (graph.py:408). But the BOT BEHAVIOUR doc prescribes **instructional psychoed skills** for these categories precisely because an unstructured KB-dump-then-freeflow is the wrong way to teach someone about their sleep or burnout (the doc's Format column = *instructional* for this delivery mode).

## The fix's true shape
At the info_request short-circuit (skill_select.py:586-595), **consult instructional-skill matching BEFORE force-routing to KB. An instructional-skill match wins → the skill is delivered; no match → the KB path exactly as today.** Three properties, all load-bearing:
1. **Fail-open to current behavior.** Genuine info-requests ("what's the helpline number?", "how does this app work?") match no instructional skill and flow to KB untouched. The risk of breaking real info-requests is bounded **by construction**, not by tuning.
2. **A skill-matching *consult*, not an intent reclassification.** Do NOT touch `intent_route`. The classifier is right; only the router's downstream assumption is wrong. Fix at the short-circuit; blast radius = one branch.
3. **The must-stay-freeflow/KB controls ARE the acceptance test** (F6's over-suppression guard, this time inverted): the 4 controls from the characterization + genuine-info fixtures, red before / green after, per gating.

## Disposition scoping (re-scoped 2026-07-17 after the Task-1 finding) — NOT delivery-format

**Incident, on the record:** the first spec scoped the consult by *delivery format* (`Format == Instructional`), fusing two orthogonal axes. Task 1's grounding-first derivation returned `{sleep_hygiene}` — one skill, none of the cluster — because the psychoed categories' prescribed skills are Video/guided-conversation format, not Instructional. The premise "the doc prescribes *instructional* skills here" was false. **The two axes must never share a field:**
- **Disposition** — *what response does this presentation get?* (`target_presentations` / the doc's prescription column; the router's / node-4's question, Rules-Service territory).
- **Delivery** — *how is that skill rendered?* (`delivery_format`: video/guided/instructional/single_message/info_resource; P0b's field; the executor's / node-5's question).

The consult's question is a **disposition** question — does the doc prescribe a skill for this presentation, even though the intent classified as `info_request`? Delivery format is irrelevant to it. Scoping by format was an architectural misplacement (delivery as a routing input, which v7 nowhere licenses), not just an empirical miss.

**The consult scope (disposition, doc-derived):** `INFO_REQUEST_SKILL_CONSULT_SET = frozenset({"psychoed_anxiety", "psychoed_depression", "assertive_communication", "grief_loss"})` — the union of the `expected_skill_family` prescriptions for the four in-scope categories (§1f, §6d, §3c, S2c) per the layer-1 corpus (the doc-derived oracle). Matching is via each skill's existing `target_presentations` (the clinician-owned matching field node-4 already uses). **Only a match in this set is accepted for an info_request; experiential skills are never pulled in.** Fail-open: a genuine info-request ("what's the helpline number?") matches nothing in the set and hits the KB untouched.

**Name + governance:** the set is a **disposition** set, doc-derived engineering config (like B1's variants). Its in-code comment states the disposition-vs-delivery axis distinction and cites this incident, so the next reader can't re-fuse the axes. **No P0b convergence test on this set** — that test was pinned to the wrong axis; it lives (correctly) on `instructional_set.py`'s `{sleep_hygiene}` (delivery-format), which Task 1 already shipped and which stays.

**`{sleep_hygiene}` / `instructional_set.py` is kept** — it is the *correct* delivery-format derivation (P0b will consume it), just not the consult's scope.

## Where the code changes (two sites, one logical fix)
- **`skill_select.py` info_request branch (586-595):** before returning the KB-bound result, run the existing keyword/semantic matching; if the top match is in `INSTRUCTIONAL_SKILLS`, select it (set `active_skill_id` + a `skill_match_method` like `"info_request_instructional_match"`). If no instructional match, return the KB-bound result unchanged (today's behavior).
- **`graph.py` `_route_after_skill_select` (345-346):** the `if primary_intent == "info_request": return "knowledge_retrieve"` currently precedes the `active_skill_id → skill_executor` check, so a selected skill would still be sent to KB. Reorder/condition so that an info_request for which an instructional skill was selected routes to `skill_executor`; an info_request with NO skill selected routes to `knowledge_retrieve` (unchanged). Key on the new `skill_match_method` (or a dedicated signal), not on `active_skill_id` alone (a pre-existing active skill must not change this).

## Scope boundaries (from the characterization)
- **Mechanism A ONLY.** Not Mechanism B (7/30 `general_chat` → freeflow; folds later into the skill_suppression ruling's `_route_after_intent` territory). Not the §4a/§7c semantic-description gap.
- **§4a/§7c will NOT fully recover from this fix** — they have an independent matching gap (§7c's nearest match is out-of-family). That is a **clinical content question routed to the packet** (do not rewrite `semantic_description` to satisfy the router — reality-bent-to-fit-artifact with clinician-owned material). §1f and §6d recover cleanly (5/5 would-match); §3c/S2c partially.

## Acceptance (red before, green after; per gating)
- **Red tests = the 23 Mechanism-A drives verbatim** → reach the prescribed instructional skill (assert skill selected + routed to skill_executor, not KB/freeflow), for the categories whose skill would-match (§1f/§6d fully; §3c/S2c/§7c where they match). Where the matching gap blocks (§4a/§7c), the test asserts the *routing* now reaches skill_select-matching (the KB short-circuit no longer diverts them) even if the match itself is the packet's content gap — separate the routing win from the content gap in the assertions.
- **Must-stay-KB/freeflow controls (the guard fixtures):** the 4 characterization controls (topic-mention-without-request, e.g. "I'm so tired today" as chat) + genuine info-requests ("what's the crisis helpline number?") → route to KB/freeflow exactly as today. This is the over-pull guard; it is a REQUIRED fixture set, not an afterthought.
- OFF/unchanged paths: non-info_request routing byte-identical; the existing info_request→KB path byte-identical when no instructional match.
