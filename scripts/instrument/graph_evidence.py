"""Parity graph-invocation helper — the ONLY supported way to invoke the graph for evidence.

Implements rule 1 + 2 + 4 of the SIGNED instrument-parity standing rule
(docs/superpowers/governance/2026-07-28-instrument-parity-standing-rule.md):

  1. Flag derivation from the SERVING readback. Every SAGE_* var config.py reads
     (auto-derived by regex, same approach as
     scripts/bot_behaviour_audit/measure_layer1_fullgraph.py, so the NEXT flag to
     land is checked automatically) is resolved from the authed /health/version
     *_raw_env readback — the authoritative running state. Coverage semantics
     mirror the committed parity runner: a var the readback does not expose is
     resolved from railway (desired) when railway is available — railway is prod's
     only env source, so a var railway does not set runs the config default — and
     its coverage source is stamped so the readback hole stays VISIBLE in every
     artifact. A var reachable by NEITHER source is a READBACK GAP: the helper
     REFUSES (exit nonzero, explicit message) — a hard error, never a default.
     It likewise REFUSES on a deploy window (serving != desired on any parity
     var). If railway is unavailable, the deploy-window check cannot run: the
     helper states that loudly and proceeds readback-only (which also means any
     var the readback does not cover is then a hard gap).

  2. Provenance on the artifact. header_block()/write_artifact() stamp every
     artifact with: the full resolved flag set + per-var coverage source, the
     build SHA from the readback, classifier model + OpenRouter provider pin +
     requested seed + the seed-HONOR signal (classifier_system_fingerprint status
     — what came BACK, or null/unavailable, never fabricated), N per fixture, and
     the degraded-turn count (turns carrying the static-fallback signature:
     primary_intent == general_chat at confidence EXACTLY 0.5, the intent_route
     parse-failure default).

  4. Distributional rider (Node-2 bistability finding,
     2026-07-28-node2-intent-bistability-finding.md): run_fixture() drives a
     multi-turn session N times on N independent session threads and returns
     per-sample per-turn records — a distribution, never a single trajectory.

Local-instrument deviation (recorded, non-routing): SAGE_AUDIT_LOG is forced
"false" on export so a local evidence run never inserts rows into the prod
Supabase session-audit table (same deviation the 1a characterization instrument
recorded; AUDIT_LOG gates nothing on the routing path).

Usage:
  # parity probe only (no graph, no LLM): derive + print the header block
  uv run python scripts/instrument/graph_evidence.py probe [--base-url URL]

  # run one fixture N times through the LOCAL graph under the derived flag set
  uv run python scripts/instrument/graph_evidence.py run --fixture <case.json> \
      --n 10 --out <records.json> [--base-url URL]

Supersedes scripts/characterize_1a_gap.py (branch 1a-gap-phase0) as the
invocation path: that script exported a hand-pinned three-flag set; this one
derives the full set from the serving readback and refuses on gaps.
"""
import argparse
import asyncio
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import datetime, timezone


def _local_tree_sha(repo: str | None = None) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo or REPO, text=True,
            stderr=subprocess.DEVNULL).strip()
    except Exception:  # noqa: BLE001
        return "unknown"

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Default prod base URL — same source of truth as scripts/prod_smoke/run.py.
DEFAULT_BASE_URL = "https://sage-api-production-3328.up.railway.app"

# Infra/operational vars excluded from parity (same list as the committed runner:
# they configure pools/caches/credentials, not routing behaviour).
PARITY_INFRA_DENYLIST = {
    "SAGE_DB_POOL_MAX_SIZE", "SAGE_HTTP_MAX_CONNECTIONS", "SAGE_HTTP_MAX_KEEPALIVE",
    "SAGE_CHECKPOINT_POOL_MAX_SIZE", "SAGE_AUDIT_LOG", "SAGE_WARMUP_BGE",
    "SAGE_EMBED_CACHE_ENABLED", "SAGE_TEST_USER_IDS", "SAGE_API_KEY",
}

# Static-fallback signature (intent_route.py: data.get("primary_intent", "general_chat")
# + intent_confidence default 0.5 on classifier parse failure). A turn wearing this
# signature was NOT classified by the LLM — it is a degraded turn and every artifact
# must carry the count.
DEGRADED_INTENT = "general_chat"
DEGRADED_CONFIDENCE = 0.5

