import json, uuid
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

# Plan:
# Turn 1: Initial trigger — financial anxiety dominating life, affecting sleep/relationships/work
# Turn 2: Respond to normalization — name specific pressures (visa, remittance to family)
# Turn 3: Engage deeper — express the shame and provider role burden
# Turn 4: Respond to psychoeducation — acknowledge distinction between reality and anxiety amplification
# Turn 5: Reflect on locus of control — what's in hands vs. not
# Turn 6: Engage with coping/agency step — connect to values behind provider role
# Turn 7: Name one concrete action for the week

turns = [
    # Turn 1: Initial trigger
    "القلق المالي يسيطر عليّ بالكامل. أفكر في الفلوس طول الوقت وهذا يأثر على نومي وعلاقاتي وشغلي.",

    # Turn 2: Respond to validation/normalization — add specifics about structural pressures (visa, remittance)
    "إي والله، الضغط مو بس على الفلوس بحد ذاتها. الفيزا متعلقة بالشغل، ولو أخسر شغلتي لازم أرجع البلد. وعندي أهل في المنزل يعتمدون عليّ كل شهر، ماميه وأبوي وأختي الصغيرة. أنا المسؤول الوحيد.",

    # Turn 3: Express deeper — shame, identity as provider, catastrophic thinking
    "بس أحيان أحس إني فاشل. كأن كل الناس عارفين إني ما قدرت أوفر بس أنا. ما أقدر أكلم أحد عن هذا الموضوع، حتى ما أقدر أكلم أهلي لأني ما أبي أخوّفهم. الضغط يصير داخلي كله.",

    # Turn 4: Respond to psychoeducation — acknowledge the distinction between situation and anxiety response
    "أيوه، أنا أعرف إن التفكير المستمر ما راح يحل المشكلة، بس صعب أوقفه. كأن عقلي يدور على المشاكل حتى لو ما في شي جديد. تقدر توضح لي أكثر وش الفرق بين الوضع نفسه والقلق منه؟",

    # Turn 5: Reflect on locus of control — what's in hands vs not
    "صح. اللي مو بيدي: نظام الكفالة، وتكاليف المعيشة، واحتياجات أهلي. لكن اللي بيدي شوي: كيف أتعامل مع نفسي كل يوم، وإن أحافظ على روتين يساعدني. وكمان ممكن أتكلم مع واحد أثق فيه بدل ما أحمل الضغط لحالي.",

    # Turn 6: Engage with provider role as values/love — connect meaning to burden
    "هذا الكلام وصلني. اللي يقلقني على أهلي مو بس واجب، فيه محبة تحته. أبي أساعدهم لأني أحبهم. بس الثقل أحيان يغطي على هذا الإحساس.",

    # Turn 7: Name one concrete step for the week
    "أظن اللي أقدر أسويه هالأسبوع هو إني أتصل بأمي مو عشان أتكلم عن الفلوس، بس عشان أسمع صوتها وأحس إن علاقتنا مو كلها ضغط ومسؤولية. وكمان أحاول أمشي كل يوم ربع ساعة، عشان أصفي راسي شوي."
]

print(f"Session ID: {session_id}")
print("=" * 70)

results = []
for i, msg in enumerate(turns, 1):
    print(f"\n--- Turn {i} ---")
    print(f"USER: {msg[:100]}...")
    try:
        r = chat(msg)
        results.append(r)
        print(f"SKILL_ID: {r['skill_id']}")
        print(f"STEP_ID:  {r['step_id']}")
        print(f"PATH:     {r['path']}")
        print(f"WC:       {r['wc']}")
        print(f"RESPONSE: {r['text'][:300]}...")
        has_error = "[[SERVER_ERROR]]" in r['text']
        print(f"ERROR:    {has_error}")
    except Exception as e:
        print(f"EXCEPTION: {e}")
        results.append({"text": f"EXCEPTION: {e}", "skill_id": "", "step_id": "", "path": "", "wc": 0})

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
for i, r in enumerate(results, 1):
    print(f"Turn {i}: skill={r['skill_id']!r:25} step={r['step_id']!r:35} wc={r['wc']:3} error={'YES' if '[[SERVER_ERROR]]' in r['text'] else 'no'}")
