import json, uuid
from urllib.request import Request, urlopen

session_id = str(uuid.uuid4())
history = []

def chat(msg, debug=False):
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
    if debug:
        print(f"  RAW BODY START: {repr(body[:100])}")
    has_error_in_raw = "[[SERVER_ERROR]]" in body
    # Strip prefixes
    for prefix in ["[[CRISIS_SIGNAL]]", "[[CRISIS_DETECTED]]"]:
        if body.startswith(prefix):
            body = body[len(prefix):].strip()
    history.append({"role": "assistant", "content": body})
    return {
        "text": body,
        "skill_id": hdrs.get("x-sage-skill-id", ""),
        "step_id": hdrs.get("x-sage-step-id", ""),
        "path": hdrs.get("x-sage-node-path", "[]"),
        "intent": hdrs.get("x-sage-intent", ""),
        "wc": len(body.split()),
        "raw_error": has_error_in_raw
    }

# Debug first 2 turns carefully
print("=== Turn 1 (debug) ===")
r = chat("القلق المالي يسيطر عليّ بالكامل. أفكر في الفلوس طول الوقت وهذا يأثر على نومي وعلاقاتي وشغلي.", debug=True)
print(f"intent={r['intent']}, skill={r['skill_id']}, step={r['step_id']}")
print(f"wc={r['wc']}, raw_error={r['raw_error']}")
print(f"RESPONSE: {r['text'][:400]}")

print("\n=== Turn 2 (debug) ===")
r = chat("إي والله، الضغط مو بس على الفلوس. الفيزا متعلقة بالشغل، لو أخسر شغلتي لازم أرجع. وأهلي يعتمدون عليّ كل شهر.", debug=True)
print(f"intent={r['intent']}, skill={r['skill_id']}, step={r['step_id']}")
print(f"wc={r['wc']}, raw_error={r['raw_error']}")
print(f"RESPONSE: {r['text'][:400]}")

print("\n=== Turn 3 (debug) ===")
r = chat("أحس إني فاشل. ما أقدر أكلم أحد عن موضوع الفلوس، حتى أهلي، لأني ما أبي أخوّفهم.", debug=True)
print(f"intent={r['intent']}, skill={r['skill_id']}, step={r['step_id']}")
print(f"wc={r['wc']}, raw_error={r['raw_error']}")
print(f"RESPONSE: {r['text'][:400]}")

print("\n=== Turn 4 (debug) ===")
r = chat("أيوه، أعرف إن التفكير المستمر ما راح يحل المشكلة. بس صعب أوقفه. كأن عقلي يدور على المشاكل طول الوقت.", debug=True)
print(f"intent={r['intent']}, skill={r['skill_id']}, step={r['step_id']}")
print(f"wc={r['wc']}, raw_error={r['raw_error']}")
print(f"RESPONSE: {r['text'][:400]}")