REQUIRED_HEADER_FIELDS = (
    "instrument", "generated_at", "base_url", "build_sha", "build_sha_source",
    "local_tree_sha", "resolved_flag_set", "flag_coverage", "classifier_model",
    "openrouter_provider_pin", "classifier_seed", "seed_honor",
    "n_per_fixture", "degraded_turn_count", "db_pool_available",
    "railway_desired_available", "deploy_window_checked", "parity_notes",
)

INSTRUMENT_ID = (
    "graph_evidence.py FULL-GRAPH app.ainvoke, N independent session threads per fixture; "
    "flags derived from /health/version serving readback (refuse-on-gap, refuse-on-deploy-window); "
    "signed instrument-parity standing rule 2026-07-28"
)


class ParityRefusal(RuntimeError):
    """The helper refuses to produce evidence. Callers exit nonzero."""


# ---------------------------------------------------------------------------
# Flag enumeration + readback mapping
# ---------------------------------------------------------------------------

def config_sage_vars(repo: str = REPO) -> dict:
    """Every SAGE_ env var config.py reads, mapped to its default literal (None when it
    has none). Scanned from source (same regex as measure_layer1_fullgraph.py) so a
    newly-added routing flag is auto-included — operator recall is never trusted.
    Matches both the raw os.getenv("SAGE_...") idiom and the single strict-flag parser
    _strict_flag("SAGE_...", default_on=...) (K2.1, src/sage_poc/config.py) so a flag
    migrated to the shared helper stays covered by the guard."""
    src = open(os.path.join(repo, "src/sage_poc/config.py"), encoding="utf-8").read()
    out = {}
    for m in re.finditer(
        r'os\.getenv\(\s*"(SAGE_[A-Z0-9_]+)"\s*(?:,\s*"([^"]*)")?'
        r'|_strict_flag\(\s*"(SAGE_[A-Z0-9_]+)"(?:\s*,\s*default_on\s*=\s*(True))?',
        src,
    ):
        if m.group(1):
            name, default = m.group(1), m.group(2)
        else:
            name, default = m.group(3), ("true" if m.group(4) else "false")
        if name not in PARITY_INFRA_DENYLIST:
            out[name] = default
    return out


def map_readback_to_sage(health: dict) -> dict:
    """/health/version *_raw_env fields -> {SAGE_VAR: raw value (may be None = unset
    in the serving env, i.e. prod runs the config default)}."""
    return {"SAGE_" + hk[: -len("_raw_env")].upper(): val
            for hk, val in health.items() if hk.endswith("_raw_env")}


# ---------------------------------------------------------------------------
# Network fetchers (never called from tests — tests inject fabricated payloads)
# ---------------------------------------------------------------------------

def _load_env_file(path: str) -> dict:
    """Minimal KEY=VALUE .env reader (no sage_poc import — config reads the
    environment at import time, and we must not import it before export_env)."""
    vals = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                vals[k.strip()] = v.strip()
    return vals


def resolve_api_key() -> str | None:
    """SAGE_API_KEY from the environment, else from <repo>/.env."""
    return os.getenv("SAGE_API_KEY") or _load_env_file(os.path.join(REPO, ".env")).get("SAGE_API_KEY")


def fetch_readback(base_url: str = DEFAULT_BASE_URL, api_key: str | None = None) -> dict:
    """Authed GET /health/version — the serving readback. Evidence REQUIRES it:
    unreachable readback is a refusal, not a fallback to inference."""
    api_key = api_key or resolve_api_key()
    if not api_key:
        raise ParityRefusal(
            "REFUSING: no SAGE_API_KEY (env or .env) — cannot read the authed "
            "/health/version serving readback, and evidence without readback-derived "
            "flags violates the signed instrument-parity rule.")
    try:
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl.create_default_context()  # never disable verification
        req = urllib.request.Request(
            base_url.rstrip("/") + "/health/version",
            headers={"X-Sage-Api-Key": api_key})
        return json.loads(urllib.request.urlopen(req, timeout=20, context=ctx).read())
    except Exception as e:  # noqa: BLE001
        raise ParityRefusal(
            f"REFUSING: /health/version readback unreachable at {base_url} "
            f"({type(e).__name__}: {str(e)[:200]}). The serving flag state is the only "
            "authoritative source; run cannot proceed without it.") from e


