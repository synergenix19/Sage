"""Tests for the doc-derived INSTRUCTIONAL_SKILLS stopgap (Psychoed Mechanism-A, Task 1).

Derivation table (doc pathway -> Format cell VERBATIM -> skill_id), sourced from
docs/superpowers/specs/bot-behaviour-oracle/bot-behaviour-spec-source-2026-07-08.md
("Skill" tables under each category's "4. Skills" section). Verified two ways:
(1) `grep -n -i "instructional"` over the full 1842-line source returns exactly
    4 hits, only one of which is a table cell (the rest are prose using the word
    "instructional" as an adjective, not a Format value):
      L1296  prose ("...the fix is more instructional (habits and environment)...")
      L1330  TABLE CELL — the Format value itself
      L1335  prose ("Sleep Hygiene (instructional), key areas to walk through:")
      L1343  prose (timing note)
    So `^Instructional$` as a standalone Format-column line occurs exactly once
    in the whole spec source.

| Doc pathway (category, line)          | Skill (line)                | Format cell (line)                    | skill_id       | In set? |
|----------------------------------------|------------------------------|----------------------------------------|----------------|---------|
| S1b Sleep Disruption (L1295, Skills L1324-1332) | Sleep Hygiene (L1329) | `Instructional` (L1330, VERBATIM)      | sleep_hygiene  | YES     |
| S1b Sleep Disruption, "if asked for more depth" (L1331) | sleep-001 (fuller info resource) (L1332) | `Info -- see timing note below` (L1333) | (KB article, not a skill_id) | NO -- info_resource, not Instructional; also carries the S1b timing suppression (L1343) that must not be bypassed |
| Anxiety Offer-First (L110-120)         | Box Breathing (L115)         | `Video` (L116)                         | box_breathing  | NO |
| Anxiety Offer-First (L110-120)         | 5-4-3-2-1 Grounding (L118)   | `Visual + guided conversation` (L119)  | grounding_5_4_3_2_1 | NO |
| Anxiety Offer-Second (L121-134)        | STOPP (L125)                 | `Visual + guided conversation` (L126)  | stop_technique | NO |
| Anxiety Offer-Second (L121-134)        | PMR (L128)                   | `Video` (L129)                         | progressive_muscle_relaxation | NO |
| Anxiety Offer-Second (L121-134)        | Mindfulness Meditation (L131)| `Video` (L132)                         | mindfulness_meditation | NO |
| Anxiety Offer-Second (L121-134)        | Psychoeducation (L134, "options from 1f") | `Info` (L135) | (factsheet, not a skill_id) | NO -- info_resource |
| Worry Loops / C-1d (L256)              | Worry Time (L256)            | `Described in one message` (L257)      | worry_time     | NO -- single_message |
| S1a Mind Racing at Night (L1269-1281)  | Worry Time (L1280, 2nd occurrence, same skill different category table) | `Guided conversation` (L1281) | worry_time | NO -- still not `Instructional` verbatim (doc's two Worry Time table rows disagree with each other, but neither is `Instructional`) |
| S1a Mind Racing at Night               | Pre-Sleep Box Breathing (L1274) | `Video` (L1275)                     | box_breathing  | NO |
| S1a Mind Racing at Night               | Guided Visualization / PMR (L1277) | `Video` (L1278)                  | safe_place_visualization / progressive_muscle_relaxation | NO |
| DF-6..DF-13 (conformance matrix cross-check, section B) | dbt_tipp, grounding_5_4_3_2_1, stop_technique, worry_tree, Extended Exhale, Emotions Wheel, Life Compass | `one instruction at a time` / `Visual + guided conversation` / `Described in one message` / `Show visual, THEN guided` / `single instruction, no counting` / `Visual (static)` / `Show all domains, then one at a time` | various / no matching skill JSON | NO -- none read `Instructional` verbatim |
| DF-15..n (conformance matrix, remaining guided-conversation skills) | BA, CBT, cognitive_restructuring, problem_solving, assertive_comm, interpersonal, DEARMAN, self_compassion, financial_anxiety, grief_loss, psychoed_x3, mi_readiness, mood_check_in, post_crisis, values, act | `Guided conversation` | behavioral_activation, cbt_thought_record, cognitive_restructuring, problem_solving_therapy, assertive_communication, interpersonal_effectiveness, self_compassion_break, financial_anxiety, grief_loss, psychoed_anxiety, psychoed_depression, psychoed_stress, mood_check_in, post_crisis_check_in, values_clarification, act_psychological_flexibility | NO -- Guided conversation, not Instructional |

Conclusion: exactly one skill_id -- `sleep_hygiene` -- has a Format cell that reads
`Instructional` verbatim anywhere in the spec source. This is a deliberately SMALL
stopgap set; see src/sage_poc/skills/instructional_set.py for the discipline this
protects (do not extend by "skills that teach" reasoning).
"""

