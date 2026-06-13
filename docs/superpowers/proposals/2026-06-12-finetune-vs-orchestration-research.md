# Fine-Tuning on Therapy Scripts vs Prompt-Orchestrated Skills — Research Synthesis

**Date:** 2026-06-12
**Status:** Research synthesis — answers the follow-up question raised by the engagement-layer proposal (§4 "Long-term")
**Question:** Should Sage fine-tune/train the responder model on therapy transcripts, or does the current prompt-orchestrated skills architecture deliver better results?
**Method:** Deep-research harness: 5 search angles, 25 sources fetched, 124 claims extracted, top 25 adversarially verified (3 independent refutation votes each; 19 confirmed, 1 refuted, 5 lost to verifier rate-limiting — marked below). Companion to `2026-06-12-engagement-layer-recommendations.md`.

---

## Bottom line

**Do not fine-tune now. The skills + prompt-orchestration architecture is the right approach for the POC and Gitex, and the evidence says it remains right until four specific preconditions exist. Fine-tuning is a post-POC strategic option, not a quality lever available today — and when it happens, it goes *inside* the current architecture (responder only), not in place of it.**

Three load-bearing facts from the verified evidence:

1. **The only RCT-validated fine-tuned therapy model (Therabot) cost ~6 years and 100,000+ human hours** of clinician-written, peer-reviewed CBT dialogues — and it still needed a separate crisis classifier, post-transmission clinician review of every response, and 28 staff interventions in a 4-week trial. Fine-tuning did not replace Sage's architecture; it sat inside one.
2. **Cheap fine-tunes on existing counseling corpora do not work.** A 2026 paired comparison across 127 open models found mental-health fine-tuning produced *no* significant improvement over the exact base models on any psychiatrist-reviewed safety task, and several fine-tunes significantly *degraded* performance (ΔF1 −0.17 to −0.19). Backbone generation and scale predicted performance better than any fine-tuning. MentaLLaMA (105K-sample SFT) still significantly underperformed ChatGPT on domain professionality.
3. **The eval harness must come first.** MindEval (clinician-designed multi-turn eval, Nov 2025): all 12 SOTA LLMs score below 4/6; performance degrades with conversation length and symptom severity; and LLM judges systematically overrate responses and miss safety problems human experts catch. Without a human-calibrated multi-turn harness, a fine-tune cannot even be evaluated — you could ship a regression and not know.

## What the verified evidence says, by question

### Clinical outcomes (the pro-fine-tuning case, stated fairly)

- Therabot RCT (NEJM AI 2025, N=210): depression d=0.845–0.903, anxiety d=0.794–0.840, eating-disorder risk d=0.627–0.819 vs waitlist control at 4 and 8 weeks — the strongest clinical evidence for any generative therapy chatbot. [AIoa2400802] (3-0)
- It is genuinely a fine-tune: Falcon-7B + LLaMA-2-70B, QLoRA, on an original corpus written and peer-reviewed by a board-certified psychiatrist and clinical psychologist. NOT prompting over a frontier model. (3-0)
- But: trained on *clinician-authored* dialogues (not scraped transcripts), built since 2019, 100,000+ human hours. (3-0)
- And: every response clinician-reviewed post-transmission; separate crisis guardrail; 15 safety interventions + 13 response corrections in 4 weeks; lead author: "no generative AI agent is ready to operate fully autonomously in mental health." (3-0)

**Reading:** Therabot proves the *ceiling* of fine-tuning with extraordinary data investment. It does not show fine-tuning beats orchestration at any feasible near-term budget, and it independently validates every structural element Sage already has (deterministic crisis layer, clinician review queue, output gating).

### Benchmark head-to-heads (the anti-fine-tuning case)

- 127-model paired comparison (medRxiv 2026): MH-specific fine-tuning → no significant gain on suicidal-ideation / therapy-request / therapy-engagement detection vs exact base models; several fine-tunes significantly worse (Gemma ΔF1 −0.19, LLaMA −0.17). Newer backbone generation had the largest effects (β = 0.52–0.65). Authors: pick a strong modern backbone over fine-tuning a weaker one. (2-0, 1 abstain)
- MentaLLaMA-chat-13B: matches ChatGPT on explanation consistency, approaches discriminative SOTA on 7/10 detection sets — but significantly underperforms ChatGPT on professionality in human eval. Corpus-scale SFT does not transfer frontier-level clinical knowledge into a small model. (3-0 / 2-1)
- CBT-Bench: frontier models *exceed* the human baseline on declarative CBT knowledge (Llama-3.1-405B 95.0%, GPT-4o 94.1% vs human 90.7%) but all models lag human therapists on therapeutic response generation. (3-0 both)

