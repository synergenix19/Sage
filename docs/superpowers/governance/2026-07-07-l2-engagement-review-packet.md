# L2 Engagement Batch — Clinical Review Packet — 2026-07-07

**For:** clinical lead (sign-off), one review session covering the four L2 template drafts, the PI-SI-001 upgrade (separate artifact, same session), and ratification of the deviation register.
**Prepared by:** engineering (drafts authored for clinical redline; `approved_by: null` throughout).
**Companion docs:** deviation register `2026-07-07-l2-engagement-deviation-register.md` (READ FIRST — carries the budget amendment); PromptFoo cases `drafts/2026-07-07-l2-engagement-promptfoo.yaml`; RCA memory `project_info_request_engagement_gap.md`.

## Session opener: what you are ratifying (four gap classes, one posture system)

This work began as a single screenshot bug report (a KB answer reading as a dry, list-shaped dead-end). Tracing it to root closed **four distinct gap classes**, and you are ratifying the system that stops any of them silently recurring, not just four template rewrites:

1. **Content gap** — `info_request` and its siblings never received the 2026-06-14 engagement rewrite (still on the pre-engagement "do not pad" template). Closed by the four template drafts.
2. **Mechanism gap** — blended intent is live-but-partial: `PI-SI-001` injects a generic symmetric DBT frame, not the v7 §5.6.1 *ordered* validate-then-inform contract; single-intent turns bypass it entirely. Closed by the PI-SI-001 v2.0.0 draft (this session).
3. **Architecture violation** — `low_confidence` bypassed `compose_prompt` (L0 never composed), a §5.6.3 breach. Remediated in PR #124; its content is ratified here.
4. **Systemic process gap** — nothing forced an L2 surface to declare an engagement posture, which is *why* PR #4 rolled out partially. Closed by the engagement-posture manifest + enumeration guard (PR #127, merged).

The **deviation register + the manifest** together mean none of these can silently recur. That systemic control is the substance of what you are signing, with the four template rewrites and the PI-SI-001 upgrade as its content.

## The one decision this packet asks you to make first: the bridge rule

The reported bug: KB/"Ask" answers (`info_request`) read as dry, list-shaped dead-ends with no conversational continuation, because the `info_request` template never got the 2026-06-14 engagement rewrite and still says "answer briefly, do not pad with unsolicited support." The fix must decide HOW an info answer closes. This is a clinical-strategy call, so it is put to you explicitly rather than baked into the wording. Ratify the RULE, then the wording.

| Option | Rule | Why / why not |
| --- | --- | --- |
| (a) | Always close with one bridge, phrased generically | Deterministic, but a generic close can read as preachy on a purely factual turn. |
| **(a\*) — DRAFTED** | **Always close a single-intent info_request with exactly ONE light bridge, conditionally PHRASED (invitation, not assumption), affect-neutral by construction** | Deterministic (no runtime detection), yet the conditional phrasing does the targeting: it lands for a distressed user and reads as a harmless offer to a curious one. Matches the Abby benchmark close, which is itself affect-neutral ("if anxiety is making life hard, it might help to talk with someone"). Keeps the "do not pad" clause's real core (no affect assumption) and deletes only its engagement-killing scope. |
| (b) | Bridge only when the turn carries affect/self-reference signal | REJECTED (architectural). Needs runtime affect detection, which can only live (i) in the template as LLM discretion = Cardinal Rule 3 violation (LLM choosing therapeutic strategy), (ii) in intent_route = redundant, since affect+info IS blended intent by definition (primary general_chat/new_skill + secondary info_request), so a single-intent info_request is by contract affect-free, or (iii) in the Rules Service keyed on emotional_intensity = a legal but SECOND overlapping mechanism before the first (PI-SI-001) is validated. Keep (iii) as the documented escalation path if you want affect-conditioning later, not the v2.0.0 design. |
| (c) | Bridge only when a KB passage grounds the answer | REJECTED (backwards). ABSTAIN turns are the ones that MOST need a bridge: a terse "I don't have that information" is a retrieval failure AND a conversation dead-end, the exact reported bug on the worst turn. Grounding availability shapes the answer, it must never gate the engagement. |

**Engineering recommendation: (a\*).** The drafts are authored on it. If you prefer (a), (b), or (c), the wording changes accordingly.

## The four drafts (all `approved_by: null`, not loaded, in docs/)