def fetch_railway_desired(service: str = "sage-api") -> dict | None:
    """Prod's DESIRED variable set via railway CLI (may lag serving mid-deploy).
    None when railway is unavailable (headless/CI) — the caller states that loudly."""
    rw_env = {**os.environ, "RAILWAY_CALLER": "instrument:graph_evidence"}
    for cmd in (["railway", "variables", "--json", "-s", service],
                ["railway", "variables", "--json"]):
        try:
            raw = subprocess.check_output(cmd, text=True, timeout=45, env=rw_env,
                                          stderr=subprocess.DEVNULL)
            return json.loads(raw)
        except Exception:  # noqa: BLE001
            continue
    return None


# ---------------------------------------------------------------------------
# Derivation: refuse-on-gap + refuse-on-deploy-window
# ---------------------------------------------------------------------------

def derive_flag_set(readback_health: dict, desired: dict | None,
                    mapping: dict | None = None,
                    allow_deploy_window: bool = False) -> dict:
    """Derive the full flag set from the serving readback (+ railway desired).

    Returns {"resolved_env": {var: str|None}, "effective": {var: str|None},
             "coverage": {var: source}, "railway_desired_available": bool,
             "deploy_window_checked": bool, "notes": [str, ...]}

    resolved_env value None == prod does not set the var (local env must UNSET it so
    config.py resolves its own default — never default it in by hand).
    effective == the value config.py will actually resolve (raw value or default
    literal), for the artifact header.

    Raises ParityRefusal on (a) any config var covered by neither the readback nor
    railway — the standing rule's hard error — and (b) a deploy window (serving !=
    desired on any parity var).
    """
    mapping = mapping if mapping is not None else config_sage_vars()
    serving = map_readback_to_sage(readback_health)
    notes: list = []
    resolved, effective, coverage, gaps = {}, {}, {}, []

    for var, default in sorted(mapping.items()):
        if var in serving:
            raw = serving[var]
            resolved[var] = raw
            effective[var] = raw if raw is not None else default
            coverage[var] = "serving_readback"
        elif desired is not None:
            if var in desired and desired[var] is not None:
                resolved[var] = desired[var]
                effective[var] = desired[var]
                coverage[var] = "railway_desired"
            else:
                # railway IS prod's only env source; a var it does not set runs the default
                resolved[var] = None
                effective[var] = default
                coverage[var] = "railway_default"
        else:
            gaps.append(var)

    if gaps:
        raise ParityRefusal(
            "REFUSING (readback gap = hard error, signed instrument-parity rule 1): "
            f"{len(gaps)} config.py flag(s) covered by NEITHER the /health/version "
            f"serving readback nor railway (desired): {', '.join(gaps)}. "
            "Fix: widen the /health/version *_raw_env readback to cover them (rule 3 "
            "pattern), or provide railway access so desired-state coverage can assert them. "
            "The helper never resolves an unasserted flag to a default.")

    if desired is None:
        notes.append(
            "LOUD: railway (desired) UNAVAILABLE — deploy-window check (serving vs "
            "desired) could NOT run; proceeding READBACK-ONLY. Every var above is "
            "asserted from the serving readback alone.")
        deploy_window_checked = False
    else:
        # Deploy-window detector: for every readback-covered var, serving-resolved vs
        # desired-resolved (desired value, else config default — railway is the sole
        # env source). Divergence == prod is transitioning; a run now measures a
        # system whose number is stale on arrival.
        window = []
        for var in sorted(mapping):
            if var not in serving:
                continue
            srv = serving[var] if serving[var] is not None else mapping[var]
            des = desired.get(var) if desired.get(var) is not None else mapping[var]
            if srv != des:
                window.append((var, srv, des))
        if window:
            lines = "; ".join(f"{v}: serving={s!r} desired={d!r}" for v, s, d in window)
            if not allow_deploy_window:
                raise ParityRefusal(
                    f"REFUSING (deploy window): serving flags differ from desired (railway) — "
                    f"prod is mid-transition and evidence taken now is stale on arrival: {lines}. "
                    "Re-run once prod has quiesced (serving == desired).")
            # Loud override (smoke/diagnostic use only — never an evidence baseline).
            # Resolution stays SERVING-authoritative; the divergence is stamped so the
            # artifact is distinguishable at read time (standing rule 2).
            notes.append(
                f"LOUD: DEPLOY WINDOW OVERRIDDEN (--allow-deploy-window) — serving != "
                f"desired: {lines}. Output is NOT citable as a quiesced-prod baseline.")
        deploy_window_checked = True

    readback_holes = [v for v, src in coverage.items() if src != "serving_readback"]
    if readback_holes:
        notes.append(
            f"readback coverage hole ({len(readback_holes)} var(s) asserted via railway, "
            f"not the serving readback): {', '.join(sorted(readback_holes))} — widen "
            "/health/version *_raw_env to close (standing-rule 3 pattern).")

    return {
        "resolved_env": resolved,
        "effective": effective,
        "coverage": coverage,
        "railway_desired_available": desired is not None,
        "deploy_window_checked": deploy_window_checked,
        "notes": notes,
    }


