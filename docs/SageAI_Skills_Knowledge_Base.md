# SageAI Skills & Knowledge Base Inventory

**Classification:** Confidential — Sage Internal  
**Version:** 1.2 | **Date:** 2026-06-01  
**Status:** Living document — update on each sprint completion  
**Owner:** Clinical Lead + Engineering Lead (joint approval required for additions)  

> **Purpose:** Canonical inventory of all structured skills in the SageAI system, their status, evidence base, and CMS workflow position. Referenced by `SKILL_REGISTRY` in `skill_ids.py` and the `SageAI_Skills_Knowledge_Base.docx` cited in v7 §9.1.  
> Skills may not be added to `SKILL_REGISTRY` without an entry in this document at status ≥ **Clinically Approved**.

---

## Status Definitions

| Status | Meaning | Gate to next |
|--------|---------|-------------|
| **Implemented** | In `SKILL_REGISTRY`, schema-valid, clinician-reviewed, in production | N/A |
| **Clinically Approved** | Schema complete, clinician signed off, pending registration | Engineering merge + calibration |
| **Draft — Clinical Review** | JSON authored, awaiting clinical sign-off | Dual-clinician approval (§6.3) |
| **Proposed** | Identified as needed, not yet authored | Inventory approval + authoring |

---

## Skill Inventory

### Tier 1 — Implemented (24 skills)

*All implemented skills are in `SKILL_REGISTRY` (`src/sage_poc/skill_ids.py`). JSON files in `src/sage_poc/skills/`. Schema-valid against the Pydantic `Skill` model. All 24 skills clinician-reviewed and approved for production.*

| # | Skill ID | Skill Name | Technique Family | Evidence Base | Sprint Introduced | Cluster |
|---|----------|-----------|-----------------|--------------|------------------|---------|
| SK-001 | `cbt_thought_record` | CBT Thought Record | Cognitive Behavioural Therapy | Beck (1979); Burns (1980) | Sprint 1 | ruminative_anxiety |
| SK-002 | `grounding_5_4_3_2_1` | 5-4-3-2-1 Grounding | Sensory grounding / DBT | Najavits (2002) | Sprint 1 | somatic_distress |
| SK-003 | `sleep_hygiene` | Sleep Hygiene Psychoeducation | Behavioural sleep medicine | Harvey (2002) | Sprint 1 | sleep |
| SK-004 | `post_crisis_check_in` | Post-Crisis Safety Check-In | Crisis intervention | ASIST (2018); SAMHSA Safe Messaging (2023) | Sprint 1 | (auto-select only) |
| SK-005 | `box_breathing` | Box Breathing | Respiratory regulation / ANS reset | Jerath et al. (2006) | Sprint 1 | somatic_distress |
| SK-006 | `mood_check_in` | Mood & Wellbeing Check-In | Monitoring / psychometric | PHQ-2 derivative; Kroenke & Spitzer (2002) | Sprint 2 | mood_engagement |
| SK-007 | `behavioral_activation` | Behavioural Activation | BA for depression | Lewinsohn (1974); Martell et al. (2001) | Sprint 2 | mood_engagement |
| SK-008 | `worry_time` | Worry Time | Cognitive worry containment | Borkovec et al. (1983) | Sprint 2 | ruminative_anxiety |
| SK-009 | `mi_readiness_ruler` | MI Readiness Ruler | Motivational Interviewing | Miller & Rollnick (2012) | Sprint 2 | readiness_ambivalence |
| SK-010 | `stop_technique` | STOP Mindfulness Technique | MBSR | Williams et al. (2007); Kabat-Zinn (1990) | Sprint 2 | impulse_pause |
| SK-011 | `progressive_muscle_relaxation` | Progressive Muscle Relaxation | Somatic relaxation | Jacobson (1938); Bernstein & Borkovec (1973) | Sprint 3 | somatic_distress |
| SK-012 | `safe_place_visualization` | Safe Place Visualisation | Imagery rescripting / stabilisation | Hackmann et al. (2011); EMDR precursor | Sprint 3 | visualization |
| SK-013 | `dbt_tipp` | DBT TIPP Skills | Dialectical Behaviour Therapy | Linehan (1993); Linehan (2015) | Track 1 / Sprint 4 | somatic_distress |
| SK-014 | `psychoed_anxiety` | Anxiety Psychoeducation | CBT psychoeducation | Beck (1985); Clark (1986); NICE CG113 | V7 Sprint | psychoeducation |
| SK-015 | `psychoed_depression` | Depression Psychoeducation | CBT psychoeducation | APA DSM-5-TR; Gotlib & Hammen (2002); NICE CG90 | V7 Sprint | psychoeducation |
| SK-016 | `psychoed_stress` | Stress Psychoeducation | CBT psychoeducation | Selye (1956); Lazarus & Folkman (1984) | V7 Sprint | psychoeducation |
| SK-017 | `values_clarification` | ACT Values Clarification | Acceptance & Commitment Therapy | Hayes et al. (1999); Wilson & Murrell (2004) | V7 Sprint | values_communication |
| SK-018 | `assertive_communication` | Assertive Communication | Assertiveness training | Wolpe (1990); Alberti & Emmons (2008) | V7 Sprint | values_communication |
| SK-019 | `self_compassion_break` | Self-Compassion Break | MSC / Neff self-compassion | Neff (2011); Germer (2009) | V7 Sprint | self_compassion |
| SK-020 | `mindfulness_body_scan` | Mindfulness Body Scan | MBSR / MBCT | Kabat-Zinn (1990); Williams et al. (2007) | V7 Sprint | somatic_distress |
| SK-021 | `cognitive_restructuring` | Cognitive Restructuring | CBT / thought challenging | Beck (1979); Burns (1980); Clark & Beck (2010); NICE CG91 | Phase 2 (2026-05-31) | ruminative_anxiety |
| SK-022 | `interpersonal_effectiveness` | Interpersonal Effectiveness | DBT / DEAR MAN / GIVE / FAST | Linehan (1993); Linehan (2015) | Phase 2 (2026-05-31) | values_communication |
| SK-023 | `financial_anxiety` | Financial Anxiety (Gulf Context) | Psychoeducation + CBT applied to financial stress | Shapiro (2007); Gulf labour market research; kafala / provider role literature | Phase 2 (2026-05-31) | financial_stress |
| SK-024 | `grief_loss` | Grief and Loss Support | Grief counselling / continuing bonds | Worden (1991); Klass et al. (1996); Islamic grief framework (Al-Ghazali) | Phase 2 (2026-05-31) | grief_and_loss |