1. **`info_request` v2.0.0** — rule (a\*). Validate-free but warm; answer directly; ground in passages / honest ABSTAIN with no fabrication; exactly one conditional invitation as the close and as the ABSTAIN recovery; explicit "do not assume the person is struggling, no unsolicited sympathy." Instruction budget 50→**160** (needs the budget amendment). Separately, R-1 psychoeducation **80–150w** is the desired OUTPUT length — reviewers may state that range explicitly in wording; it is a different number from the instruction budget.
2. **`new_skill` v1.1.0** — inherits the conditional-invitation principle where a next step fits; consent-preserving ("shape it or set it aside"); no affect assumption. 50→100w.
3. **`exit_skill` v1.1.0** — warm no-pressure transition + one conditional invitation to name what they want to focus on now. 50→80w.
4. **`low_confidence` v1.1.0** — **content ratification only**, NOT an expansion. Ratifies the behaviour-frozen text already merged live via PR #124 as approved content. Its single clarifying QUESTION is the bridge; no second bridge added. **Keeps the 2-sentence cap — SAFETY-COUPLED:** that cap is what keeps the (suppressed) freeflow guardrail benign on this path. Relaxing the cap requires re-enabling the guardrail on the override path in the same change.

## What your sign-off in this session clears — and what it does not

CLEARS (clinical content gate): ratify the bridge rule; set `approved_by` + `status: approved` on the four templates (promote wording into the live `src/.../L2_intents/*.json` on promotion); ratify the deviation register's budget amendment (item 1) and taxonomy note (item 2); sign the PI-SI-001 ordered-contract upgrade.

DOES NOT CLEAR: PR #124 engineering review (separate, done); the L2-enumeration regression test (separate small eng PR); the overflow/L1-budget accounting defect #125 (eng, coupled to the budget amendment); the PromptFoo harness wiring (eng); and merge/deploy authority (product owner triggers; deploys are manual).

## Promotion path (post sign-off) — obligation on the promoter

On sign-off, whoever promotes an approved template into `src/.../templates/L2_intents/*.json` must, **in the same change, re-confirm its engagement posture and bump `classified_against_version` in `prompts/l2_engagement_manifest.json`** (per merged PR #127). The version-drift guard reds the build otherwise — by design: content cannot be re-versioned without a posture re-review. Concretely, promoting `info_request` to v2.0.0 requires re-confirming its `engagement_bridge` posture and setting `classified_against_version: "2.0.0"` in the manifest. Same for `new_skill`/`exit_skill` v1.1.0; `low_confidence` v1.1.0 is content-identical to the PR #124 live text, so promotion is only setting `approved_by` (no content copy) plus the manifest re-confirm.

## Test evidence status (read before the session)

Evidence is split into what can be verified without a live model and what needs one:

- **Deterministic layer — GREEN NOW (attached).** `tests/test_l2_engagement_drafts_composition.py` (7 tests) proves the drafts encode rule (a\*): single conditional bridge, no affect-assumptive phrasing, ABSTAIN-as-recovery, grounding, single-question, no em dashes, list-directive compatibility. Plus `test_l2_engagement_manifest.py` (the enumeration guard) and the composer shim verified to compose the draft bridge + L0 + L4 for every scenario without an LLM.
- **LLM-output layer — RUN 2026-07-07: 4 / 5 passed.** The five PromptFoo cases ran against the DRAFT templates via `openrouter:openai/gpt-4o` (key injected from Railway). Full analysis in `2026-07-07-l2-engagement-promptfoo-results.md`; raw output in `drafts/2026-07-07-l2-eval-results.json`. Passes: pure-factual (bridge, zero assumed distress), affect-slipped-single-intent (conditional bridge lands), ABSTAIN (bridge-as-recovery, no fabrication), negative (no affect-assumptive opener). **One failure (list-compat):** on a pure symptom-list turn the model did not lead with a one-sentence plain answer before the list (the L4 lead-with-prose directive) — the rule-(a\*) bridge and affect-neutrality HELD on that case. It is a prompt-adherence signal, not a bridge failure. The lead-with-prose directive is **L4-owned** (`light_structure_directive`), so the decision is **accept vs. reinforce-in-L4** — reinforcing in the L2 `info_request` draft is prohibited by §5.6.2 single-ownership and is struck. See the results doc for the reframed decision plus the Falcon-transfer caveat and the do-not-move-to-the-output-gate note. Post-decision test disposition (results doc): reinforce-in-L4 → re-run to 5/5; accept → rewrite the case to encode the accepted behaviour (list without prose lead-in = pass, bridge + affect-neutrality still asserted), not left red and not deleted. Reported as-is, not patched to force green.

## Standing constraints verified in every draft

No em dashes (mirrors into output). No affect-assumptive language on factual/single-intent turns. Grounding/ABSTAIN rules unchanged and independent of the engagement change. List-directive compatibility: the bridge is a closing line that coexists with the L4 light-structure numbered-list output. PromptFoo cases encode each failure mode (pure factual → bridge, zero assumed distress; affect-laden-slipped-single-intent → conditional bridge lands; ABSTAIN → bridge as recovery, no fabrication; negative → no affect-assumptive phrasing; list-compat).
