# body_scan deroute decision + §1a-§6 family audit (for Vee, 2026-08-04)

One decision request, family-scoped per the PO's audit directive — with two corrections to
what the room was previously told, stated first because they change the recommendation's
grounds (not its direction).

## Corrections to the prior framing (mine, on the record)

1. **"body_scan has no contraindications field" — RETRACTED as meaningless.** No skill in
   the repo has a top-level `contraindications` field; the schema does not define one.
   Contraindication CONTENT lives inside step guidance text and semantic descriptions —
   and body_scan HAS it (5 contraindication mentions in its steps, including a
   derealization/dissociation hold on its entry screen, same pattern as MM). The
   "structurally incomplete against a MANDATORY schema field / nothing for a signature to
   ratify" argument is therefore withdrawn: there IS an authored artifact a signature can
   cover. "Sign it today" returns to the available options.
2. **"approved_by: null" is schema-wide, not distinctive.** Only 2 of 28 skills carry an
   `approved_by` key at all (behavioral_activation, psychoed_depression). The original v7
   skill set was clinician-authored at spec time and carries no per-skill field. What made
   MM distinctive was PROVENANCE: its own commit says "PENDING CLINICAL APPROVAL" and the
   2026-07-07 escalation documents it unsigned. body_scan's provenance: authored
   2026-05-27 (Track A, A7) with an evidence base (Kabat-Zinn MBSR, Williams MBCT, Ong
   2014) and 3 cultural_overrides — whether it received clinical review is NOT decidable
   from the repo. That is exactly the question for Vee, and the honest status is
   "signature record not found," not "unsigned."

## The next-hop audit (the PO's one-query check, run 2026-08-04)

Keyword tier: meditation phrasings now match NOTHING (MM's keywords left with it); "body
scan" keyword-matches body_scan directly. The live absorption is SEMANTIC-tier. Measured
ranking (BGE-M3, threshold 0.4593), with body_scan hypothetically derouted, next catchers:

| request shape | next catcher after body_scan | family? |
|---|---|---|
| "I want to try mindfulness meditation…" | act_psychological_flexibility (0.560), box_breathing (0.555) | NO — cognitive / Tier-1 breathing |
| "guided meditation" | safe_place_visualization (0.533) | **BORDERLINE — guided imagery** |
| "i want to meditate" | box_breathing (0.547) | NO — Tier-1 breathing |
| "can we do some sitting meditation" | box_breathing (0.534) | NO — Tier-1 breathing |

**The chain mostly terminates in one hop**: after body_scan, meditation demand lands in
Tier-1 breathing and cognitive skills OUTSIDE the §1a-§6 contraindicated family. The one
family-adjacent residual is `safe_place_visualization` catching "guided meditation" —
guided imagery, which can be trauma-contraindicated; whether it belongs to her §1a-§6
class is a clinical membership call, not an engineering one.

## The decision (hers, one sentence, options in recommendation order)

- **(a) Deroute body_scan** (same one-line mechanism + blurb removal; staged, executes in
  minutes) **and rule on safe_place_visualization's family membership** in the same
  sentence — in = deroute it too (then the chain fully terminates outside the family);
  out = chain terminates after body_scan alone. PO-advisor recommendation, and mine.
- **(b) Sign body_scan as-authored** — available (correction 1), covers the absorption
  path with a reviewed artifact; its entry-screen derealization hold then becomes the
  serving protection, as MM's was designed to be.
- **(c) Status quo** — body_scan keeps absorbing derouted meditation demand with its
  signature status unresolved. Not recommended; it is the state the item-3 ruling exists
  to end.

## Also before her (context that shaped this packet)

- The PO advisor's correction on the item-3 staging, which she should hear with the
  sibling decision: the "deroute cost ≈ zero" advice reasoned from the spec's offer
  ordering, not from where the matcher sends live requests once MM was gone — deroute
  redistributes demand, it does not delete it, and the first live probe found the
  redistribution landing one skill over in the same family. The one-hop-shallow cost
  model is why this packet carries the full next-hop table.
- **Deroute checklist line adopted** (this PR, corpus_constants comment): every future
  skip-set addition records where its traffic lands and the landing skill's signature
  status in the deroute's own record, at decision time rather than probe time.