**Reading:** the gap is not knowledge (frontier models have it; Sage's skill templates structure it) — the gap is *in-conversation delivery quality*, which is exactly what the engagement-layer R1–R5 recommendations target at the prompt layer, and what only Therabot-grade data closes at the model layer.

### Multi-turn evaluation (the precondition)

- MindEval (arXiv 2511.18491): clinician-co-designed, fully automated multi-turn eval via patient simulation. All 12 SOTA models < 4/6; weakest on AI-specific failure patterns (sycophancy, overvalidation); scale and reasoning do not guarantee better performance; degradation with length and severity. (3-0)
- CounselBench-style expert eval (arXiv 2506.08584): raw frontier answers frequently flagged for safety, most notably unauthorized medical advice; **LLM judges systematically overrate responses and miss safety concerns human experts catch.** (3-0)

This directly confirms two standing internal positions: the MindEval-style 3-agent harness in the multi-turn test plan, and the requirement that the Judge LLM be calibrated against human raters before gating anything (feedback_test_content_guardrails).

### Safety regressions from fine-tuning — flagged, not fully verified

The Qi et al. 2023 findings (arXiv 2310.03693) — fine-tuning aligned models on *purely benign* data measurably erodes safety alignment (GPT-3.5 harmfulness 5.5%→31.8% after 1 epoch on Alpaca; Llama-2-Chat 0.3%→16.1%), and mixing safety data mitigates but does not restore baseline — were extracted but their verification votes were lost to a rate limit (0-0, all abstain), so they carry **unverified** status in this run. The paper is well-known and widely replicated; treat the direction as reliable, re-verify exact numbers before quoting externally. Implication if it holds: a therapy SFT inherits a safety-maintenance burden (re-alignment, regression suites, re-doing this on every base-model upgrade) that orchestration over an unmodified frontier model avoids entirely.

One claim was actually refuted (1-2): "zero-shot frontier models underperform supervised methods on MH classification" — do not reuse.

### Arabic / Khaleeji

No verified source provides an Arabic therapy fine-tuning corpus or benchmark. This matches the internal finding (multi-turn test plan, 2026-06-05): no Arabic multi-turn public dataset exists. All clinical-outcome evidence above is English-only. A fine-tune today would be trained on data that does not cover half of Sage's target users; the prompt layer (cultural_overrides, Arabic-example-first) is currently the *only* mechanism that does.

## When fine-tuning beats prompt orchestration — preconditions

Fine-tuning becomes the better option only when ALL of the following exist:

1. **A proprietary, clinician-authored/approved dialogue corpus at meaningful scale.** Not public corpora (ESConv/PsyQA-class data demonstrably doesn't move the needle). Sage's clinician review queue + quality log are the natural flywheel: every clinician-approved Sage conversation is future training data. This is an argument for instrumenting and accumulating *now*, training *later*.
2. **A human-calibrated multi-turn eval harness** (MindEval-style patient simulation + judge calibrated against human clinical raters) able to detect regressions in safety, sycophancy, and therapeutic quality. Internal status: planned, not built; CRADLE baseline frozen; judge calibration pending.
3. **A safety regression suite the team trusts.** Current internal numbers (S1 recall 66.7% vs ≥95% KPI; CRADLE S1 37.1%) say the measurement layer itself is still being fixed — per the standing principle, fix measurement before changing production.
4. **Bilingual data parity** — an Arabic/Khaleeji dialogue corpus with clinical sign-off, or an explicit decision to fine-tune English-only and keep Arabic on the prompt path.

When those exist, the evidence-backed shape is the Therabot/Ash hybrid: LoRA-tune the **responder only**, on Sage's own approved dialogues, with safety data blended into the mix; keep the deterministic crisis layer, intent routing, output gate, and clinician review exactly as they are; full model-promotion protocol (recalibrate thresholds, determinism check) on every iteration.

## Recommendation

1. **Keep the current architecture through POC and Gitex.** No fine-tuning work now. The engagement gap is a prompt-layer problem with prompt-layer fixes (R1–R5, already specced).
2. **Start the data flywheel immediately (cheap, high-leverage):** tag clinician-approved conversations in the review queue as "training-eligible," with consent/PDPL review of that designation. This is the single precondition with a long lead time.
3. **Build the eval harness before any training decision** (already planned as MindEval-style 3-agent harness) and calibrate the judge against human raters — this is now triple-confirmed as mandatory (internal feedback + MindEval + CounselBench findings).
4. **Re-decide post-POC** with the preconditions checklist above. If pilot data shows the prompt layer plateauing on delivery quality *and* the corpus + harness exist, a responder-only LoRA inside the existing graph is the evidence-backed path — not a generalist swap, and not training a model from scratch.

## Sources (verified claims drawn from)

- Heinz et al., NEJM AI 2025 (AIoa2400802) + full text — Therabot RCT, architecture, oversight, cost.
- MindEval, arXiv 2511.18491 — multi-turn eval, 12-model results, judge limitations.
- CounselBench-class expert eval, arXiv 2506.08584 — frontier-model safety flags, LLM-judge overrating.
- CBT-Bench, arXiv 2410.13218 — Level I knowledge vs Level III generation gap.
- MentaLLaMA, arXiv 2309.13567 — IMHI SFT results, professionality gap.
- medRxiv 2026.01.02.25343289 — 127-model paired fine-tune comparison, backbone-dominance finding.
- Qi et al., arXiv 2310.03693 — benign fine-tuning safety erosion (UNVERIFIED in this run — rate-limited; re-verify before external use).
- Slingshot Ash sources (STAT News, NEJM AI AIp2500453, Nebius vendor story) were fetched; no Ash claim reached the verified set — treat Ash specifics from the engagement-layer doc as vendor-channel, per its existing flag.
