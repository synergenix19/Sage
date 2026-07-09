# §3a Low-Mood — SDD progress ledger
Branch: feat/low-mood-3a-impl (off origin/master 140ff2d)
venv: .venv/bin/python -m pytest
Baseline: 3 pre-existing test_nodes.py Arabic-translation-mock failures on clean master (not ours).

Task 1: complete (commit ee6f4ca, flag + cross-turn state fields, inline, tests green)
Task 2: in_progress (skill_select §3a interception, EN-gated, + precision set) — subagent-driven

Task 2 review (base ee6f4ca..62ad9b5): SPEC ✅ / CODE QUALITY changes-requested.
  Findings:
  - [Important #1] is_low_mood_disclosure matches ~only its own test strings; real §3a
    paraphrases false-negative -> unscreened BA offer. Confirmed by probe (BA offerable but
    detect=False for "I have no motivation for anything anymore"). Detector also does real
    precision work ("tired after a long week": BA offerable, correctly excluded). Root cause:
    brief gave 10 e.g. phrases as if a complete set. Trigger set is CLINICIAN-OWNED ->
    ESCALATED as a decision (needs signed §3a trigger set + robust matching + data-file).
  - [Important #2] AC2 rewrite authorization recorded only in report -> closing via durable
    record (this ledger + controller verified the arabic_offer_excluded repro independently).
  - [Minor #3] stale prod comment skill_select.py:560 "today's offer path" (AR is direct-entry).
  - [Minor #4] dead `offerable` kwarg in tests (inert; tests pass via real Tier-1 keyword match).
  - [Minor #5] trigger list inline vs ocd_compulsion's CMS-JSON single-source -> fold into #1.
  STATUS: Task 2 structurally correct; NOT complete — #1 open, human decision required before Task 3.

Task 2 hardening (30de34c) REVIEW: SPEC ❌ / CODE QUALITY changes-requested — REJECTED.
  Adversarial novel-input review (verified independently by controller):
  - Novel §3a recall = 2/15 (13.3%) — same overfitting as v1; regexes fit the 10 seed paraphrases, not the family/scope discriminator. "nothing excites me anymore", "I feel hollow", "zero drive" all MISS.
  - Novel look-alike FP = 3/15 (20%) — NEW safety negative. "I feel stuck in traffic", "no energy left to clean the kitchen tonight", "nothing fun at this party" all FIRE -> SI question -> broken GL-1 card.
  - NOT single-sourced: matching runs on a hand-typed _LITERAL_PHRASES tuple + regexes, JSON only feeds tests -> clinician edits won't change behavior (the drift risk we set out to close).
  DECISION: two deterministic attempts have now failed to generalize. §3a detection is a SEMANTIC problem, not keyword/regex. Escalated to user: revisit the "deterministic only" constraint; recall likely belongs to the existing semantic BA-offerable signal, precision to a semantic filter or BA's own target_presentations. Do NOT dispatch a third regex fix. Hardening 30de34c to be reverted or redesigned per user's approach decision. Flag stays OFF regardless.

SEMANTIC-GENERALIZATION PROBE (2026-07-10, direct _semantic_match_with_runner_up, warm model):
  Novel §3a paraphrases -> behavioral_activation:
    "nothing excites me anymore" -> None (0.44)      MISS
    "I feel hollow inside"        -> box_breathing (0.43) WRONG SKILL
    "drag myself out of bed"      -> behavioral_activation (0.50) HIT
    "zero drive to do anything"   -> None (0.46)      MISS
    "stopped replying to friends" -> None (0.42)      MISS
    "everything feels pointless"  -> None (0.44)      MISS
    => semantic §3a recall = 1/6.
  Look-alikes:
    "tired after a long week"     -> behavioral_activation (0.53)  SPURIOUS + HIGHEST score of all
    "no energy left to clean..."  -> None (0.42)      ok
    "stuck in traffic"            -> worry_time (0.47) wrong skill
  CONCLUSION: the scope discriminator defeats semantic similarity TOO. Semantic recall for §3a is
  weak (1/6) AND mis-fires on the situational look-alike with the HIGHEST score (embedding captures
  surface energy/tiredness, not the §3a construct). So "semantic recall + precision gate" does NOT
  work cleanly. HONEST ANSWER (Vee's anticipated harder territory): §3a screening-ELIGIBILITY needs
  a trained classifier (same class as crisis-tier S2/MARBERT), eval-gated on List A/B, err-toward-
  not-asking. Minimal deterministic detector stays as flag-OFF placeholder; robust eligibility is a
  roadmap/classifier gate. DETERMINISTIC SI-ANSWER CATCH (Task 3) is unaffected and is where the
  safety determinism lives -> still the right next build.

CONTENTION (2026-07-10): parallel crisis session's git stash -u swept 5 uncommitted safety files in
  sage-poc-crisisfix (safety_check.py, crisis_keywords.json, passive_si_patterns.json, engine.py,
  safety tests) into stash@{0} (WIP on master f44d30b); checkout restored to clean master 098469c.
  stash pop will CONFLICT (master advanced via PR#269 t2-ordering touching same files) -> theirs to
  resolve w/ sign-off. IMPACT ON US: Task 3 edits safety_check.py = same contended file. Do NOT build
  Task 3's safety_check edit blind into this; rebase impl branch on current master (098469c) and
  coordinate merge order with the crisis workstream, OR sequence Task 3 after their safety work lands.

*** CORRECTION (2026-07-10): the semantic probe above is REJECTED as design-driving evidence. ***
  It measured a possibly-cold model via a bypassed-timeout direct call with hand-rolled query
  construction (bare utterance, empty profile), NOT the real prod routing path. Tells of a broken
  measurement, not a hard problem: (1) ALL inputs scored in a flat 0.42-0.53 band = matcher not
  discriminating anything; (2) look-alike "tired after a long week" scored HIGHEST (0.53), the
  discriminator inverted; (3) it CONTRADICTS established prod behavior (BA-offerable already routes
  real §3a paraphrases — the interception is gated on exactly that), and when a probe contradicts the
  system it probes, the probe is on trial. The "§3a needs a trained classifier / S2-MARBERT roadmap"
  conclusion is WITHDRAWN — unproven, not settled. Re-probe required through the genuine warm routing
  path with a calibration anchor before any classifier decision. DECOUPLED from the Task-3 contention
  hold, which stands on its own (correct regardless of how the detector question resolves).

VALID RE-PROBE (2026-07-10, calibration-gated, real V2 path: exemplar anchors + reranker ON):
  Calibration PASSED: canonical §3a -> behavioral_activation 0.853; anxiety -> grounding; "grocery
  store close" -> None 0.572. Measurement trustworthy (contrast the prior artifact: bi-encoder only,
  no exemplars, no reranker -> flat 0.42-0.53 band).
  Novel §3a recall = 5/5 -> behavioral_activation (0.72-0.85). Look-alikes: "tired after a long week"
  -> sleep_hygiene (NOT BA), "no energy to clean kitchen" -> None, "stuck in traffic" -> None = 0/3
  spurious BA.
  CONCLUSION (reverses the withdrawn one): the semantic V2 routing GENERALIZES for §3a. No trained
  classifier / S2-MARBERT roadmap needed. Design "semantic recall (BA-offerable) + precision gate +
  deterministic SI-answer catch" is clean and BACK ON. The hand-rolled keyword detector can likely be
  DROPPED. Residual precision note: the earlier "tired -> BA offerable" was a KEYWORD-tier
  (target_presentations) artifact, not semantic; the semantic tier routes "tired" -> sleep_hygiene. So
  the residual precision fix is a targeted tightening of BA's keyword target_presentations, NOT a
  classifier. CAVEAT (do not over-conclude twice): sample is 5 §3a + 3 look-alikes; confirm on the full
  List A/B eval set through this same calibration-gated path before finalizing the precision guard.
  Process: the calibration anchor is what made this trustworthy — Vee's prescribed check. Decoupling
  held: Task-3 contention hold stood on its own; only the design conclusion was the artifact.

FULL-EVAL (2026-07-10, calibration-gated harness, config-stamped; oracle = PROPOSED-unsigned List A/B
@ dfbff92 sha 8ae6cdd42fda; V2 exemplars + reranker on, threshold 0.4593, anchors [996,1024]):
  CALIBRATION PASSED (canonical §3a->BA; unrelated,anxiety NOT BA) -> numbers trustworthy.
  List A recall = 0.641 (25/39) on PROPOSED List A -> FAIL (pre-reg >= 0.90).
  List B FP     = 0.200 (3/15)  on PROPOSED List B -> FAIL (pre-reg = 0.00).
  MISS-CLUSTER (amendment b — risk-relevant, not aggregate): 14 misses concentrate in TERSE canonical
    markers, worst = AFFECTIVE FLATNESS 4/4 ("I feel flat/numb/disconnected/not myself") + energy/effort
    3 + "nothing sounds enjoyable"/"can't be bothered"/"don't want to talk to anyone". Verbose paraphrases
    hit; short clinical markers miss -> a hole in a high-risk sub-band, NOT a benign 36% loss.
  FP breakdown: 2 SEMANTIC ("gym today" 0.79, "nothing fun to do right now" 0.85) + 1 KEYWORD
    ("no energy today"). So precision holes are NOT purely keyword-tier; the semantic layer over-fires too.
  CONCLUSION: "drop keyword detector, rely on semantic BA-offerable" is REFUTED by this run — semantic-
    alone = 64% recall with a flatness-cluster hole + its own 2 semantic FPs. Keyword detector NOT
    droppable. My earlier 5/5 spot-check was unrepresentative (Vee's "don't over-conclude twice" — realized).
  NEXT (targeted, measurable — NOT a classifier decision yet): does enriching BA's semantic_anchors with
    the missed terse §3a markers (esp. affective flatness) + tightening for the 2 semantic look-alike FPs
    move the semantic path to the pre-reg gate? Re-run this harness after anchor tuning. If it reaches
    recall>=0.90 & FP=0 -> semantic-with-tuned-anchors is the mechanism. If not -> the classifier question
    re-opens HONESTLY (on valid measurement this time), not before.
  STATUS: design "semantic owns recall" is NOT confirmed — it FAILED design-confirmation. recall>=0.90 was
    the DESIGN gate; flag-flip recall remains Vee's clinical acceptance call regardless. Task-3 hold stays
    decoupled + independent.

JOINT-PATH CONFIRMED (2026-07-10): the 0.641 full-eval WAS the combined keyword+semantic path (not
  semantic-in-isolation). Proof: List A tier dist = {semantic_offer:28, no_match:7, keyword_offer:4};
  BA-offerable hits = {semantic:21, keyword:4}. Keyword Tier 1 live (4 exact target_presentations hits).
  => "did we already fix this" = NO; combined prod routing = 64% recall on §3a. Residual survives BOTH tiers.
  RESIDUAL ROUTING (for Vee's true-gap-vs-defensible-edge read):
    NO-MATCH (route to NOTHING) — clearest gap: "everything feels like an effort", "stay under the
      covers", "nothing sounds enjoyable", "can't be bothered", "I feel numb", "I feel disconnected".
    ROUTED-ELSEWHERE (often depression-ADJACENT, arguably handled): "I feel flat"->{body_scan,
      psychoed_depression}; "going through the motions"->{mindfulness,mood_check_in}; "don't feel like
      myself"->{cbt_thought_record,cognitive_restructuring}; "keep putting everything off"->{cbt,
      problem_solving}; "I feel stuck"->{act,worry_time}; "even small tasks difficult"->{act,dbt_tipp};
      "build a better routine"->{body_scan,problem_solving}.
    NOTE on the dissociation concern: "I feel numb"/"disconnected" route to NOTHING (no-match), NOT to a
      dissociation skill -> the anchor-enrichment clinical-error risk (routing trauma->BA) is real but not
      currently manifesting as mis-routing; they're simply unmatched.
    VARIANCE CAVEAT: "I don't want to talk to anyone" (harness MISS/None) vs "I do not want to talk to
      anyone" (offered BA) -> borderline §3a markers are phrasing/contraction-sensitive; the exact 64% has
      surface-form noise (picture robust, exact number soft).
  NEXT: residual -> Vee for the clinical read (which are true §3a gaps that should fire BA vs defensible
    routing to an adjacent skill). NO anchor-enrichment until that read (per Vee: enriching a
    dissociation-adjacent marker would route trauma->BA = clinical error). Keyword detector NOT dropped.
    Design NOT confirmed. Task-3 hold decoupled + flag-OFF, unchanged.

SPEC-GROUNDED RESIDUAL READ (2026-07-10, BOT BEHAVIOUR.docx, cross-category verified by line):
  Checked all 14 residual misses against the docx by name AND for cross-category claims.
  TRUE §3a GAPS (~11 — spec lists the bare STATEMENT only/primarily under §3a -> should reach §3a screen):
    "everything feels like an effort"(525), "stay under the covers"(525), "nothing sounds enjoyable"(527),
    "can't be bothered"(529), "even small tasks feel difficult"(525), "keep putting everything off"(529),
    "I feel flat"(533), "I feel disconnected from everything"(533; the 657 hit is the QUESTION form ->
    §3c), "going through the motions"(535), "build a better routine"(537), "don't want to talk to anyone"(531).
  ORACLE EDGES (3 — spec ITSELF cross-categorizes the bare statement; routing elsewhere is spec-DEFENSIBLE;
    Vee owns the boundary; force-enriching into BA would VIOLATE the spec):
    "I feel numb" = §3a(533) AND S2a FRESH/RAW GRIEF(1600, identical bare phrase) -> enriching numb->BA
      pulls GRIEF into behavioral activation = the clinical error Vee named.
    "I don't feel like myself" = §3a(533) AND §2b VALUES/identity(470 "I don't feel like myself anymore").
    "I feel stuck" = §3a(535) AND §2a practical-decision(418, identical) AND §2b(478) AND S2b grief(1659).
  IMPLICATION: the real §3a recall gap = the ~11 §3a-only markers (25/36 excl. edges = 0.69, still < 0.90).
    Any future anchor-enrichment targets ONLY these 11, NEVER the 3 edges. The spec (Vee-approved) ANSWERS
    most of the read; only the 3 edges need Vee's explicit boundary call. Held the meta-pattern: spec check
    FIRST (Vee's instruction), no jump to fix. Task-3 hold + flag-OFF unchanged.

*** APPROVED (Vee, relayed 2026-07-10): R1-R7 + CD1-CD5 + trigger-set List A/B all signed. ***
  Oracle low_mood_3a_triggers.json flipped PROPOSED -> SIGNED. Design CONFIRMED (was pending).
  Signed calls: R1 semantic+scoped-anchor (no classifier); R2 determinism on SI-answer catch;
  R3 11 §3a gaps (CD1: tier by DSM strength); R4/CD3 exclude numb/stuck/feel-like-myself from BA,
  clarifying-turn default for bare numb, suppress BA in acute grief; R5/CD4 two-tier recall
  (fail-safe screen ~80-90%, acute-SI catch near-zero-miss); R6/CD5 err-toward-not-asking, rationale
  = specificity/burden/trust NOT "asking harms"; R7 signed-oracle governance + flip-gates.
  NOW UNBLOCKED (in order): (a) apply CD1 tiering + CD3 exclusions to the signed oracle; (b) run the
  SCOPED enrichment (BA semantic_anchors for the strong §3a-only markers, NEVER the 3 edges) against
  the SIGNED oracle via the calibration-gated harness — measure recall + FP + BA GLOBAL side-effects
  + the affective-flatness miss-distribution (Vee's watch-item), not just aggregate; (c) if it clears
  CD4 band + FP=0, retire keyword detector in a commit that shows the eval justifying it; (d) Task 3
  (deterministic SI-catch) after the crisis safety_check contention lands; (e) flag flips only when
  ALL R7 gates clear (signed lists + recall bar + FP=0 + GL-1 fixed + DPO + AR unit for Gulf).
  MEMORY: this approval is for the COMMAND SESSION to write; this work session does not.
  BRANCH: enrichment touches BA global routing -> build off CURRENT master (impl branch is behind),
  coordinate with the skill_select workstream, keep flag OFF throughout.

=== HANDOFF TO COMMAND SESSION (memorialize first, then release step 2) ===
CORRECTED MEMORY LINE (preserve signed != certified):
  "§3a low-mood: full design (R1-R7) + clinical decisions (CD1-CD5) DESIGN-SIGNED by Vee 2026-07-10;
   trigger-set List A/B now the signed eval oracle. SIGNED != CERTIFIED — performance numbers are
   measured only against the now-signed oracle at ENRICHMENT time, which has NOT been run. Enrichment-
   measurement + flip-gates pending; keyword-detector retirement gated on the eval; Task 3 gated on the
   crisis safety_check contention. Flag OFF throughout."
STEP-2 CONSTRAINTS (now documented in scripts/low_mood_3a_semantic_eval.py header, wire before running):
  (1) CD3 edges -> HARD ABORT if BA-offerable post-enrichment (like calibration anchor).
  (2) flatness-cluster recall -> its own stamped pass/fail criterion, separate threshold.
  (3) non-§3a CONTROL set -> assert BA global offer-rate does not rise (List B won't catch it).
STEP 2 = run off CURRENT master, coordinate with skill_select workstream, flag OFF, don't start until
  command session releases it. Do NOT start step 2 in the current work session.
