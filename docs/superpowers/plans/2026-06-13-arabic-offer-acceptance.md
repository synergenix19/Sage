# Arabic Offer Acceptance (S2-2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the consent gate work for Khaleeji Arabic users: live accept/decline classification on Khaleeji replies, Arabic display names echoed verbatim into classification, defense-in-depth choice resolution, and the clinical handoff that unlocks authored Arabic blurbs as a pure data drop.

**Why (audit evidence, 2026-06-13 PR #4 audit, finding S2-2 — launch-blocking for Arabic):** live runs showed bare "ايه" and positional "ابي الثاني" both classified `offer_ignored` (not promoted), with the responder mistranslating "ابي" as "my father" ("شنو تقصد بأبوك الثاني؟"). Root causes: (1) the classifier sees only `message_en` — the Arabic→English translation is where "ابي الثاني" degrades; (2) the PENDING OFFER block grounds choices in English display names/ids only; (3) no Khaleeji accept exemplars in the block; (4) `ar` blurb values are all null, so nothing Arabic exists to echo. The audit's chained finding: a missed accept led to ungoverned freeflow exercise delivery — every missed Arabic accept is a consent-gate bypass risk, not just lost UX.

**Architecture:** All changes ride the per-turn PENDING OFFER block in `build_intent_prompt` (INTENT_SYSTEM stays byte-identical — the bare-emotional-words SPOF guard binds every task here), the `_resolve_offer_choice`/`_offer_display_map` helpers, and `offer_descriptions.json` data. The live-classifier Arabic tests become the S2-2 exposure gate. Blurb authoring is handed to clinical as a work order; the bilingual envelope (ar null → en fallback) means authored content activates with zero code changes.

**PIPELINE DEVIATION (v7 §3) — declared and bounded:** v7's language pipeline is detect → translate → process: every node downstream of safety_check consumes `message_en`, never raw Arabic. This plan deviates: Node 2's classifier prompt additionally receives the raw Khaleeji text. The deviation is the fix — the audit proved the loss happens IN the translation step ("ابي الثاني" → "my father the second"), so any downstream-of-translation repair is repairing a corrupted signal.
- **Bound:** the raw-Arabic line is injected ONLY when `offered_skill_ids` is pending AND `detected_language == "ar"` — offer-classification turns in Arabic sessions, nothing else. All other turns, and all other consumers (skill matching, criteria eval, safety rules beyond their existing text_ar paths), continue to consume `message_en` exclusively. INTENT_SYSTEM is not modified.
- **Eval-set implication (and the task that discharges it):** Node 2 now consumes Khaleeji-bearing prompts, so the intent-classification guard family must include Khaleeji-bearing cases — not just the new offer tests. Task 3 adds a live Khaleeji bare-emotional-word guard (the Arabic analogue of the `bare_emotional_words` SPOF guard) asserting that a bare Khaleeji emotional statement with an offer pending still classifies `general_chat` and is never read as an accept. If the deviation is ever widened beyond offer turns, the full bare-emotional-words guard set needs Khaleeji variants first — recorded here as the widening precondition.
- **Arabizi bound (declared, not silent):** Arabizi is detected as `"en"` by the current language pipeline (arch doc §6.4 named decision; the detect→"az" plan is unimplemented), so `detected_language == "ar"` structurally excludes Arabizi from this deviation — an Arabizi "abi el thani" gets neither the raw-Arabic line nor the Khaleeji exemplar benefit. This is the declared bound, not an oversight; Arabizi offer-acceptance joins the existing Arabizi work plan (2026-06-08), not this one.
- **Sign-off:** this deviation is a control-layer change on Node 2 (Rule 1) and an architecture-doc change (§3 + §5.2); both flagged in Task 5.

**Branch:** `feat/arabic-offer-acceptance` stacked on `feat/engagement-r1-r3-r5` (this work depends on its code). Rebase onto master after PR #4 merges; do not merge before PR #4.

**Tech Stack:** Python 3.12, pytest via `uv run pytest`; live-classifier tests are `@pytest.mark.slow` (real LLM). Working dir: `/Users/knowledgebase/Documents/Sage/sage-poc`.

**Governance:** prompt-block changes are control-layer (Rule 1); the Khaleeji exemplar strings and the blurb work-order content need clinical review. No em dashes in any prompt-bound string.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/sage_poc/nodes/intent_route.py` | Modify | raw-Arabic context line, language-aware display map, Khaleeji exemplars + "ابي" disambiguation, ordinal-tolerant resolution |
| `tests/test_intent_route_node.py` | Modify | structure tests (mocked) for the new block content + resolution |
| `tests/test_arabic_offer_live.py` | Create | live-classifier Khaleeji contract (slow; the S2-2 exposure gate) |
| `tests/test_engagement_templates.py` | Modify | composer echoes ar display names when present (monkeypatched blurbs) |
| `docs/work-orders/arabic-offer-blurbs.md` | Create | clinical handoff package for the 25 ar blurb pairs |

---

### Task 0: Branch

- [ ] **Step 1:**
```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git checkout feat/engagement-r1-r3-r5 && git pull && git checkout -b feat/arabic-offer-acceptance
```
- [ ] **Step 2:** Baseline: `uv run pytest tests/test_intent_route_node.py tests/test_engagement_templates.py -q -m "not slow" 2>&1 | tail -2` — green.

---

### Task 1: Classifier sees the raw Arabic + Khaleeji grounding in the PENDING OFFER block

**Files:** Modify `src/sage_poc/nodes/intent_route.py`; test `tests/test_intent_route_node.py`. INTENT_SYSTEM untouched.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_intent_route_node.py`):

