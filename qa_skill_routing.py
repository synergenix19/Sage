"""Test different trigger messages for post_crisis_check_in routing"""
import asyncio, os, json, uuid
from dotenv import load_dotenv
load_dotenv()

async def test_msg(msg, label):
    from sage_poc.graph import build_graph
    from sage_poc.server_helpers import _build_state, _RequestLike, _MessageLike

    graph = build_graph(checkpointer=None)
    session_id = str(uuid.uuid4())

    req = _RequestLike(
        messages=[_MessageLike(role='user', content=msg)],
        session_id=session_id
    )
    state = _build_state(req)
    state['therapeutic_profile'] = None

    config = {'configurable': {'thread_id': session_id}}
    result = await asyncio.wait_for(
        graph.ainvoke(state, config=config),
        timeout=60
    )

    skill_id = result.get('active_skill_id', 'None')
    step_id = result.get('executed_step_id', 'None')
    path = result.get('path', [])
    sem_score = result.get('semantic_score', 'N/A')
    primary_intent = result.get('primary_intent', 'N/A')
    print(f"\n[{label}]")
    print(f"  msg: {msg[:60]}...")
    print(f"  skill_id={skill_id}, step_id={step_id}")
    print(f"  path={path}")
    print(f"  semantic_score={sem_score}, intent={primary_intent}")
    return skill_id

async def main():
    test_msgs = [
        ("مريت بأسبوع صعب جداً الأسبوع الماضي. كانت الأمور مخيفة. أبي أشيك على نفسي اليوم وأشوف كيف أنا.", "original trigger"),
        ("أحس أحسن الحين، حبيت أتكلم معك بعد الأسبوع الصعب", "أحس أحسن"),
        ("أبي أشوف كيف أنت بعد قبل شوي", "keyword match"),
        ("كنت بحالة صعبة قبل شوي وأبي أشيك على نفسي", "check in after crisis"),
        ("مريت بأزمة الأسبوع الماضي وأحس أحسن الحين، أبي أتكلم", "crisis + احسن"),
        ("still here, wanted to check in after what happened", "English check in"),
        ("feeling safer now, wanted to check in", "feeling safer"),
        ("wanted to check in after earlier", "check in after earlier"),
        ("أبي أشيك على نفسي بعد اللي صار", "check in after what happened"),
    ]

    for msg, label in test_msgs:
        try:
            skill_id = await test_msg(msg, label)
        except Exception as e:
            print(f"[{label}] ERROR: {e}")

asyncio.run(main())