import pytest

from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.skills import _SKILLS
from sage_poc.skills.instructional_set import INSTRUCTIONAL_SKILLS


def test_all_members_exist_in_skill_registry():
    for skill_id in INSTRUCTIONAL_SKILLS:
        assert skill_id in SKILL_REGISTRY, (
            f"INSTRUCTIONAL_SKILLS member {skill_id!r} is not a registered skill_id"
        )


def test_set_is_the_expected_verbatim_derivation():
    # The whole point of the task: this is a SMALL, certain set, not a
    # "skills that teach" grep. Exactly one member today.
    assert INSTRUCTIONAL_SKILLS == frozenset({"sleep_hygiene"})


def test_worry_time_excluded_single_message_format():
    """worry_time's Format cell reads 'Described in one message' (L257, Worry
    Loops / C-1d) and 'Guided conversation' (L1281, S1a Mind Racing at Night) --
    neither is `Instructional` verbatim. Folding single_message-format skills
    into an "instructional" set is the enum-collapse mistake the design doc
    warns against re-making as a curated list.
    """
    assert "worry_time" not in INSTRUCTIONAL_SKILLS


def test_sleep_001_info_resource_excluded():
    """sleep-001 is a KB article_id (data/knowledge_corpus/en/sleep-001.json),
    not a skill_id -- it can never appear in SKILL_REGISTRY or INSTRUCTIONAL_SKILLS.
    Its doc Format cell reads 'Info -- see timing note below' (L1333), not
    Instructional. It is a link-handoff to the fuller resource, and it owns the
    S1b nighttime timing suppression (L1343: don't hand over the longer reading
    resource while the person is mid-struggle at night) -- a consult that
    silently substituted sleep-001 for sleep_hygiene (or vice versa) would bypass
    that suppression. Confirm it is not a skill_id at all, and confirm the
    skill_id namespace has no such entry.
    """
    assert "sleep-001" not in SKILL_REGISTRY
    assert "sleep-001" not in INSTRUCTIONAL_SKILLS
    assert "sleep_hygiene" in INSTRUCTIONAL_SKILLS  # the actual instructional skill, distinct from the KB article


@pytest.mark.xfail(reason="until P0b delivery_format field lands", strict=False)
def test_converges_with_p0b_delivery_format_field():
    """Pin the convergence, don't just intend it.

    There is no `delivery_format` field on the `Skill` schema yet (P0b). Today,
    `getattr(skill, "delivery_format", None)` is None for every registered skill,
    so the right-hand side below is the empty set and this assertion fails --
    which is why it is marked xfail(strict=False): a *known*, *expected* red,
    not a passing no-op.

    The day P0b lands a real `delivery_format` field, this test starts running
    for real: if `sleep_hygiene` (or any other skill) reports
    `delivery_format == "instructional"` and INSTRUCTIONAL_SKILLS disagrees, this
    flips from xfail to a hard failure, forcing reconciliation instead of letting
    the curated set silently drift.

    This is the guard against INSTRUCTIONAL_SKILLS becoming the project's THIRD
    dormant-divergent artifact -- after `escalation_matrix` (built, never
    consulted) and the activation-map (built, never wired) -- a curated set that
    looks authoritative but nothing ever checks against the real field once the
    real field exists.
    """
    derived_from_schema = frozenset(
        skill_id
        for skill_id in SKILL_REGISTRY
        if getattr(_SKILLS[skill_id], "delivery_format", None) == "instructional"
    )
    assert INSTRUCTIONAL_SKILLS == derived_from_schema
