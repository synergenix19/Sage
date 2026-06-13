import json
import uuid
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

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

# Plan the conversation:
# Turn 1: Initial trigger - intense emotional distress, need crisis skills
# Turn 2: Respond to entry_screen safety check - confirm not in danger, just overwhelmed
# Turn 3: Confirm wanting to try TIPP skills
# Turn 4: Acknowledge temperature step - confirm splashing cold water on face
# Turn 5: Report outcome of temperature step
# Turn 6: Acknowledge intense exercise step - do jumping jacks
# Turn 7: Report outcome of intense exercise
# Turn 8: Acknowledge paced breathing step - practice the breathing
# Turn 9: Report after breathing exercise
# Turn 10: Final check-in response - how feeling now

turns = [
    # Turn 1: Trigger
    "I am in intense emotional distress right now. The feelings are overwhelming and I cannot regulate. I need crisis skills immediately.",

    # Turn 2: Entry screen - answer safety check (not suicidal, just overwhelmed)
    "No, I am not having thoughts of hurting myself. I am just completely overwhelmed by emotion. My heart is racing, I feel like I might explode, I can't calm down. I need something to help me right now.",

    # Turn 3: Confirm willing to try TIPP
    "Yes, please. I want to try the TIPP skills. I have used them before and they help. Let's start.",

    # Turn 4: Temperature step - respond to cold water instruction
    "Okay, I went to the bathroom and splashed cold water on my face several times. I also ran cold water over my wrists. The shock of it definitely got my attention and brought me out of my head for a moment.",

    # Turn 5: Confirm effect of temperature
    "The cold water helped a little. My heart rate feels slightly lower. I am still feeling a lot of emotion but the intensity dropped maybe a small amount. What is next?",

    # Turn 6: Intense exercise step - respond to exercise instruction
    "I just did 30 jumping jacks as fast as I could. My legs are burning and I am out of breath. I pushed myself hard.",

    # Turn 7: Report outcome of intense exercise
    "That actually helped more than I expected. Moving my body that intensely shifted something. The emotion is still there but it feels less like it is consuming me. I feel more grounded in my body now.",

    # Turn 8: Paced breathing step - follow along with breathing
    "Okay, I am doing the paced breathing now. Breathing in slowly for a count of four, holding, and breathing out for a longer count. I did five full cycles like that.",

    # Turn 9: Report after paced breathing
    "The breathing really helped settle things down. My chest feels less tight. The racing heart has calmed quite a bit. I feel more present and less like I am going to fall apart.",

    # Turn 10: Check-in response - report current state
    "I feel significantly better. The overwhelming feeling has gone from about a 9 out of 10 down to maybe a 4. I am still emotionally activated but I feel like I can think clearly now. Thank you, the TIPP skills really worked."
]

results = []
print(f"Session ID: {session_id}")
print("="*70)

for i, turn in enumerate(turns, 1):
    print(f"\n[TURN {i}] USER: {turn[:80]}...")
    try:
        result = chat(turn)
        results.append(result)
        print(f"  skill_id : {result['skill_id']}")
        print(f"  step_id  : {result['step_id']}")
        print(f"  path     : {result['path']}")
        print(f"  wc       : {result['wc']}")
        print(f"  response : {result['text'][:200]}...")

        # Check for server error
        if "[[SERVER_ERROR]]" in result['text']:
            print("  *** SERVER ERROR DETECTED ***")
    except HTTPError as e:
        print(f"  HTTP ERROR: {e.code} {e.reason}")
        results.append({"text": f"HTTP_ERROR:{e.code}", "skill_id": "", "step_id": "", "path": "[]", "wc": 0})
    except URLError as e:
        print(f"  URL ERROR: {e.reason}")
        results.append({"text": f"URL_ERROR:{e.reason}", "skill_id": "", "step_id": "", "path": "[]", "wc": 0})
    except Exception as e:
        print(f"  EXCEPTION: {e}")
        results.append({"text": f"EXCEPTION:{e}", "skill_id": "", "step_id": "", "path": "[]", "wc": 0})

    time.sleep(0.5)  # Small pause between turns

print("\n" + "="*70)
print("SUMMARY TABLE")
print("="*70)
print(f"{'Turn':<6} {'skill_id':<18} {'step_id':<22} {'WC':<6} {'Errors'}")
print("-"*70)

issues = []
for i, r in enumerate(results, 1):
    has_error = "[[SERVER_ERROR]]" in r['text']
    wc_ok = 20 <= r['wc'] <= 250
    print(f"{i:<6} {r['skill_id']:<18} {r['step_id']:<22} {r['wc']:<6} {'SERVER_ERROR' if has_error else ('WC_OUT_OF_RANGE' if not wc_ok else 'OK')}")
    if has_error:
        issues.append(f"Turn {i}: SERVER_ERROR in response")
    if not wc_ok and r['wc'] > 0:
        issues.append(f"Turn {i}: Word count {r['wc']} out of range 20-250")

print("\n" + "="*70)
print("STEP PROGRESSION")
print("="*70)
step_ids_seen = [r['step_id'] for r in results if r['step_id']]
print(f"Step IDs seen: {step_ids_seen}")

expected_steps = ["entry_screen", "temperature", "intense_exercise", "paced_breathing", "check_in"]
steps_seen_set = set(step_ids_seen)
for step in expected_steps:
    found = step in steps_seen_set
    print(f"  {step}: {'FOUND' if found else 'MISSING'}")
    if not found:
        issues.append(f"Step not traversed: {step}")

print("\nISSUES FOUND:")
if issues:
    for issue in issues:
        print(f"  - {issue}")
else:
    print("  None")

# Output full results as JSON for parsing
print("\n" + "="*70)
print("FULL RESULTS JSON:")
print(json.dumps(results, indent=2))