---

### Tier 3 — Proposed Future Skills (4 skills — Status: Proposed)

*Identified to reach the 28-skill target. Not yet authored. Require clinical scoping and evidence-base definition before authoring begins. Do not add to `SKILL_REGISTRY` without this document showing status ≥ Clinically Approved.*

| # | Skill ID (proposed) | Skill Name | Technique Family | Rationale | Priority |
|---|---------------------|-----------|-----------------|-----------|---------|
| SK-025 | `emotion_regulation` | Emotion Regulation | DBT Emotion Regulation module | Closes gap between TIPP (crisis-level) and general emotion skills; Linehan (2015) | High |
| SK-026 | `thought_defusion` | Cognitive Defusion | ACT defusion | Complements `cognitive_restructuring` with acceptance-based alternative; Hayes et al. (2012) | Medium |
| SK-027 | `behavioural_experiment` | Behavioural Experiment | CBT behavioural testing | Closes CBT spectrum: thought record → restructuring → experiment; Bennett-Levy et al. (2004) | Medium |
| SK-028 | `problem_solving` | Structured Problem Solving | CBT problem-solving therapy | Addresses functional impairment from depression/anxiety; D'Zurilla & Nezu (2010) | High |

---

## Knowledge Base Article Inventory

### English Corpus — 30 articles (Implemented)

Located in `data/knowledge_corpus/en/`. All 30 articles are schema-valid and ingested. 4 crisis articles are flagged; Arabic pairs for these require dual-clinician sign-off before they can be authored or ingested.