def export_env(derived: dict, env_file: str | None = None) -> None:
    """Mirror the derived flag set into THIS process's environment. MUST run before
    any sage_poc import — config.py reads the environment at import time.

    .env re-injection guard: config.py calls load_dotenv() at import, which SETS any
    var we just popped if the repo .env defines it — silently defeating "unset means
    prod default". A .env SAGE_ parity var that differs from the derived effective
    value is therefore a REFUSAL; an equal one is a benign note."""
    env_file = env_file if env_file is not None else os.path.join(REPO, ".env")
    envf = _load_env_file(env_file)
    conflicts = []
    for var, val in derived["resolved_env"].items():
        if val is None and var in envf:
            effective = derived["effective"].get(var)
            if envf[var] != (effective if effective is not None else ""):
                conflicts.append((var, envf[var], effective))
            else:
                derived["notes"].append(
                    f"note: .env sets {var}={envf[var]!r} (load_dotenv re-injects it after "
                    "unset) — equal to the derived effective value, so parity holds.")
    if conflicts:
        lines = "; ".join(f"{v}: .env={e!r} derived-effective={d!r}" for v, e, d in conflicts)
        raise ParityRefusal(
            "REFUSING (.env re-injection): config.py load_dotenv() would re-inject "
            f"SAGE_ var(s) the derivation says must be UNSET (prod runs the default), with "
            f"values that DIFFER from the derived effective state: {lines}. Remove or align "
            f"them in {env_file} before producing evidence.")
    for var, val in derived["resolved_env"].items():
        if val is None:
            os.environ.pop(var, None)  # prod runs the default -> so must we
        else:
            os.environ[var] = val
    # Local-instrument deviation (recorded, non-routing): never write session-audit
    # rows into prod Supabase from a local evidence run.
    os.environ["SAGE_AUDIT_LOG"] = "false"


def build_local_graph(warm: bool = True):
    """Import + build the LOCAL graph under the exported flag set. Import happens
    HERE, after export_env, by design."""
    from langgraph.checkpoint.memory import MemorySaver
    from sage_poc.graph import build_graph
    app = build_graph(MemorySaver())
    if warm:
        # Instrument fidelity (same as the committed runner): prod warms BGE-M3 at
        # startup; warm here so every turn is measured with the layers prod serves.
        import sage_poc.nodes.skill_select as _ss
        _ss._ensure_semantic_ready()
        try:
            from sage_poc.safety import s3_semantic as _s3
            _s3._ensure_s3_ready()
        except Exception as e:  # noqa: BLE001
            print(f"(s3 warm note: {str(e)[:100]})", flush=True)
    return app


