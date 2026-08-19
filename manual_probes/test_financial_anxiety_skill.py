import json
import uuid
from urllib.request import Request, urlopen

session_id = str(uuid.uuid4())
history = []

def chat(msg):
    history.append({"role": "user", "content": msg})
    data = json.dumps({"messages": history, "session_id": session_id}).encode()
    req = Request(
        "http://localhost:8000/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urlopen(req, timeout=90) as r:
        body = r.read().decode()
        hdrs = dict(r.headers)
    for prefix in ["[[CRISIS_SIGNAL]]", "[[CRISIS_DETECTED]]"]:
        if body.startswith(prefix):
            body = body[len(prefix):].strip()
    history.append({"role": "assistant", "content": body})
    return {
        "text": body,
        "skill_id": hdrs.get("x-sage-skill-id", ""),
        "step_id": hdrs.get("x-sage-step-id", ""),
        "path": hdrs.get("x-sage-node-path", "[]"),
        "wc": len(body.split())
    }

turns = [
    # Turn 1: The provided trigger
    "My financial worries are completely consuming me. I think about money constantly and it is affecting my sleep, relationships, and work.",

    # Turn 2: Respond to validation — add Gulf-specific specifics (kafala, remittance)
    "Yes, exactly. I work here in Dubai on a visa that is tied to my employer. If I lose my job, I lose my visa and I have to leave the country. And my parents and younger siblings back home depend on me — I send money every month. The pressure of knowing I am the only one keeping everything together is just overwhelming.",

    # Turn 3: Confirm feeling heard, deepen the specific anxiety
    "You really do understand it. The worst part is the constant 'what if' thoughts — what if the company downsizes, what if my contract isn't renewed? I can't afford to lose this job because then everything falls apart. My family loses their income, I lose my home here, and I would feel like I failed them completely.",

    # Turn 4: Respond to psychoeducation — acknowledge the distinction
    "That distinction actually makes sense. I know the worrying itself isn't helping me — it doesn't change the financial situation at all. But my mind just keeps spinning. I know some things like the company's business decisions are totally out of my control, but the anxiety doesn't care about that. It just keeps going.",

    # Turn 5: Reflect on locus of control
    "I think what's within my reach is how I take care of myself day to day — getting enough sleep, not letting the worry spiral at night. And I can make sure I do good work so my employer sees my value. What feels completely outside my hands is the broader economy, whether the company decides to cut costs, and how much my family needs each month.",

    # Turn 6: Engage with the values/provider reframe
    "That's a different way to look at it. When I think about WHY I'm carrying all this — it's because I love them. My mother's health needs, my sister's university fees, being able to give my family a better life. The worry is real but so is the love behind it. I've never really thought about separating those two things before.",

    # Turn 7: Name a concrete small step
    "I think one thing I can do this week is call my mother — not to talk about money or obligations, just to hear her voice and remind myself why this matters. And I'll try to put my phone away at 9pm so the financial news and work emails don't keep feeding the anxiety before bed. Those feel manageable.",
]

print(f"Session ID: {session_id}\n")
print("=" * 70)

results = []
for i, msg in enumerate(turns, 1):
    print(f"\n--- TURN {i} ---")
    print(f"USER: {msg[:120]}{'...' if len(msg) > 120 else ''}")
    result = chat(msg)
    results.append(result)
    print(f"SKILL: {result['skill_id']} | STEP: {result['step_id']} | WC: {result['wc']}")
    print(f"PATH: {result['path']}")
    has_error = "[[SERVER_ERROR]]" in result['text']
    print(f"ERROR: {has_error}")
    print(f"RESPONSE ({result['wc']} words): {result['text'][:300]}{'...' if len(result['text']) > 300 else ''}")
    print()

print("=" * 70)
print("\nSUMMARY TABLE:")
print(f"{'Turn':<6} {'Skill ID':<20} {'Step ID':<30} {'WC':<6} {'Error'}")
for i, r in enumerate(results, 1):
    has_error = "[[SERVER_ERROR]]" in r['text']
    print(f"{i:<6} {r['skill_id']:<20} {r['step_id']:<30} {r['wc']:<6} {has_error}")

# Step progression check
print("\nSTEP PROGRESSION:")
steps_seen = []
for i, r in enumerate(results, 1):
    step = r['step_id']
    if step and (not steps_seen or steps_seen[-1] != step):
        steps_seen.append(step)
    print(f"  Turn {i}: {step}")

print(f"\nUnique steps (in order): {steps_seen}")
expected_steps = ["normalize_and_validate", "psychoeducate_and_separate", "coping_and_agency"]
covered = [s for s in expected_steps if s in steps_seen]
print(f"Expected steps covered: {covered}")
missing = [s for s in expected_steps if s not in steps_seen]
print(f"Missing steps: {missing}")