```python
# ── S2-2: Arabic offer-classification grounding ──────────────────────────────

def test_pending_offer_block_includes_raw_arabic_for_ar_sessions():
    from sage_poc.nodes.intent_route import build_intent_prompt
    state = _base_state(message_en="my father the second", detected_language="ar", **_OFFER_STATE_KW)
    state["raw_message"] = "ابي الثاني"
    prompt = build_intent_prompt(state)
    assert "ابي الثاني" in prompt, (
        "ar sessions must expose the raw Arabic to the classifier; the EN translation "
        "is where Khaleeji accepts degrade (audit S2-2: 'ابي' became 'my father')"
    )
    assert "original Arabic" in prompt


def test_pending_offer_block_omits_raw_arabic_for_en_sessions():
    from sage_poc.nodes.intent_route import build_intent_prompt
    prompt = build_intent_prompt(_base_state(message_en="yes", **_OFFER_STATE_KW))
    assert "original Arabic" not in prompt


def test_pending_offer_block_carries_khaleeji_accept_exemplars():
    from sage_poc.nodes.intent_route import build_intent_prompt
    state = _base_state(message_en="yes", detected_language="ar", **_OFFER_STATE_KW)
    state["raw_message"] = "ايه"
    prompt = build_intent_prompt(state)
    for exemplar in ("ايه", "يلا", "اوكي"):
        assert exemplar in prompt, f"Khaleeji accept exemplar {exemplar!r} missing"
    assert "I want" in prompt, (
        "the block must disambiguate Khaleeji 'ابي' (I want) from MSA 'أبي' (my father)"
    )


def test_offer_display_map_uses_arabic_names_when_present(monkeypatch):
    import sage_poc.nodes.intent_route as ir
    fake_descs = {
        "box_breathing": {"display_name": {"en": "Box breathing", "ar": "تنفس الصندوق"},
                          "description": {"en": "x", "ar": None}},
        "grounding_5_4_3_2_1": {"display_name": {"en": "5-4-3-2-1 grounding", "ar": None},
                                 "description": {"en": "y", "ar": None}},
    }
    monkeypatch.setattr("sage_poc.prompts.composer._offer_descriptions", lambda: fake_descs)
    mapped = ir._offer_display_map(["box_breathing", "grounding_5_4_3_2_1"], language="ar")
    assert "تنفس الصندوق" in mapped, "authored ar display name must be echoed verbatim"
    assert "5-4-3-2-1 grounding" in mapped, "null ar falls back to en"
    assert "box_breathing" in mapped and "grounding_5_4_3_2_1" in mapped, "ids stay as the return contract"
```