| Article ID | Title | Crisis Content | Clinical Gate |
|-----------|-------|---------------|---------------|
| anxiety-001 | What is anxiety? | | |
| anxiety-002 | Anxiety — physical symptoms | | |
| anxiety-003 | Managing anxiety | | |
| assertiveness-001 | Assertiveness | | |
| breathing-001 | Breathing techniques | | Deferred AR pair — covered by `box_breathing` skill |
| cbt-001 | CBT overview | | Deferred AR pair — covered by psychoed skills |
| cbt-002 | CBT techniques | | Deferred AR pair — covered by psychoed skills |
| coping-001 | Healthy coping strategies | | |
| coping-002 | Coping with stress | | |
| **crisis-001** | What to do in a mental health crisis | **Yes** | **AR pair: dual-clinician sign-off required** |
| **crisis-002** | Suicidal ideation support | **Yes** | **AR pair: dual-clinician sign-off required** |
| **crisis-003** | Self-harm | **Yes** | **AR pair: dual-clinician sign-off required** |
| **crisis-004** | Crisis de-escalation | **Yes** | **AR pair: dual-clinician sign-off required** |
| depression-001 | What is depression? | | |
| depression-002 | Causes of depression | | |
| depression-003 | Depression recovery | | |
| grief-001 | Grief and loss | | |
| grounding-001 | Grounding techniques | | Deferred AR pair — covered by `grounding_5_4_3_2_1` skill |
| gulf-001 | Mental health in Gulf Arab culture | | |
| mindfulness-001 | Mindfulness | | |
| relationships-001 | Relationships and mental health | | |
| relationships-002 | Relationship conflict | | |
| self-compassion-001 | Self-compassion | | |
| sleep-001 | Sleep and mental health | | |
| stress-001 | What is stress? | | |
| stress-002 | Stress management | | |
| therapy-001 | Types of therapy | | Deferred AR pair — lower priority, no paired skill |
| trauma-001 | Trauma and PTSD | | Deferred AR pair |
| values-001 | Values and priorities | | |
| wellbeing-001 | Psychological wellbeing | | |

### Arabic Corpus — 20 articles (Implemented — approved 2026-06-01)

Located in `data/knowledge_corpus/ar/`. All 20 articles authored in Khaleeji Gulf Arabic dialect, schema-valid, 200–290 words each, properly cited. Approved for production ingest 2026-06-01. **Pending operational step: run `scripts/ingest_knowledge.py` against `data/knowledge_corpus/ar/` to load into the `knowledge_articles` pgvector table.**

| Article ID | Arabic Title | Words | Clinical Note |
|-----------|-------------|-------|---------------|
| anxiety-001 | ما هو القلق؟ | 272 | |
| anxiety-002 | القلق والأعراض الجسدية | 247 | |
| anxiety-003 | كيف تتعامل مع القلق | 254 | |
| assertiveness-001 | ما هي الحزم والتعبير عن النفس؟ | 224 | |
| coping-001 | استراتيجيات التكيف الصحية | 238 | |
| coping-002 | التكيف مع الضغط النفسي | 228 | |
| depression-001 | ما هو الاكتئاب؟ | 217 | |
| depression-002 | أسباب الاكتئاب | 230 | Biological model — faith framing reviewed and approved |
| depression-003 | التعافي من الاكتئاب | 242 | Recovery framing — faith-consistent language reviewed and approved |
| grief-001 | الحزن والفقد | 289 | Islamic grief framework (عزاء, صبر, رحمة) — reviewed and approved |
| gulf-001 | الصحة النفسية في الثقافة الخليجية | 269 | |
| mindfulness-001 | اليقظة الذهنية | 233 | |
| relationships-001 | العلاقات والصحة النفسية | 213 | |
| relationships-002 | التعامل مع الصراعات في العلاقات | 213 | |
| self-compassion-001 | الرحمة بالنفس | 221 | |
| sleep-001 | النوم والصحة النفسية | 227 | |
| stress-001 | ما هو التوتر؟ | 203 | |
| stress-002 | إدارة التوتر | 229 | |
| values-001 | القيم والأولويات | 220 | |
| wellbeing-001 | الرفاهية النفسية | 222 | |

**Deferred Arabic pairs (6):** breathing-001, cbt-001, cbt-002, grounding-001, therapy-001, trauma-001 — rationale documented in `src/sage_poc/corpus_constants.py`.

**Crisis Arabic pairs (4) — NOT authored, NOT ingested:** crisis-001, crisis-002, crisis-003, crisis-004 require dual-clinician sign-off before Arabic versions may be written or ingested. This gate is independent of the 2026-06-01 general approval.

---

## Amendment Log

| Date | Change | Approved by |
|------|--------|------------|
| 2026-05-31 | Created document from project records; confirmed SK-001–SK-020 (Implemented); added SK-021–SK-024 as Phase 2 inventory items (Draft — Clinical Review); identified SK-025–SK-028 as Tier 3 Proposed | Engineering Lead |
| 2026-06-01 | **Clinical approval received.** SK-021–SK-024 promoted to **Implemented** — `cognitive_restructuring`, `interpersonal_effectiveness`, `financial_anxiety`, `grief_loss` cleared for production. Arabic corpus (20 articles) confirmed as fully authored Khaleeji Gulf Arabic content — status updated from draft to Implemented. depression-002, depression-003, grief-001 Arabic articles reviewed and approved for production ingest. Pending operational: run `ingest_knowledge.py` on AR corpus. | Clinical Lead + Engineering Lead |