async def invoke_turn(app, state_in: dict, thread_id: str) -> dict:
    """Single-turn graph invocation, given a FULLY-CONSTRUCTED state dict and a thread_id.

    `thread_id` is REQUIRED, not optional: `build_local_graph()` always compiles the graph
    WITH a checkpointer (MemorySaver, mirroring the committed layer1 runner's own
    `build_graph(MemorySaver())` pattern), and LangGraph raises `ValueError: "Checkpointer
    requires one or more of the following 'configurable' keys: thread_id, ..."` on ANY
    `ainvoke()` call that omits `config={'configurable': {'thread_id': ...}}` when a
    checkpointer is present -- structurally, before any node runs, independent of what the
    caller's own state-carry strategy is. This function's first version omitted `config`
    entirely (Task 9 fix-round-3 incident: a live run crashed on its very first invocation --
    the amendment-8 smoke case runs before any of the 196 corpus rows -- with zero rows
    driven and no output doc written). Mirrors measure_layer1_fullgraph.py's own
    `drive(app, msg, tid)` (`config={"configurable": {"thread_id": tid}}`) -- the established,
    working convention this codebase's OTHER checkpointer-backed driver already uses; not a
    new pattern invented here.

    The caller owns state construction (e.g. make_e2e_state/carry_state, or hand-built
    overrides) -- this function's only job is the actual `app.ainvoke(...)` call, kept here
    per the instrument-parity standing rule (rule 1, 2026-07-28): every graph invocation whose
    output feeds a decision/memo/matrix-row/escalation goes through this file, never
    re-implemented at the call site (test_instrument_helper_only.py enforces this by static
    scan). Added for Task 9's psychoed flip-tier runner (scripts/bot_behaviour_audit/
    measure_psychoed_families.py), which needs per-turn `state_overrides` and manual
    turn-to-turn carry (test_psychoed_fixtures_ci.py's own `_carry` pattern) rather than
    run_fixture()'s flat-message-list/N-sample shape below -- generic, not psychoed-specific,
    so any future instrument needing single-turn control can reuse it instead of re-deriving
    a direct ainvoke() call."""
    return await app.ainvoke(state_in, config={"configurable": {"thread_id": thread_id}})


