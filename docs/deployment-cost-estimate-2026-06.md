# Sage POC — Deployment Cost Estimate
**Date:** June 2026  
**Stack:** Next.js (Vercel) · FastAPI/LangGraph + BGE-M3 (Railway) · PostgreSQL + pgvector (Supabase) · OpenAI via OpenRouter  
**Research basis:** 106 agents · 24 sources fetched · 25 claims adversarially verified · models verified against live codebase

---

## Actual Models in Use

> Models confirmed from `src/sage_poc/config.py`, `.env`, and `nodes/skill_select.py`. These are **not assumptions**.

| Role | Model | Where |
|------|-------|--------|
| Response generation | `openai/gpt-4o` | OpenRouter (SAGE_RESPONDER_MODEL) |
| Intent classification | `openai/gpt-4o-mini` | OpenRouter (SAGE_CLASSIFIER_MODEL) |
| Translation (Arabic ↔ English) | `openai/gpt-4o-mini` | OpenRouter (SAGE_TRANSLATOR_MODEL) |
| Semantic skill matching | `BAAI/bge-m3` | **Loaded locally in Railway container** |

**Claude / Anthropic models are PDPL-blocked.** `test_llm_config.py:11` asserts that no default model string contains `"anthropic"` or `"claude"`. This is a data residency compliance constraint, not a configuration preference. The `.env.example` shows `anthropic/claude-sonnet-4-6` as a commented-out alternative — it cannot be used without a policy review.

**BGE-M3 is always in-memory on Railway.** `SAGE_WARMUP_BGE=1` is the default. The model loads at server startup and stays warm. Actual measured RAM footprint on Railway Linux (float16) is ~1.05 GB for the model, ~1.16 GB total service.

---

## OpenRouter Pricing (verified June 2026)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|-----------------------|------------------------|
| `openai/gpt-4o` | **$2.50** | **$10.00** |
| `openai/gpt-4o-mini` | **$0.15** | **$0.60** |
| `BAAI/bge-m3` | n/a — runs locally | n/a |

