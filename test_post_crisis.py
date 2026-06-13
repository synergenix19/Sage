import json, uuid
from urllib.request import Request, urlopen

session_id = str(uuid.uuid4())
history = []

def chat(msg):
    history.append({"role": "user", "content": msg})
    data = json.dumps({"messages": history, "session_id": session_id}).encode()
    req = Request("http://localhost:8000/chat", data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=90) as r:
        body = r.read().decode()
        hdrs = dict(r.headers)
    for prefix in ["[[CRISIS_SIGNAL]]", "[[CRISIS_DETECTED]]"]:
        if body.startswith(prefix): body = body[len(prefix):].strip()
    history.append({"role": "assistant", "content": body})
    return {
        "text": body,
        "skill_id": hdrs.get("x-sage-skill-id", ""),
        "step_id": hdrs.get("x-sage-step-id", ""),
        "path": hdrs.get("x-sage-node-path", "[]"),
        "wc": len(body.split())
    }

turns = [
    # Turn 1: Trigger - coming back after a hard week, wanting to check in
    "مريت بأسبوع صعب جداً الأسبوع الماضي. كانت الأمور مخيفة. أبي أشيك على نفسي اليوم وأشوف كيف أنا.",
    # Turn 2: Respond to the check-in question - calmer now, stable, still here
    "الحين أحس أحسن بكثير. الحمد لله على السلامة. ما عدت أحس بنفس الخوف. أحس نوع من الهدوء، بس ما نسيت اللي صار.",
    # Turn 3: Indicate some continued heaviness but managing, open to talking
    "في أحيان أحس بثقل بس أقدر أتحمله. لو تبي أتكلم عن اللي يساعدني، أنا مستعد.",
    # Turn 4: Feeling steadier, ready to wrap up but grateful for the support
    "أشكرك على وقوفك معاي. أحس الحين أقدر أمشي. بس أبي أعرف إذا يحتاجني شي، وين أرجع.",
    # Turn 5: Acknowledge the close warmly
    "شكراً جزيلاً. هذا كفاية الحين. بس حبيت أعرف إن في مكان أرجع له لو احتجت."
]

results = []
for i, msg in enumerate(turns):
    print(f"\n{'='*60}")
    print(f"TURN {i+1}")
    print(f"USER: {msg}")
    r = chat(msg)
    results.append(r)
    print(f"SAGE: {r['text']}")
    print(f"  skill_id={r['skill_id']} | step_id={r['step_id']}")
    print(f"  path={r['path']} | wc={r['wc']}")

print("\n\n" + "="*60)
print("SUMMARY")
for i, r in enumerate(results):
    has_error = "[[SERVER_ERROR]]" in r["text"]
    print(f"Turn {i+1}: skill={r['skill_id']}, step={r['step_id']}, wc={r['wc']}, error={has_error}")