async def attach_db_pool():
    """Serving-parity DB pool for the KB path. knowledge_retrieve resolves its pool
    from server.app.state._db_pool — created only by the FastAPI lifespan, which a
    direct-graph evidence run never executes, so the KB path silently abstains on
    every turn (the 2026-07-29 shakedown's DB-absent caveat). Replicate the serving
    pool exactly as server.py's lifespan builds it and attach it where _get_pool()
    looks. Import happens here, after export_env, by design (same rule as
    build_local_graph). Returns the pool, or None (DATABASE_URL unset / connect
    failure) — the CALLER decides whether absence is a refusal (full baselines) or
    a stamped degradation (smokes)."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_url = _load_env_file(os.path.join(REPO, ".env")).get("DATABASE_URL")
        if db_url:
            os.environ["DATABASE_URL"] = db_url
    if not db_url:
        print("(db pool: DATABASE_URL not set — KB path will abstain)", flush=True)
        return None
    try:
        import asyncpg  # noqa: PLC0415
        # server.py lives at the repo ROOT (uvicorn's cwd in prod); the instrument only
        # puts src/ on sys.path. Root must be importable or knowledge_retrieve's own
        # `from server import app` fails the same way inside the graph.
        if REPO not in sys.path:
            sys.path.insert(0, REPO)
        import server as _server  # noqa: PLC0415  (module import only; lifespan NOT run)
        from sage_poc.config import DB_POOL_MAX_SIZE  # noqa: PLC0415
        pool = await asyncpg.create_pool(
            db_url, min_size=1, max_size=DB_POOL_MAX_SIZE,
            max_inactive_connection_lifetime=300)  # mirror server.py verbatim
        _server.app.state._db_pool = pool
        return pool
    except Exception as e:  # noqa: BLE001
        print(f"(db pool attach FAILED: {str(e)[:150]} — KB path will abstain)", flush=True)
        return None


# ---------------------------------------------------------------------------
# N-sample driver (bistability rider)
# ---------------------------------------------------------------------------

def is_degraded(primary_intent, confidence) -> bool:
    """Static-fallback signature: general_chat at confidence EXACTLY 0.5."""
    return primary_intent == DEGRADED_INTENT and confidence == DEGRADED_CONFIDENCE


def _record(turn_no: int, user_msg: str, state: dict) -> dict:
    rec = {
        "turn": turn_no,
        "user_message": user_msg,
        "primary_intent": state.get("primary_intent"),
        "secondary_intent": state.get("secondary_intent"),
        "confidence": state.get("intent_confidence"),
        "path": state.get("path") or [],
        "offered_skill_ids": state.get("offered_skill_ids"),
        "active_skill_id": state.get("active_skill_id"),
        "completed_skill_id": state.get("completed_skill_id"),
        "skill_match_method": state.get("skill_match_method"),
        "classifier_system_fingerprint": state.get("classifier_system_fingerprint"),
    }
    rec["degraded"] = is_degraded(rec["primary_intent"], rec["confidence"])
    return rec


def _prod_turn_state(msg: str, thread_id: str) -> dict:
    """SERVING-PARITY per-turn input: the REAL server_helpers._build_state — the same
    function prod calls on every /chat turn — via a minimal request shim, so the
    instrument's per-turn resets can NEVER drift from serving's (single-source).

    Incident this closes (2026-08-12, screen-completion family): run_fixture passed
    only {raw_message, path} per turn, none of _build_state's ~30 per-turn resets;
    prod resets screen_question_text every turn, the instrument did not, and the
    stale turn-1 screen text routed the answer turn back to screen_response, which
    nulled the freshly made offer — behavior that CANNOT occur in serving. Import is
    deferred (after export_env, same rule as build_local_graph)."""
    from sage_poc.server_helpers import _build_state  # noqa: PLC0415

    class _Msg:  # noqa: N801
        role = "user"
        content = msg

    class _Req:  # noqa: N801
        messages = [_Msg]
        session_id = thread_id
        user_id = None

    return _build_state(_Req)


async def run_fixture(app, session_turns: list, n: int,
                      thread_prefix: str = "evidence") -> dict:
    """Drive a multi-turn session N times, each on an INDEPENDENT session thread
    (fresh checkpoint state), and return the distribution of per-turn records."""
    samples = []
    degraded = 0
    for s in range(n):
        tid = f"{thread_prefix}-s{s}-{uuid.uuid4().hex[:8]}"
        records = []
        for i, msg in enumerate(session_turns, start=1):
            state = await app.ainvoke(
                _prod_turn_state(msg, tid),
                config={"configurable": {"thread_id": tid}})
            rec = _record(i, msg, state)
            degraded += int(rec["degraded"])
            records.append(rec)
        samples.append({"sample": s, "thread_id": tid, "records": records})
    return {"n": n, "turns": len(session_turns), "samples": samples,
            "degraded_turn_count": degraded}


def collect_fingerprints(fixture_result: dict) -> list:
    """Per-turn classifier_system_fingerprint values, in run order (None preserved —
    an absent echo is data, never fabricated)."""
    return [rec.get("classifier_system_fingerprint")
            for sample in fixture_result["samples"] for rec in sample["records"]]


# ---------------------------------------------------------------------------
# Artifact header (standing rule 2: the artifact carries its provenance)
# ---------------------------------------------------------------------------

def _seed_honor(effective: dict, fingerprints) -> dict:
    prov_on = (effective.get("SAGE_AUDIT_CLASSIFIER_PROVENANCE") or "false").lower() == "true"
    if not prov_on:
        return {"status": "unavailable_provenance_flag_off",
                "detail": "SAGE_AUDIT_CLASSIFIER_PROVENANCE resolves false — the "
                          "classifier_system_fingerprint state channel is not written; "
                          "seed honor CANNOT be asserted for this run",
                "distinct_fingerprints": []}
    fps = list(fingerprints or [])
    distinct = sorted({f for f in fps if f})
    if not fps:
        status = "no_classifier_turns_recorded"
    elif not distinct:
        status = "fingerprint_absent_provider_did_not_echo"
    elif len(distinct) == 1:
        status = "fingerprint_stable"
    else:
        status = "fingerprint_varied_backend_mix"
    return {"status": status, "distinct_fingerprints": distinct,
            "turns_with_fingerprint": sum(1 for f in fps if f), "turns_total": len(fps)}


def header_block(derived: dict, readback_health: dict, *, n_per_fixture: int,
                 degraded_turn_count: int, fingerprints=None,
                 base_url: str = DEFAULT_BASE_URL,
                 db_pool_available: bool = False) -> dict:
    eff = derived["effective"]
    local_sha = _local_tree_sha()
    serving_sha = readback_health.get("build_sha", "unknown")
    header = {
        "instrument": INSTRUMENT_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "base_url": base_url,
        "build_sha": serving_sha,
        "build_sha_source": readback_health.get("build_sha_source", "unknown"),
        # The LOCAL tree the graph was actually built from. Flags come from the
        # serving readback; the CODE is this tree — when they differ the artifact
        # must say so or it wears the serving SHA's name on another tree's number.
        "local_tree_sha": local_sha,
        "resolved_flag_set": dict(sorted(eff.items())),
        "flag_coverage": dict(sorted(derived["coverage"].items())),
        "classifier_model": eff.get("SAGE_CLASSIFIER_MODEL"),
        "openrouter_provider_pin": eff.get("SAGE_OPENROUTER_PROVIDER_PIN") or None,
        "classifier_seed": eff.get("SAGE_CLASSIFIER_SEED") or None,
        "seed_honor": _seed_honor(eff, fingerprints),
        "n_per_fixture": n_per_fixture,
        "degraded_turn_count": degraded_turn_count,
        # Run-environment DB parity (2026-07-30 close-read gap): serving always has the
        # KB pool; a direct-graph run has it ONLY when attach_db_pool() succeeded. False
        # means every KB-path turn abstained — a different graph than prod serves.
        "db_pool_available": bool(db_pool_available),
        "railway_desired_available": derived["railway_desired_available"],
        "deploy_window_checked": derived["deploy_window_checked"],
        "parity_notes": list(derived["notes"]),
    }
    if not db_pool_available:
        header["parity_notes"].append(
            "DB POOL ABSENT: knowledge_retrieve abstained on every KB-path turn — the "
            "run is NOT DB-parity with serving; not citable as a baseline-of-record "
            "(2026-07-30 close-read ruling).")
    if local_sha not in ("unknown",) and serving_sha not in ("unknown",) \
            and not serving_sha.startswith(local_sha) and not local_sha.startswith(serving_sha):
        header["parity_notes"].append(
            f"NOTE: LOCAL tree {local_sha[:12]} != SERVING build {serving_sha[:12]} — "
            "flags are serving-derived but the code under measurement is the local tree; "
            "cite accordingly.")
    missing = [f for f in REQUIRED_HEADER_FIELDS if f not in header]
    if missing:  # defensive: the template is load-bearing for every future artifact
        raise ParityRefusal(f"header template incomplete, missing: {missing}")
    return header


def render_header_md(header: dict) -> str:
    lines = [
        "<!-- instrument-parity header block (signed standing rule 2026-07-28) — template artifact -->",
        "",
        "## Provenance (instrument-parity header block)",
        "",
        f"- **Instrument:** {header['instrument']}",
        f"- **Generated at:** {header['generated_at']}",
        f"- **Serving readback:** {header['base_url']} /health/version",
        f"- **Build SHA (from readback):** `{header['build_sha']}` (source: {header['build_sha_source']})",
        f"- **Local tree SHA (code measured):** `{header['local_tree_sha']}`",
        f"- **Classifier model:** `{header['classifier_model']}`",
        f"- **OpenRouter provider pin:** `{header['openrouter_provider_pin']}`",
        f"- **Requested classifier seed:** `{header['classifier_seed']}`",
        f"- **Seed-honor signal (system_fingerprint):** `{header['seed_honor']['status']}`"
        + (f" — distinct: {header['seed_honor']['distinct_fingerprints']}"
           if header['seed_honor'].get('distinct_fingerprints') else ""),
        f"- **N per fixture:** {header['n_per_fixture']}",
        f"- **Degraded turns (static-fallback signature general_chat@0.5):** {header['degraded_turn_count']}",
        f"- **DB pool (KB-path serving parity):** {'AVAILABLE' if header['db_pool_available'] else 'ABSENT — KB path abstained'}",
        f"- **Railway (desired) available:** {header['railway_desired_available']}"
        f" | **deploy-window checked:** {header['deploy_window_checked']}",
    ]
    for note in header["parity_notes"]:
        lines.append(f"- **Parity note:** {note}")
    lines += ["", "### Resolved flag set (full, with coverage source)", "",
              "| var | effective value | coverage |", "|---|---|---|"]
    for var, val in header["resolved_flag_set"].items():
        lines.append(f"| `{var}` | `{val}` | {header['flag_coverage'].get(var, '?')} |")
    lines.append("")
    return "\n".join(lines)


def write_artifact(path: str, header: dict, body_md: str, title: str | None = None) -> None:
    """EVERY artifact this instrument writes goes through here: header first, body
    after — a non-parity artifact must be distinguishable at read time."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    parts = []
    if title:
        parts.append(f"# {title}\n")
    parts.append(render_header_md(header))
    parts.append(body_md)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def prepare_evidence_env(base_url: str = DEFAULT_BASE_URL,
                         railway_service: str = "sage-api",
                         allow_deploy_window: bool = False,
                         flag_overrides: dict | None = None) -> tuple:
    """The one-call setup: readback -> railway -> derive (refusals raise) -> export.
    Returns (derived, readback_health).

    flag_overrides (Phase-3 fix-arm measurement, 2026-08-12): DELIBERATE per-flag
    deltas applied AFTER serving-parity export, for measuring dark code with its flag
    ON while everything else stays serving-derived. Every override is stamped into the
    resolved set (coverage source "deliberate_override"), and a LOUD parity note names
    each one — the artifact is a counterfactual measurement arm and must never read as
    a serving-parity baseline. Empty/None = byte-identical to before."""
    readback = fetch_readback(base_url)
    desired = fetch_railway_desired(railway_service)
    if desired is None:
        print("LOUD: railway (desired) unavailable — proceeding readback-only; "
              "deploy-window check skipped.", flush=True)
    derived = derive_flag_set(readback, desired, allow_deploy_window=allow_deploy_window)
    for var, val in (flag_overrides or {}).items():
        # BOTH maps, or the header lies about the run (2026-08-12 first-arm incident:
        # effective/coverage said true, resolved_env — the map export_env actually
        # exports — kept the var unset, and the artifact's flag table diverged from
        # the process env; caught by the zero-marker readout, now self-checked below).
        derived["effective"][var] = val
        derived["resolved_env"][var] = val
        derived["coverage"][var] = "deliberate_override"
        derived["notes"].append(
            f"DELIBERATE FLAG OVERRIDE (fix-arm measurement): {var}={val!r} — serving "
            f"carries a different value; this run is a COUNTERFACTUAL arm, not a "
            f"serving-parity baseline. Cite only against its paired baseline.")
    for note in derived["notes"]:
        print(note, flush=True)
    export_env(derived)
    for var, val in (flag_overrides or {}).items():
        if os.environ.get(var) != val:
            raise ParityRefusal(
                f"REFUSING: override {var}={val!r} did not reach the process env "
                f"(got {os.environ.get(var)!r}) — the artifact would claim a flag "
                "state the run does not have.")
    return derived, readback


