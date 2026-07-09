# Containment Pathway (Phase 2 Task 0) — Signature Asks to Relay

**Status:** the deviation-design spec (`2026-07-08-clinical-containment-pathway-design.md`, PR #200) is complete and assembled from already-ruled decisions — nothing in it should surprise a signatory. Per the blocking gate, NO Phase-2 implementation starts until all three are recorded. These are the three one-paragraph asks to relay. **Build begins the moment they land; if they stall past this week it is a scheduling item, not a build-ahead license.**

## → Arch-doc owner
The containment pathway adds one Rules-Service action (`contain`), one `SageState` field (`containment_directive`), and ONE conditional graph edge (directive present → knowledge_retrieve → freeflow, or skill_executor) — no new node, no rewrite. It is an Absolute-Rule-1 amendment to the v7 graph. Please review §2 (the six-point design) and sign that the graph-edge / state-schema / Rules-Service-vocabulary change is architecturally sound. Everything downstream is content behind CMS.

## → Clinical lead
Containment is a new first-class response class — validate → psychoeducate → differentiate → risk-check → **refer** → engage — for disclosures that must not get a self-help skill and deserve more than bare clarification (OCD/intrusive, and the #1 safeguarding family). The clinically load-bearing pieces are already your rulings: the **ego-syntonic/psychosis → crisis** branch (absence of distress / command-language is the danger signal, not the reassuring one), the first-person-vs-third-party family split, and the safeguarding posture (referral-with-urgency + mandatory L2 review). Please sign that containment-as-a-destination-class + the template steps + the ego-syntonic branch are clinically correct. (Harm-intrusive lexicon + phasing already signed 2026-07-08.)

## → PO
This is an Absolute-Rule-1 architecture deviation. Please sign (a) acceptance of the deviation, (b) the **bounded-scope discipline** — Phase 2 builds ONLY the three approved families (harm-intrusive enrichment, OCD upgrade, safeguarding); the audit's other Class-A discoveries go to the CMS backlog you prioritize, they do NOT enter Phase-2 scope by discovery — and (c) the **2026-07-31 safeguarding target date**.

---

# One-Writer Control — word to relay to the parallel session(s)
Three stale-build incidents and two clobbers happened THIS quarter under less concurrency than we have right now (live prod moved 7f2b30d → 7c038da under an active deploy; #205 and #213 merged in parallel). **Deploys must serialize through `2026-07-08-prod-deploy-control.md`: one writer claims the prod window explicitly, deploys detached `origin/master` (never a feature branch) with a full-SHA cache-bust, verifies the fresh-code provenance field + a behavioral probe, and runs the ancestry gate.** Uncoordinated `railway up` is how the next silent clobber happens — when, not if. If you are deploying, claim the window first.
