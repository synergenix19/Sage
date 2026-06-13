import asyncio, os, json, uuid
from dotenv import load_dotenv
load_dotenv()

async def test():
    try:
        from sage_poc.graph import build_graph
        from sage_poc.server_helpers import _build_state, _RequestLike, _MessageLike

        graph = build_graph(checkpointer=None)

        session_id = str(uuid.uuid4())

        req = _RequestLike(
            messages=[_MessageLike(role='user', content='مريت بأسبوع صعب جداً الأسبوع الماضي. كانت الأمور مخيفة. أبي أشيك على نفسي اليوم وأشوف كيف أنا.')],
            session_id=session_id
        )
        state = _build_state(req)
        state['therapeutic_profile'] = None

        config = {'configurable': {'thread_id': session_id}}
        print('Invoking graph...')

        result = await asyncio.wait_for(
            graph.ainvoke(state, config=config),
            timeout=60
        )

        print('SUCCESS!')
        print('active_skill_id:', result.get('active_skill_id'))
        print('executed_step_id:', result.get('executed_step_id'))
        print('path:', result.get('path'))
        print('response[:300]:', str(result.get('response', ''))[:300])

    except asyncio.TimeoutError:
        print('TIMEOUT after 60s')
    except Exception as e:
        print('ERROR:', type(e).__name__, str(e))
        import traceback
        traceback.print_exc()

asyncio.run(test())