async def _run_cli(args) -> int:
    derived, readback = prepare_evidence_env(args.base_url, args.railway_service,
                                             args.allow_deploy_window)
    fixture = json.load(open(args.fixture, encoding="utf-8"))
    turns = fixture["turns"] if isinstance(fixture, dict) else list(fixture)
    app = build_local_graph()
    t0 = time.time()
    result = await run_fixture(app, turns, args.n, thread_prefix=f"ge-{readback.get('build_sha', 'x')[:7]}")
    header = header_block(derived, readback, n_per_fixture=args.n,
                          degraded_turn_count=result["degraded_turn_count"],
                          fingerprints=collect_fingerprints(result),
                          base_url=args.base_url)
    out = {"header": header, "fixture": args.fixture, "result": result,
           "elapsed_s": round(time.time() - t0, 1)}
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False, default=str)
        print(f"records written: {args.out}")
    else:
        print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_probe = sub.add_parser("probe", help="derive + print the header block (no graph, no LLM)")
    p_run = sub.add_parser("run", help="run one fixture N times through the local graph")
    for p in (p_probe, p_run):
        p.add_argument("--base-url", default=os.getenv("SAGE_PROD_HEALTH_URL", DEFAULT_BASE_URL))
        p.add_argument("--railway-service", default="sage-api")
        p.add_argument("--allow-deploy-window", action="store_true",
                       help="SMOKE/DIAGNOSTIC ONLY: proceed although serving != desired; "
                            "the divergence is stamped loudly and the output is not a baseline")
    p_run.add_argument("--fixture", required=True,
                       help='JSON file: {"turns": [...]} or a bare JSON list of turns')
    p_run.add_argument("--n", type=int, default=10)
    p_run.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    try:
        if args.cmd == "probe":
            derived, readback = prepare_evidence_env(args.base_url, args.railway_service,
                                                     args.allow_deploy_window)
            header = header_block(derived, readback, n_per_fixture=0,
                                  degraded_turn_count=0, fingerprints=[],
                                  base_url=args.base_url)
            print(json.dumps(header, indent=2, ensure_ascii=False))
            return 0
        return asyncio.run(_run_cli(args))
    except ParityRefusal as e:
        print(str(e), file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
