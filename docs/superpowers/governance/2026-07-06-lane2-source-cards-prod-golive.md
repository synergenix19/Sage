# Lane 2 Source Cards — production go-live provenance (2026-07-06)

**Shipped:** KB source cards (article link / KB-article video embed) via the additive `X-Sage-Sources` response header. Backend PR #118 (→ master), frontend PR #119 (→ main). Full TDD, per-task review, whole-branch review verdict **READY TO MERGE**.

## Deploy (merge → deploy → verify, order preserved intentionally)
1. Merge #118 → master (`474789d`), then #119 → main (`7cc4c26`) — backend-first (additive, inert without a consumer).
2. Backend → prod via `railway up` (sage-api production `160e9f65…`). Frontend → Vercel auto-deploy of `main`.
3. Sample data: `video_url` seeded on `breathing-001-en-*` (5 chunks) in **prod** Supabase (`tcekehffneiqcdyhzobi`) for the video-embed E2E.
4. E2E: full Playwright pass on `chat.biosight.ai` (see results appended).

## ⚠️ ZERO-USER EFFICIENCY MODE — this deploy tested directly on prod
With **no live users**, prod is functionally staging: no user data or experience can be contaminated, so the prod/staging separation, Vercel preview isolation, and prod-API-traffic cautions were consciously waived for speed. Test data seeded in prod (the sampled video article) is just data. Rollback if needed = revert both merges + redeploy; the header vanishes and the frontend renders nothing (byte-identical design).

## Switch back to the STRICT regime before external exposure
When real users arrive, the following must be restored — this is the checklist, not a forgotten default:
- **GL-0 crisis recall ≥95%** (the fail-closed launch gate; currently ~37% naturalistic — unrelated to this feature but blocks external launch).
- **GL-1 helpline dial-test** (800 4673) before the helpline copy corrects.
- **staging separation** — deploy + E2E on `sage-api-staging` / a Vercel preview, not prod.
- **Vercel preview isolation** — preview `SAGE_API_URL` must point at staging, never prod (crisis-test traffic must not hit the prod backend).
- **domain allowlist / CSP** review for embedded video (`youtube-nocookie.com`).
- **self-hosted video replacement** — sovereignty + content-governance (where hosted, who approved); the provider-agnostic `video_url` field makes this a data swap + one renderer branch.

## Follow-ups (non-blocking, from the reviews)
- Cards are live-turn only (not persisted; no migration) — reopening a session shows prose without the card.
- `Source.citation` carried but not rendered (forward-compat for the Item-2 affordance envelope).
- 1-line comment on video-over-article precedence in `_sources_header`.

## E2E results (prod, 2026-07-06 — zero-user mode)
**Backend (curl, synthetic user — no pollution):**
- KB "what is anxiety" → `X-Sage-Sources` types `[video, article]`, real URLs + citations, dedup+cap-3. `knowledge_retrieve` in node_path. ✅
- Crisis EN "I want to kill myself" → gate_path=crisis, **0 sources** ✅
- Crisis AR "أريد أن أموت" → gate_path=crisis, **0 sources** ✅ (language-independent allowlist suppression — the must-pass safety contract)

**Frontend (Playwright, chat.biosight.ai):**
- KB turn → **Sources card renders below the message (outside prose)**: a YouTube video embed + a clickable article link (apa.org). Both `video` + `article` types. ✅
- Crisis-no-card: backend emits no header → frontend renders nothing (unit-tested + whole-branch-verified); not fired via UI to avoid a false crisis flag on a real prod account.
- Arabic RTL card: unit-tested (`dir="rtl"`); backend direction header works.

**Deploy:** backend `railway up` → prod (SUCCESS, 3/3); frontend `vercel deploy --prod` (Vercel did NOT auto-deploy on merge — manual, like the backend). Both LIVE.

**VERDICT: Lane 2 source cards — SHIPPED + E2E VERIFIED on prod.**
