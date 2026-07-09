# §3a Low-Mood Trigger Set — Clinician Deliverable (fire + look-alike)

> **For Vee (clinician), via PO.** This is the **recall floor on the §3a safety screen**, not copy-completeness. When the `SAGE_LOW_MOOD_SCREEN` flag is ON, whether this detector fires is what decides whether a depression-cluster user is asked the woven suicide-risk question at all. So it sits in the same tier as the D5 affirmative lists and the verbatim SI string: a **hard prerequisite before the flag is flipped, including internal testing.** Until it is signed, the flag stays OFF and a §3a miss is a fail-safe no-op (falls through to today's unscreened offer = current prod behaviour).
>
> **Two lists, both signed together (mirroring D5's fire/clear pairing).** A fire-list signed without a look-alike list will drift toward over-firing the moment engineering makes matching token-robust — and a false positive here is not benign (it asks an SI question of someone who did not need it and routes a benign user at the still-broken GL-1 card, the SF-6 harm). So you are ratifying the **precision boundary** in the same pass as the fire-list.
>
> **Status: ENGINEERING DRAFT — every row `PROPOSED, clinician tick required`.** The FIRE list is transcribed from the BOT BEHAVIOUR §3a trigger tables (your own words). The LOOK-ALIKE list is engineering-proposed and needs your judgement most, since it defines what must NOT fire. Edit / add / reject freely. The seed currently hardcoded in `low_mood_detect.py` is a **placeholder** labelled as such in the code, pointing here; it is not "the trigger logic done."
>
> **The discriminator (state it, then test it):** §3a fires on **global, pervasive, persistent** loss of interest / energy / motivation / connection across life. It must NOT fire on the **local, situational, task-specific, or physical** look-alikes below. Every fire row should read as "across the board / lately / in general"; every look-alike is "this one thing / today / after X."

## A. FIRE list (transcribed from BOT BEHAVIOUR §3a tables — approve/edit/reject per family)

| Family | Proposed trigger phrases | Tick |
|---|---|---|
| Energy / effort | "I don't have the energy", "everything feels like an effort", "even small tasks feel difficult", "I can't seem to get going", "I don't have the energy to do anything", "I just want to stay in bed", "I just want to stay under the covers" | [ ] |
| Anhedonia / interest | "nothing sounds enjoyable", "I don't enjoy the things I used to", "I don't look forward to anything", "nothing feels rewarding", "I don't feel interested in anything", "I've lost interest in everything", "nothing brings me joy anymore" | [ ] |
| Motivation | "I don't feel like doing anything", "I can't be bothered", "I don't feel motivated", "I just don't have the motivation", "I have no motivation for anything", "I keep putting everything off" | [ ] |
| Social withdrawal | "I don't want to see anyone", "I keep cancelling plans", "I just want to be on my own", "I've been avoiding people", "I don't want to leave the house", "I'm withdrawing from everyone", "I don't want to talk to anyone", "I just want to be left alone" | [ ] |
| Affective flatness | "I feel flat", "I feel numb", "I don't really care anymore", "I feel disconnected from everything", "I feel emotionally drained", "I feel empty", "I don't feel like myself" | [ ] |
| Meaning / going through the motions | "I'm just going through the motions", "everything feels pointless", "I feel stuck" | [ ] |
| Explicit ask | "build a better routine" | [ ] |

**Question for you (A):** are there Gulf/UAE-common phrasings you'd add per family? (English here; the Arabic fire-list is the separate native-Khaleeji unit.) And any row above you'd move to the look-alike list?

## B. LOOK-ALIKE list — must NOT fire (the precision boundary; engineering-proposed, needs your tick most)

| Category | Proposed look-alikes (must NOT screen) | Why it's not §3a | Tick |
|---|---|---|---|
| Situational / transient | "meh, bit of a flat day today", "feeling a bit down after a rough week", "just an off day" | a day, not a pervasive pattern | [ ] |
| Task-specific (not global) | "I lost interest in the movie halfway through", "can't be bothered to cook tonight", "no energy to finish this report", "don't feel like going to the gym today" | one activity, not loss of interest across the board | [ ] |
| Physical / literal | "my arm feels numb", "numb from the cold", "I'm tired after a long week", "didn't sleep well so I've no energy today" | bodily/fatigue, not affective flatness or anhedonia | [ ] |
| Ordinary boredom | "bored, what should I do tonight", "nothing fun to do right now" | boredom seeking activity, not anhedonia | [ ] |
| Growth / values (routes elsewhere: §2b) | "I want to make a change", "I want to grow as a person" | forward-seeking, not withdrawal | [ ] |

**Question for you (B):** this list defines what we deliberately let fall through to today's normal flow. Anything here you'd actually want to fire (move up to A), or additional look-alikes you've seen that must stay out?

## C. How these get used (so you know what your signature governs)
- Engineering makes matching **family/token-robust** (so "I feel *so* numb" still matches the numb family) — but every phrase in list B stays a **held-green precision test**: the widen may not start firing on any look-alike. Recall and precision move together; the false-positive rate on list B is a recorded metric, asserted at zero, through every change.
- Both lists live in a **clinician-owned data file** (like the crisis phrases), not inline code, so future edits are auditable and go through you.
- Your signature on **both** lists is the flag-flip prerequisite (internal and external).

## What needs approval (easy path)
1. **List A (fire)** — tick each family, or edit phrasings, or add Gulf-common ones.
2. **List B (look-alike)** — tick each category, or move any row to A, or add look-alikes.
3. Confirm the **discriminator** wording (global/pervasive vs local/situational) reads right clinically.

Approve / edit / reject per row or per family. On sign, this replaces the placeholder seed and the flag can be considered for flip (with GL-1 + DPO per D10).