Sources: [openrouter.ai/openai/gpt-4o](https://openrouter.ai/openai/gpt-4o) · [openrouter.ai/openai/gpt-4o-mini](https://openrouter.ai/openai/gpt-4o-mini)

---

## Summary

| Tier | Users | Monthly Range | Main driver |
|------|-------|---------------|-------------|
| POC | 20 | **$85 – $120** | Infra base + moderate gpt-4o usage |
| Pilot | 100 | **$165 – $335** | gpt-4o responder scales linearly |
| Growth | 500 | **$565 – $1,415** | gpt-4o output tokens dominate |

**Infrastructure base is $65/month** (Vercel $20 + Railway $20 + Supabase $25). BGE-M3 runs at ~1.16 GB actual RAM on Railway Linux (float16), keeping compute within the $20 Pro credit.

---

## Service-by-Service Breakdown

### 1. Vercel (Frontend — Next.js)

**Recommended plan: Pro ($20/month)**

| Item | Hobby (Free) | Pro ($20/month) |
|------|-------------|----------------|
| Bandwidth | 100 GB/month | 1 TB/month |
| Edge Requests | 1 M/month | 10 M/month |
| Function max duration | 300 s | 800 s (Fluid Compute) |
| Overage: bandwidth | — (pauses) | $0.15/GB |
| SLA | None | 99.99% |
| Additional deploying seats | — | $20/seat |

Hobby is unsuitable for any client-facing deployment — projects pause on quota hit, no SLA. At 20–500 users, bandwidth stays well under 1 TB. Heavy compute runs on Railway; Vercel only serves the Next.js shell.

**Vercel estimate:**

| Tier | Users | Cost |
|------|-------|------|
| POC | 20 | **$20** |
| Pilot | 100 | **$20** |
| Growth | 500 | **$20** |

---

### 2. Railway (Backend — FastAPI + LangGraph + BGE-M3)

**Recommended plan: Pro ($20/month)**  
The $20/month subscription acts as a resource credit. Actual compute is billed on top.

| Resource | Rate |
|----------|------|
| RAM | $10/GB/month |
| CPU | $20/vCPU/month |
| Egress | $0.05/GB |

**Actual RAM usage — measured from live Railway metrics (2026-06-01):**

| Component | Actual RSS |
|-----------|-----------|
| BGE-M3 (sentence_transformers loads float16 on PyTorch 2+, not float32) | ~1.05 GB |
| FastAPI + LangGraph + asyncpg pool + OS | ~0.11 GB |
| **Measured steady-state total** | **~1.16 GB** |

The earlier estimate of ~3 GB assumed float32 model weights. In practice, sentence_transformers defaults to float16 on Railway's Linux/PyTorch environment, halving the footprint. Measured directly from the production service's MEMORY_USAGE_GB metric.

At 1.16 GB × $10/GB = **$11.60/month RAM**.  
CPU at idle is ~0.002 vCPU; per-request spikes (BGE-M3 inference + LLM call) last 1–2 minutes each and add ~$0.30–1.50/month at current traffic.  
Total compute: **~$12–13/month — fully within the $20 Pro credit.**

**Railway estimate:**

| Tier | Users | Measured RAM | Compute cost | Pro credit | **Bill** |
|------|-------|-------------|-------------|-----------|---------|
| POC | 20 | ~1.16 GB | ~$12 | −$20 (covers all) | **$20** |
| Pilot | 100 | ~1.16 GB | ~$13 | −$20 (covers all) | **$20** |
| Growth | 500 | ~1.2–1.5 GB | ~$15–20 | −$20 | **$20** |

> **Caveat — Railway "per seat" vs per-account:** Docs describe per-account billing, but marketing says "per seat." For a shared account with 2–3 developers, confirm at Railway → Account → Billing before provisioning.

---

### 3. Supabase (PostgreSQL + pgvector + Auth + Realtime)

**Recommended plan: Pro ($25/month)**

| Feature | Free | Pro ($25/month) |
|---------|------|----------------|
| Database disk | 500 MB | 8 GB |
| Monthly Active Users | 50,000 | 100,000 |
| Egress | 5 GB | 250 GB |
| pgvector | ✅ included | ✅ included |
| Realtime (clinician dashboard) | ✅ included | ✅ included |
| Project pausing | After 1 week idle | Never |
| Overage: disk | — | $0.125/GB |
| Overage: MAUs | — | $0.00325/MAU |

Free tier pauses after 1 week inactivity — unsuitable for any demo or production use. All three scale tiers fit comfortably within Pro limits.

| Resource | 20 users | 100 users | 500 users | Pro limit |
|----------|---------|----------|----------|-----------|
| pgvector (10K skill embeddings) | ~30 MB | ~30 MB | ~30 MB | 8 GB ✅ |
| Conversation history (DB rows) | ~5 MB | ~25 MB | ~120 MB | 8 GB ✅ |
| MAUs | 20 | 100 | 500 | 100,000 ✅ |

**Supabase estimate:**

| Tier | Users | Cost |
|------|-------|------|
| POC | 20 | **$25** |
| Pilot | 100 | **$25** |
| Growth | 500 | **$25–35** |

---

### 4. OpenRouter — GPT-4o + GPT-4o-mini

Every user turn passes through **two model calls**:

1. **gpt-4o-mini** (classifier) — classifies intent; short prompt + short output
2. **gpt-4o** (responder) — generates the full response; growing context window as the conversation progresses

Arabic turns also incur a third call:

3. **gpt-4o-mini** (translator) — approximately 50% of turns in a bilingual deployment

**Token assumptions per turn:**

| Call | Input tokens | Output tokens | Notes |
|------|-------------|--------------|-------|
| gpt-4o-mini classifier | 300 | 50 | Short system prompt + user message |
| gpt-4o responder | 1,000 avg | 400 | Grows with conversation history (AsyncPostgresSaver loads prior turns) |
| gpt-4o-mini translator (50% of turns) | 200 | 200 | Arabic ↔ English |

**Cost per turn:**

| Call | Input cost | Output cost | Subtotal |
|------|-----------|------------|---------|
| gpt-4o-mini classifier | 300 × $0.00000015 = $0.000045 | 50 × $0.0000006 = $0.000030 | $0.000075 |
| gpt-4o responder | 1,000 × $0.0000025 = $0.002500 | 400 × $0.00001 = $0.004000 | $0.006500 |
| gpt-4o-mini translator (×0.5) | 200 × $0.00000015 × 0.5 = $0.000015 | 200 × $0.0000006 × 0.5 = $0.000060 | $0.000075 |
| **Total per turn** | | | **~$0.00665** |

The gpt-4o responder output cost ($0.004/turn) accounts for **60% of total LLM spend**. The classifier and translator are negligible by comparison.

**Monthly LLM costs (10 sessions/user/day, 10 turns/session):**

| Tier | Users | Turns/day | LLM cost/day | **LLM/month** |
|------|-------|-----------|-------------|--------------|
| POC | 20 | 200 | $1.33 | **~$40** |
| Pilot | 100 | 1,000 | $6.65 | **~$200** |
| Growth | 500 | 5,000 | $33.25 | **~$998** |

> **Floor scenario** (5 turns/session, lighter usage): halve the above figures.  
> **Ceiling scenario** (longer context — turns 8–10 in a session carry 3,000+ input tokens): add ~30–40% to gpt-4o input costs.

---

## Monthly Budget Summary

### Infrastructure Base (fixed at all tiers)

| Service | Monthly | Notes |
|---------|---------|-------|
| Vercel Pro | $20 | 1 deploying seat |
| Railway Pro | $20 | ~1.16 GB actual RAM, within Pro credit |
| Supabase Pro | $25 | pgvector + Realtime included |
| **Total infra** | **$65** | |

### Total Monthly Budget

| Tier | Users | Infra | LLM (typical) | LLM (floor) | LLM (ceiling) | **Total (typical)** | **Total (floor)** | **Total (ceiling)** |
|------|-------|-------|---------------|------------|--------------|---------------------|-------------------|---------------------|
| POC | 20 | $65 | $40 | $20 | $55 | **~$105** | **~$85** | **~$120** |
| Pilot | 100 | $65 | $200 | $100 | $270 | **~$265** | **~$165** | **~$335** |
| Growth | 500 | $65 | $998 | $500 | $1,350 | **~$1,063** | **~$565** | **~$1,415** |

> **Recommended budget targets:**
> - POC: **$120/month** (comfortable buffer for onboarding spike)
> - Pilot: **$300/month** (allows 100 users at above-typical engagement)
> - Growth: **$1,200/month** (review at 300 users; gpt-4o output is the lever)

---

## Cost Levers

Unlike the previous draft (which assumed a Haiku/Sonnet split), Sage currently uses **one model for all responses (gpt-4o)** with no routing. The levers available are:

| Lever | Impact | Trade-off |
|-------|--------|-----------|
| Switch responder to gpt-4o-mini | ~10× cheaper output | Significant quality drop for complex/crisis turns |
| Introduce routing (gpt-4o-mini for simple turns) | ~50–70% cost reduction | Requires routing logic in LangGraph; test coverage needed |
| Reduce context window (summarise earlier) | Cuts gpt-4o input cost by 30–50% | LangGraph summarisation node adds latency |
| Reduce turns/session (session timeout) | Linear reduction | UX impact |
| Rate-limit heavy users | Caps ceiling | Product decision |

At growth (500 users), adding even a simple routing rule (gpt-4o-mini for greetings and simple Q&A, gpt-4o for skills + crisis) could reduce the LLM bill from ~$1,000 to ~$400–500/month.

---

## Free Tier Limits to Watch

| Service | Limit | Risk |
|---------|-------|------|
| Supabase Free: 500 MB disk | Hit with ~200K stored conversation turns | Use Pro from day 1 |
| Supabase Free: pauses after 1 week idle | Kills POC demo reliability | Use Pro from day 1 |
| Railway Pro: $20 compute credit | Measured compute ~$12/month — within credit at all tiers | No overage risk at current scale |
| Vercel Hobby: projects pause on traffic | Any production use | Use Pro |

---

## Recommended Launch Configuration

| Service | Plan | Monthly | Action |
|---------|------|---------|--------|
| Vercel | Pro (1 seat) | $20 | New account, Pro from day 1 |
| Railway | Pro (1 account) | $20 | Default config; ~1.16 GB RAM stays within credit |
| Supabase | Pro | $25 | New project, Pro from day 1; never Free in prod |
| OpenRouter | Pay-as-you-go | ~$40–200 | Set **$80/month spend alert** for POC |
| **Total** | | **$105–265/month** | POC through pilot |

Set a spend alert in OpenRouter at **$80/month** for the POC phase. The gpt-4o output rate ($10/M tokens) can surprise — a single misconfigured loop or runaway LangGraph node can burn $20–30 in minutes.

---

## Notes on Claude / Anthropic Models

The `.env.example` lists `SAGE_RESPONDER_MODEL=anthropic/claude-sonnet-4-6` as a commented alternative. This cannot be used in the current build without:

1. Removing or updating the PDPL compliance assertion in `test_llm_config.py:11`
2. A policy decision confirming that routing user data through Anthropic's API is permissible under UAE PDPL data residency requirements

If the PDPL constraint is lifted, switching to Claude Sonnet 4.6 ($3.00/M input, $15.00/M output) would **increase costs** vs. the current gpt-4o ($2.50/$10.00). Haiku 4.5 ($1.00/$5.00) would be cheaper — but only if a routing layer is introduced. Neither change should be made without a policy review first.

---

*Infrastructure prices: vercel.com/pricing · docs.railway.com/pricing/plans · supabase.com/pricing*  
*Model prices: openrouter.ai/openai/gpt-4o · openrouter.ai/openai/gpt-4o-mini*  
*Model sources: sage-poc/src/sage_poc/config.py · sage-poc/nodes/skill_select.py · sage-poc/tests/test_llm_config.py*
