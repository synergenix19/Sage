import json, uuid
from urllib.request import Request, urlopen

session_id = str(uuid.uuid4())
history = []

def chat(msg, debug=True):
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
    raw_body = body
    for prefix in ["[[CRISIS_SIGNAL]]", "[[CRISIS_DETECTED]]"]:
        if body.startswith(prefix):
            body = body[len(prefix):].strip()
    history.append({"role": "assistant", "content": body})
    result = {
        "text": body,
        "skill_id": hdrs.get("x-sage-skill-id", ""),
        "step_id": hdrs.get("x-sage-step-id", ""),
        "path": hdrs.get("x-sage-node-path", "[]"),
        "intent": hdrs.get("x-sage-intent", ""),
        "confidence": hdrs.get("x-sage-intent-confidence", ""),
        "semantic_score": hdrs.get("x-sage-semantic-score", ""),
        "wc": len(body.split()),
        "raw_error": "[[SERVER_ERROR]]" in raw_body
    }
    if debug:
        print(f"  intent={result['intent']} | skill={result['skill_id']} | step={result['step_id']} | path={result['path']}")
        print(f"  wc={result['wc']} | raw_error={result['raw_error']} | semantic_score={result['semantic_score']}")
        print(f"  RESPONSE: {result['text'][:400]}")
    return result

print(f"Session ID: {session_id}")
print()

# The system needs the FIRST message to have enough specifics to classify as new_skill.
# "financial anxiety" + specific symptoms + duration = new_skill.
# Let's try with explicit specific chronic symptom description.

print("=== Turn 1: Initial trigger with specifics ===")
r = chat("القلق المالي يسيطر عليّ بالكامل. أفكر في الفلوس طول الوقت وهذا يأثر على نومي وعلاقاتي وشغلي.")
print()

print("=== Turn 2: More context about visa/kafala/remittance ===")
r = chat("إي والله، الضغط مو بس على الفلوس. الفيزا متعلقة بالشغل، لو أخسر شغلتي لازم أرجع البلد. وأهلي يعتمدون عليّ كل شهر، ما أقدر أبعت فلوس لأهلي.")
print()

print("=== Turn 3: Provider role shame ===")
r = chat("أحس إني فاشل. ما أقدر أكلم أحد عن موضوع الفلوس، حتى أهلي، لأني ما أبي أخوّفهم. الضغط يصير داخلي كله.")
print()

print("=== Turn 4: After psychoeducation, acknowledge distinction ===")
r = chat("أيوه، أعرف إن التفكير المستمر ما راح يحل المشكلة. بس صعب أوقفه. كأن عقلي يدور على المشاكل طول الوقت.")
print()

print("=== Turn 5: Reflect on locus of control ===")
r = chat("اللي مو بيدي: نظام الكفالة، وتكاليف المعيشة، واحتياجات أهلي. لكن اللي بيدي: كيف أتعامل مع نفسي كل يوم.")
print()

print("=== Turn 6: Values/love behind provider role ===")
r = chat("هذا الكلام وصلني. اللي يقلقني على أهلي مو بس واجب، فيه محبة تحته. القلق يجي من الاهتمام.")
print()

print("=== Turn 7: Concrete step ===")
r = chat("أقدر أتصل بأمي هالأسبوع مو عشان أتكلم عن الفلوس، بس عشان أسمع صوتها. وأحاول أمشي كل يوم ربع ساعة.")
print()

print("\n=== FULL SUMMARY ===")