- [ ] **Step 2:** Run `uv run pytest tests/test_intent_route_node.py -k "raw_arabic or khaleeji or display_map_uses_arabic" -v` — expect 4 FAIL (TypeError on the new `language` kwarg; missing strings).

- [ ] **Step 3: Implement** in `src/sage_poc/nodes/intent_route.py`:

(a) `_offer_display_map` gains a `language: str = "en"` parameter and echoes the session-language display name with en fallback (the map's RIGHT side — the id to return — never changes):

```python
def _offer_display_map(offered: list[str], language: str = "en") -> str:
    """'1. "<display name the user saw>" = skill_id, ...' — grounds the classifier to
    return ids. For ar sessions the user saw the ar display name (when authored), so
    that exact string is echoed; null ar falls back to en (bilingual envelope)."""
    try:
        from sage_poc.prompts.composer import _offer_descriptions
        descs = _offer_descriptions()
    except Exception:
        descs = {}
    parts = []
    for i, sid in enumerate(offered, 1):
        entry = descs.get(sid)
        if entry:
            name = entry["display_name"].get(language) or entry["display_name"].get("en") or sid
            parts.append(f'{i}. "{name}" = {sid}')
        else:
            parts.append(f"{i}. {sid}")
    return ", ".join(parts)
```

(b) In `build_intent_prompt`, inside the `if offered:` block: compute `language = state.get("detected_language") or "en"`, pass it to `_offer_display_map(offered, language=language)`, and extend the block. Replace the current bare-agreement + ordinal sentences with:

```python
            'A short bare agreement ("yes", "ok", "sure", "yalla") is accept; Khaleeji '
            'equivalents ("ايه", "يلا", "اوكي", "تمام", "خلنا نجرب") are accept. '
            'In Khaleeji Arabic "ابي" means "I want" (a choice signal), NOT "my father". '
            'References like "the first one", "the second one", and Arabic ordinals '
            '("الاول", "الثاني") map to the options by position. '
            "All other classification rules are unchanged; classify primary_intent as usual."
```

and append, only when `language == "ar"` and `state.get("raw_message")`:

```python
        offer_block += (
            f"\nUser message (original Arabic): {state['raw_message']}\n"
            "Classify the offer_response from the original Arabic when it conflicts "
            "with the English translation."
        )
```

- [ ] **Step 4:** `uv run pytest tests/test_intent_route_node.py -q` — ALL pass (the pre-existing offer tests must stay green; the EN block text changes only in the listed sentences, so check any test pinning the old sentence text and update it if the assertion targeted replaced wording — report which).

- [ ] **Step 5: Commit:** `git add src/sage_poc/nodes/intent_route.py tests/test_intent_route_node.py && git commit -m "feat(S2-2): raw-Arabic context, Khaleeji accept exemplars, ar display-name grounding in PENDING OFFER block"`

---

### Task 2: Ordinal-tolerant choice resolution (defense in depth)

**Files:** Modify `src/sage_poc/nodes/intent_route.py`; test `tests/test_intent_route_node.py`.

- [ ] **Step 1: Failing tests:**

```python
@pytest.mark.asyncio
async def test_arabic_ordinal_echo_resolves_positionally():
    from sage_poc.nodes.intent_route import intent_route_node
    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.5, "emotional_intensity": 4, "engagement": 5, '
        '"offer_response": "accept", "offer_choice_skill_id": "الثاني"}'
    )
    state = _base_state(message_en="the second", detected_language="ar", **_OFFER_STATE_KW)
    state["raw_message"] = "ابي الثاني"
    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)
    assert result["offer_choice_skill_id"] == "grounding_5_4_3_2_1"


def test_resolve_offer_choice_handles_arabic_ordinal_words():
    from sage_poc.nodes.intent_route import _resolve_offer_choice
    offered = ["box_breathing", "grounding_5_4_3_2_1"]
    assert _resolve_offer_choice("الاول", offered) == "box_breathing"
    assert _resolve_offer_choice("الأول", offered) == "box_breathing"   # hamza variant
    assert _resolve_offer_choice("الثاني", offered) == "grounding_5_4_3_2_1"
    assert _resolve_offer_choice("first", offered) == "box_breathing"
    assert _resolve_offer_choice("second", offered) == "grounding_5_4_3_2_1"
```

- [ ] **Step 2:** Run; expect FAIL (falls back to offered[0] today).

- [ ] **Step 3: Implement** — in `_resolve_offer_choice`, after the digit-index branch, add an ordinal-word branch BEFORE the display-name branch:

```python
    _ORDINAL_WORDS = {
        "first": 1, "second": 2,
        # masculine
        "الاول": 1, "الأول": 1, "اول": 1, "أول": 1,
        "الثاني": 2, "ثاني": 2,
        # feminine — skill nouns like تمرين/طريقة pull gendered ordinals from real users
        "الاولى": 1, "الأولى": 1, "اولى": 1, "أولى": 1,
        "الثانية": 2, "الثانيه": 2, "ثانية": 2, "ثانيه": 2,
    }
    if isinstance(choice, str):
        idx = _ORDINAL_WORDS.get(choice.strip().lower())
        if idx is not None and 0 < idx <= len(offered):
            return offered[idx - 1]
```
(Hoist `_ORDINAL_WORDS` to module level next to the other constants; lowercase is a no-op for Arabic and required for "First".)

Also extend the existing digit-index branch to Arabic-Indic digits: normalize `choice` with `str.translate(str.maketrans("١٢٣٤٥٦٧٨٩٠", "1234567890"))` before the `isdigit()` check, and add to the ordinal test:
```python
    assert _resolve_offer_choice("الاولى", offered) == "box_breathing"     # feminine
    assert _resolve_offer_choice("الثانية", offered) == "grounding_5_4_3_2_1"
    assert _resolve_offer_choice("الثانيه", offered) == "grounding_5_4_3_2_1"  # ta-marbuta-as-ha spelling
    assert _resolve_offer_choice("٢", offered) == "grounding_5_4_3_2_1"    # Arabic-Indic digit
```

- [ ] **Step 4:** `uv run pytest tests/test_intent_route_node.py -q` — all pass.
- [ ] **Step 5: Commit:** `git commit -am "feat(S2-2): Arabic and English ordinal-word tolerance in offer-choice resolution"`

---

### Task 3: Live-classifier Khaleeji contract tests — the Arabic exposure gate

**Files:** Create `tests/test_arabic_offer_live.py`. These call `intent_route_node` with the REAL classifier (no mocks) — `@pytest.mark.slow`, network/API required. They replace the mocked tests as the S2-2 EVIDENCE (the mocked tests stay as structure pins).

- [ ] **Step 1: Create the file:**

```python
"""S2-2 exposure gate: live-classifier Khaleeji offer-reply contract.

The 2026-06-13 audit (finding S2-2) proved the mocked contract tests passed while
the LIVE classifier failed bare and positional Khaleeji accepts. These tests are
the merge/launch evidence for Arabic exposure: they run the real classifier on
real Khaleeji replies with an offer pending. All slow-marked (real LLM calls).
Failure here = Arabic launch stays blocked, whatever the mocked tests say.
"""
import pytest

from sage_poc.nodes.intent_route import intent_route_node

pytestmark = pytest.mark.slow

_OFFERED = ["box_breathing", "grounding_5_4_3_2_1"]


def _ar_state(raw: str, en: str) -> dict:
    return {
        "message_en": en,
        "raw_message": raw,
        "detected_language": "ar",
        "is_safe": True,
        "crisis_state": "none",
        "active_skill_id": None,
        "crisis_flags": [],
        "clinical_flags": [],
        "conversation_history": [
            {"role": "user", "content": "صار لي اسبوع ما اقدر انام"},
            {"role": "assistant", "content": "في خيارين ممكن يساعدونك: تنفس الصندوق او تمرين الحواس الخمس. وممكن بعد نكمل سوالف عادي. وش تفضل؟"},
        ],
        "therapeutic_profile": None,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 4,
        "engagement": 5,
        "path": ["safety_check"],
        "offered_skill_ids": list(_OFFERED),
        "declined_skills": [],
    }


# ── DEGRADED-TRANSLATION PINS (required amendment, plan review 2026-06-13) ───
# The gate must reproduce the audit's failure conditions, not sanitized ones.
# In production message_en comes from the real translation layer, which is WHERE
# the S2-2 loss happened. A hand-supplied correct translation lets the classifier
# pass on clean English without ever exercising the raw-Arabic line — the suite
# could go green while production still fails. Each accept case therefore pins
# the OBSERVED degraded translation; the clean-translation variants exist only to
# show both signals agree.
#
# Evidence basis: "my father the second" is the proven degradation for "ابي الثاني"
# (the live responder replied "شنو تقصد بأبوك الثاني؟", audit transcript ar-05).
# The transcripts do not record message_en for "ايه" — Step 0 below captures the
# real translator's output ONCE at execution time and pins THAT string (plus the
# "what" Egyptian-reading variant if different), so the pin is observed reality,
# not test-author guesswork.

# Step 0 (execution-time, once): run
#   uv run python -c "from sage_poc.language import translate_to_english; print(repr(translate_to_english('ايه'))); print(repr(translate_to_english('ابي الثاني')))"
# (adapt to the actual sync/async translator API in language.py) and REPLACE the
# _OBSERVED_* constants below with the captured strings before first test run.
_OBSERVED_EN_FOR_AYEH = "what"                    # ← replace with captured output
_OBSERVED_EN_FOR_ABI_ALTHANI = "my father the second"  # proven (transcript ar-05)


async def test_bare_khaleeji_accept_clean_translation():
    result = await intent_route_node(_ar_state("ايه", "yes"))
    assert result.get("offer_response") == "accept", (
        f"bare Khaleeji accept must classify accept; got {result.get('offer_response')!r} "
        f"(audit S2-2: this exact reply was offer_ignored live)"
    )


async def test_bare_khaleeji_accept_degraded_translation():
    """THE gating variant: message_en is the real translator's degraded output.
    Passing proves the raw-Arabic line overrides the corrupted translation,
    which is the pipeline deviation's entire justification."""
    result = await intent_route_node(_ar_state("ايه", _OBSERVED_EN_FOR_AYEH))
    assert result.get("offer_response") == "accept"


async def test_bare_yalla_accept():
    result = await intent_route_node(_ar_state("يلا نجرب", "let's try"))
    assert result.get("offer_response") == "accept"


async def test_positional_khaleeji_accept_degraded_translation():
    """THE gating variant for the positional case: message_en = the proven live
    degradation. accept + second-skill resolution from the raw Arabic alone."""
    result = await intent_route_node(_ar_state("ابي الثاني", _OBSERVED_EN_FOR_ABI_ALTHANI))
    assert result.get("offer_response") == "accept", (
        "audit S2-2: 'ابي الثاني' was offer_ignored live and 'ابي' parsed as 'my father'"
    )
    assert result.get("offer_choice_skill_id") == "grounding_5_4_3_2_1"


async def test_positional_khaleeji_accept_clean_translation():
    result = await intent_route_node(_ar_state("ابي الثاني", "I want the second one"))
    assert result.get("offer_response") == "accept"
    assert result.get("offer_choice_skill_id") == "grounding_5_4_3_2_1"


async def test_khaleeji_decline():
    result = await intent_route_node(_ar_state("لا مابي، بس ابي اتكلم", "no I don't want to, I just want to talk"))
    assert result.get("offer_response") == "decline"
    assert result.get("offered_skill_ids") is None
    assert result.get("declined_skills") == _OFFERED


async def test_khaleeji_topic_shift_is_other_not_decline():
    result = await intent_route_node(_ar_state(
        "اخوي ييني الاسبوع الياي وافكر وش اسوي له عشا",
        "my brother is visiting next week and I'm thinking what to cook for him",
    ))
    assert result.get("offer_response") == "other", (
        "topic-shift statements must not be recorded as declines (audit D4/S2-6)"
    )
    assert "declined_skills" not in result


async def test_khaleeji_bare_emotional_word_with_offer_pending_stays_general_chat():
    """Khaleeji analogue of the bare_emotional_words SPOF guard, scoped to the
    pipeline deviation: Node 2 now sees raw Khaleeji on offer turns, so the guard
    family needs a Khaleeji-bearing case. A bare emotional statement while an offer
    is pending must classify general_chat and must NEVER be read as an accept."""
    result = await intent_route_node(_ar_state("وايد متضايق اليوم", "I'm really upset today"))
    assert result.get("primary_intent") == "general_chat", (
        "bare Khaleeji emotional word must not classify new_skill/crisis "
        "(SPOF guard family, Arabic extension for the raw-Arabic deviation)"
    )
    assert result.get("offer_response") != "accept", (
        "venting while an offer is pending is not consent"
    )
```

- [ ] **Step 2:** First execute the Step-0 capture and replace the `_OBSERVED_*` constants with the real translator outputs (report the captured strings). Then run `uv run pytest tests/test_arabic_offer_live.py -m slow -v` (8 cases, real LLM calls). EXPECT failures on the first run — that is the point; the degraded-translation variants are the gating cases and must pass on the raw-Arabic signal alone. Iterate Task 1's exemplar/disambiguation wording until all 8 pass consistently. Run the suite 3× and record per-case pass counts. If a case cannot be stabilized by prompt wording alone, STOP and report which (escalation: classifier model choice or translation-layer fix becomes a scoped decision).
- [ ] **Step 3:** Re-run the SPOF guard (mandatory, intent_route module changed): `uv run pytest tests/test_nodes.py -k "bare_emotional_words" -m "slow" -v` — PASS required.
- [ ] **Step 4: Commit:** `git add tests/test_arabic_offer_live.py && git commit -m "test(S2-2): live-classifier Khaleeji offer contract, the Arabic exposure gate"`

---

### Task 4: Composer echo verification + clinical blurb handoff

**Files:** Modify `tests/test_engagement_templates.py`; create `docs/work-orders/arabic-offer-blurbs.md`.

- [ ] **Step 1: Composer echo test** (the content drop must activate with zero code changes) — append to `TestSkillOfferComposition`:

```python
    def test_authored_ar_display_names_flow_into_offer_block(self, monkeypatch):
        from sage_poc.prompts import composer
        fake = {
            "worry_time": {"display_name": {"en": "Worry time", "ar": "وقت القلق"},
                            "description": {"en": "x", "ar": "طريقة تحصر القلق في وقت محدد"}},
            "cognitive_restructuring": {"display_name": {"en": "Reframing practice", "ar": None},
                                         "description": {"en": "y", "ar": None}},
        }
        monkeypatch.setattr(composer, "_offer_descriptions", lambda: fake)
        state = _composer_state(
            offered_skill_ids=["worry_time", "cognitive_restructuring"],
            detected_language="ar",
        )
        system_str, user_str, layers = compose_prompt(state)
        assert "وقت القلق" in user_str, "authored ar display name must render"
        assert "طريقة تحصر القلق" in user_str
        assert "Reframing practice" in user_str, "null ar falls back to en"
```
(Import `compose_prompt` per the file's existing pattern; note `_offer_descriptions` is lru_cached — monkeypatching the symbol bypasses the cache, which is why the test patches the function, not the file.)

- [ ] **Step 2:** Run — this should PASS already (the bilingual envelope shipped in PR #4); if it fails, the fallback chain has a bug: fix before proceeding (report it).

- [ ] **Step 3: Write the handoff work order** `docs/work-orders/arabic-offer-blurbs.md`:

```markdown
# Work Order — Khaleeji Arabic Offer Blurbs (S2-2 content arm)

**Date opened:** 2026-06-13
**Owner:** Clinical lead (authoring + sign-off); engineering contact for the data drop
**Source:** PR #4 audit finding S2-2 (Arabic launch-blocking); reviewer-confirmed sequencing (before R2)
**Blocking:** Arabic user exposure of the consent-gate feature

## What is needed

Khaleeji Arabic `display_name.ar` and `description.ar` for all 25 offerable skills in
`src/sage_poc/prompts/offer_descriptions.json`. The file already carries the bilingual
envelope (`{"en": ..., "ar": null}`); authored values are a pure data drop — they
activate the offer rendering, the classifier grounding, and accept-by-name matching
with zero code changes (mechanics shipped and tested on feat/arabic-offer-acceptance).

## Authoring constraints — KHALEEJI-EXPLICIT (MSA-correct is NOT the acceptance bar)

The acceptance bar is the C-7 evaluation dimensions, applied to Khaleeji specifically:
1. **Grammar** — correct for spoken Gulf Arabic as written in chat, not MSA grammar.
   MSA-correct text that no Emirati would type FAILS this bar.
2. **Naturalness** — the register a Dubai user texts a friend in. Concrete precedent
   from the audit's live scoring: "خمس عشر دقيقة" was flagged as too formal mid-Khaleeji;
   prefer "ربع ساعة". Numbers, durations, and connectors should follow texting register.
3. **Register consistency** — no MSA/Khaleeji mixing within one blurb; match the
   warmth register of the existing approved Khaleeji skill examples (the Arabic
   examples at position [0] in the skill JSONs are the in-repo register reference).
4. **Gendered forms** — blurbs are read by all users: prefer gender-neutral phrasings;
   where Arabic forces agreement, follow the existing cultural_preferences gender_address
   convention and flag any entry where neutrality was impossible so the clinician
   reviewer decides explicitly rather than by default.

Mechanical constraints (CI-enforced):
- Plain words, no clinical jargon, rough duration included, no pressure framing.
- No em dashes anywhere (project rule: they mirror into LLM output).
- display_name ≤ 50 chars, description ≤ 160 chars, no placeholder markers.
- Display names become the EXACT strings users accept by — they are echoed verbatim
  into accept-classification grounding. Choose names a user would naturally repeat back.
- The audit transcripts (docs/superpowers/audits/2026-06-13-engagement-pr4-audit-transcripts.md)
  are the C-7 scoring input; coordinate with the native Khaleeji-speaker reviewer
  scoring them — same reviewer, same dimensions, one calibration.

## Process

1. Clinical authors fill the 25 `ar` pairs (engineering provides the en table below).
2. Engineering applies the data drop in one commit; CI validates envelope/length/em-dash
   plus placeholder-marker guards automatically (tests/test_engagement_templates.py).
3. Live Khaleeji contract suite re-run (tests/test_arabic_offer_live.py) with authored
   names in the loop; native-speaker spot-check of 3 rendered offer turns.
4. approved_by set in the file _meta on sign-off.

## The 25 entries

(engineering: paste the current en table from offer_descriptions.json here when handing off)

## Status

OPEN. Mechanics merged on feat/arabic-offer-acceptance; content not started.
```

- [ ] **Step 4:** Fill the "25 entries" section programmatically (python: load the JSON, emit a markdown table of skill_id / display_name.en / description.en).
- [ ] **Step 5: Commit:** `git add tests/test_engagement_templates.py docs/work-orders/arabic-offer-blurbs.md && git commit -m "feat(S2-2): composer ar-echo pin; clinical handoff work order for Khaleeji blurbs"`

---

### Task 5: Full verification + PR

- [ ] **Step 1:** `uv run pytest tests/ -q -m "not slow" 2>&1 | tail -3` — no new failures vs the branch baseline (compare against PR #4's failure set; the known pre-existing/env failures persist).
- [ ] **Step 2:** Live gates: `uv run pytest tests/test_arabic_offer_live.py -m slow -q` ×3 (stability) and the bare_emotional_words guard. Record per-case pass counts (e.g., "8/8 cases at 3/3 runs") — these numbers go in the PR body so Rule 1 signs against evidence and future flakes have a baseline.
- [ ] **Step 2b: Full-server Khaleeji accept smoke (required amendment — the full-pipeline witness).** The audit's failures were full-pipeline failures; node-level tests are the fast loop, this is the final evidence. Start the server per the Phase D pattern (uvicorn on :8001, real DATABASE_URL checkpointing; never touch :8000; kill own PID after). Script (throwaway, /tmp):
  1. Turn 1 (session `s2-2-smoke-1`): "صار لي اسبوع ما اقدر انام وافكاري ما توقف" → expect an offer turn (`skill_offer_made` in path; note the offered list).
  2. Turn 2: "ابي الثاني" → through the REAL translation layer, real history, real checkpoint.
  3. Assert from a direct checkpoint read (AsyncPostgresSaver `aget`, Phase D pattern): `active_skill_id == <second offered skill>`, `offer_promoted` in the turn's path, `offered_skill_ids` cleared.
  4. Repeat once with bare "ايه" in a fresh session asserting promotion of the FIRST offered skill.
  Record both transcripts in the PR body. If the smoke fails while the node suite is green, the degraded-translation pins are incomplete — capture the live `message_en` from the failure and extend the pins before iterating.
- [ ] **Step 3:** Update `docs/SageAI_architecture_current.md`: §3 (Language Pipeline) gains the declared deviation — raw Khaleeji reaches Node 2's classifier prompt on ar offer-classification turns only, with the bound and the widening precondition stated; §5.2 documents the PENDING OFFER additions (raw-Arabic line, Khaleeji exemplars, ar display-name grounding, ordinal tolerance) and names the live contract suite as the Arabic exposure gate.
- [ ] **Step 4:** Push + PR onto `feat/engagement-r1-r3-r5` (or master if PR #4 has merged — say which), body: audit S2-2 reference, live-test stability counts (3 runs), the sign-off items — Rule 1 for the prompt-block change AND for the §3 pipeline deviation specifically, clinical for the Khaleeji exemplar wording + the blurb work order — and the explicit statement that Arabic exposure stays blocked until the blurb work order closes and the live suite is green on authored names.

---

## Risks / notes

- **Live-test flakiness is signal, not noise:** the audit proved mocked tests hide exactly this failure class. If Task 3 can't stabilize via prompt wording, the escalation path (translation-layer fix or classifier model choice) is a scoped decision, not silent retry-until-green.
- **Token cost:** the raw-Arabic line adds ~1 line to ar offer turns only; the display map grows by authored-name lengths. No L1-budget interaction (classifier prompt, not composer prompt).
- **S2-6 adjacency:** the topic-shift live test pins `other`-not-`decline` for one Khaleeji case, which overlaps the separate S2-6 boundary-tightening item (Block 4) — that item stays open; this test just prevents the Arabic variant from regressing.
- **INTENT_SYSTEM is never edited** in this plan; every task re-runs the SPOF guard anyway.
