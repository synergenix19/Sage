# Wave-2 — Collapsed Video-Skill Copy Sign-off Packet

**Date:** 2026-07-10 · **Route:** rides the batched clinician relay · **Format:** per skill — **tick** (script faithful, adopt) / **edit** (reword) / **reject** (rewrite).

**Context:** the H2 ruling (2026-07-10) makes the five Video-format skills deliver **all-at-once** in one turn. The executor for this is built (PR #284, `delivery_format: video_all_at_once`); it delivers the current step content concatenated, but the current steps are authored turn-by-turn ("let me know when you've done that"), which reads awkwardly in one message. These are **proposed collapsed scripts** — one continuous post-delivery message per skill — drawn from each skill's existing content + the doc's own description. They are **new clinical copy** and need sign-off before the 5 skills get `delivery_format: video_all_at_once` set.

> **Two safety notes read first (apply across the set):**
> 1. **Entry-screen gates stay separate.** 4 of 5 skills (PMR, mindfulness meditation, body scan, safe-place) keep their `entry_screen` contraindication check as a **separate first turn** — the collapsed script is only the *post-gate* delivery. Only box_breathing has no gate.
> 2. **All-at-once removes mid-delivery pauses.** Because the whole skill is one turn, any *mid-practice* step-policy trigger cannot fire — most notably mindfulness meditation's `allow_and_accept` **emotional_intensity > 5** pause (see skill 3). The upfront entry-screen gate + the next-turn safety_check still run; but if the clinician wants a mid-practice check for a skill, that skill should stay `guided_conversation`, not `video_all_at_once`. **This is the core tradeoff to weigh per skill.**

---

## 1. box_breathing  (no entry_screen gate)
**Collapsing:** `inhale_hold` → `exhale_hold` (2 steps). **Doc (L183):** *"A simple 4-count breathing pattern that slows your heart rate and signals safety to your nervous system."*

**Proposed script:**
> "Let's do a round of box breathing together. It's a simple four-count breathing pattern that slows your heart rate and signals safety to your nervous system, and I'll take you through the whole cycle in one go so the timing stays smooth. Get comfortable, and when you're ready, breathe in slowly through your nose for four counts, one, two, three, four, then hold gently with no strain for four counts, one, two, three, four. Now let the breath out slowly through your mouth for four counts, one, two, three, four, and hold empty and still for four counts, one, two, three, four, before letting your breathing return to normal. You can repeat that cycle a couple more times at your own pace, up to three full rounds for now. If holding your breath ever feels uncomfortable, or you have a breathing or heart condition, skip the holds and just breathe slowly out. There's a short video below you can follow along with if you'd like a visual guide. Once you've tried it, how are you feeling now compared to before?"

☐ tick ☐ edit: ____________ ☐ reject

## 2. progressive_muscle_relaxation  (entry_screen: pain/injury gate — stays separate)
**Collapsing:** `breathe_and_settle` → `upper_body` → `lower_body` → `integration` (post-gate). **Doc (L196):** *"Systematically tensing and releasing muscle groups to physically discharge built-up tension."*

**Proposed script:**
> "Let's work through some progressive muscle relaxation, which is systematically tensing and releasing muscle groups to physically discharge built-up tension. I'll lay out the whole sequence here, so read it through and move at your own pace. First, settle: close your eyes if that's comfortable or soften your gaze, take a slow breath in, and as you breathe out notice where your body is holding tension. Then start at the top, shrug your shoulders up to your ears and squeeze for about five seconds, then let them drop completely and notice the difference; clench your jaw gently for five seconds, then release and let your mouth hang slightly open; scrunch your face tight for five seconds, then let it all go. Move down, squeeze your hands into fists for five seconds, then open them completely; pull your stomach in tight for five seconds, then let it soften; tense your thighs and calves and curl your toes for five seconds, then release and let your legs get heavy. Go gently on, or skip, any area that's sore or injured. To finish, scan slowly through your whole body from head to feet and notice how it feels compared to when you started. A short video below walks through the same sequence if you'd like to follow along. How are you feeling now compared to when we began?"

☐ tick ☐ edit: ____________ ☐ reject

## 3. mindfulness_meditation  (entry_screen: acute-state gate — stays separate)
**Collapsing:** `settle_and_anchor` → `observe_and_return` → `allow_and_accept` → `widen_and_close` (post-gate). **Doc (L199):** *"A longer-form practice for sitting with anxious feelings without needing to fix or fight them."*

> ⚠ **Per-skill decision:** this skill carries an `allow_and_accept` **emotional_intensity > 5** mid-practice pause that all-at-once delivery cannot enforce. **Tick only if you accept losing that mid-practice check**; otherwise keep this skill `guided_conversation` (reject) and it stays turn-by-turn.

**Proposed script:**
> "Let's do a short sitting meditation together, a longer-form practice for sitting with anxious feelings without needing to fix or fight them. I'll lay out the whole practice here so you can follow it at your own pace. First, settle into a position that's upright but not rigid, and let your eyes close or rest softly downward. Bring your attention to your breath wherever you feel it most easily, the nose, the chest, or the belly, and just notice it as it already is without changing it; this is your anchor. In a little while your mind will wander to a thought, a sound, a memory, and that's completely normal, not a mistake; each time you notice it has drifted, gently bring your attention back to the breath, and that returning is the practice, however many times it takes. If a difficult feeling is present, you can turn toward it with a little curiosity and let it be there like weather passing through, while the breath stays as steady ground underneath; but you do not have to go into anything that feels too big, there is no prize for pushing, and you can come back to the breath, or stop, any time it feels like too much. When you're ready, let your awareness widen to include the whole moment, the sounds around you and your body as a whole, then gently open your eyes and come back to the room. There's a short guided video below you can follow along with instead if you'd prefer. How do you feel now compared to when we started?"

☐ tick (accept loss of mid-practice pause) ☐ edit: ____________ ☐ reject (keep turn-by-turn)

## 4. mindfulness_body_scan  (entry_screen: dissociation/dizziness gate — stays separate)
**Collapsing:** `lower_body` → `torso` → `upper_body` → `face_and_close` (post-gate). **Doc (L1338):** *"A guided practice moving attention slowly through the body … noticing physical sensations as they are, without trying to change or fix anything."*

**Proposed script:**
> "Let's move through a body scan, a guided practice moving attention slowly through the body, noticing physical sensations as they are without trying to change or fix anything. I'll guide the whole sweep here so you can take it at your own pace. Start at the very bottom, bring your attention to your feet and legs, and just notice what's actually there, warmth, pressure from the floor, weight, tingling, or maybe nothing in particular, and all of that is fine. Move up into your torso, the belly and centre of your body, and notice the breath happening here on its own, then any tightness, holding, or ease. Continue up through your shoulders, arms and hands, areas that carry a lot; notice the weight of your shoulders, and if they want to soften a little, let them without forcing it, then notice the temperature of your hands. Finally bring your attention to your face and head, letting your jaw hang a little heavier if it wants to, then widen your awareness to hold your whole body at once as a single felt sense. When you're ready, let your eyes open gently and come back to the room. A short guided video below follows the same sweep if you'd like to use it. What do you notice now compared to when we began?"

☐ tick ☐ edit: ____________ ☐ reject

## 5. safe_place_visualization  (entry_screen: safe-place-capacity/dissociation gate — stays separate)
**Collapsing:** `introduce_safe_place` → `build_the_place` → `anchor_and_return` (post-gate). **Doc (L1448):** *"A short guided imagery video for a quick mental shift — calming or uplifting imagery, a few minutes long, no activity required."*

> ⚠ **Note:** trauma-surfacing / reorientation-sensitive. The closing lines preserve the current design's gentle reorientation ("feel the surface beneath you … you're here and safe right now"). Confirm the reorientation reads as strong enough for one-turn delivery.

**Proposed script:**
> "Let's try a safe place visualization, a short guided imagery practice for a quick mental shift, with no activity required. I'll walk you through the whole thing here so you can settle into it at your own pace. We're going to imagine a place, real or made up, where you feel completely safe and calm; it might be a beach, a room, a garden, somewhere in nature, or somewhere entirely of your own making. Once you have it, let yourself be there for a moment and build it out with your senses, what do you see around you, what's the light like, what can you hear, and what can you feel physically, the temperature, the texture of the ground or seat beneath you. Notice what it is that makes this place feel safe, the solitude, the familiar sounds, the sense of being protected here. Then, as an anchor, choose a word or phrase that captures this feeling, something you can say to yourself to bring it back any time you need it. When you're ready, take a slow breath, feel the surface beneath you, and notice that you're here and safe right now in this moment. There's a short guided video below you can follow along with too. How do you feel now compared to when we started?"

☐ tick ☐ edit: ____________ ☐ reject

---

**On sign-off:** each ticked script becomes the collapsed step content, and that skill gets `delivery_format: video_all_at_once` set (engineering already merged behind the default). Arabic collapsed copy is a follow-on translation (separate sign-off). Matrix rows flip to CONFORMS only on the driven EN+AR transcript.
