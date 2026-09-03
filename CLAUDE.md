# e2m-project — orientation for Claude Code

**Read `SESSION_HANDOVER.md` in full before doing anything else in this repo.** It has the current status, what's done vs. not, exact setup commands, and a running list of bugs already found and fixed — skipping it means re-deriving context that's already written down.

## The essentials, right now

- `main` is current and has everything (Phases 1–4, plus a slice of Phase 5). No branch switching needed.
- `uv sync && uv run pytest backend/tests/ -v` → expect **62 passed**.
- `uv run uvicorn backend.api.main:app --reload --port 8000` (backend API) + `cd frontend && npm install && npm run dev` → `http://localhost:3000` (frontend), run together.
- **Check for a GPU before assuming SAM 3 / neural rendering works**: `uv run python -c "import torch; print(torch.cuda.is_available())"`. If `False`, `backend/demo_segment.py` and neural `backend/demo_render.py` will hard-fail (not just run slowly) — the vendored `../sam3` package hardcodes `device="cuda"`. Use `demo_render.py --preview` (CPU, <50ms) instead when there's no GPU.
- Phase 5's `POST /api/boq` and `POST /api/render/preview` are done and wired to the frontend (both pure-CPU). `POST /api/segment` and `POST /api/render/neural` (GPU-only) plus Celery/WeasyPrint/DB are still not started — `SESSION_HANDOVER.md` §9 has the current status and recommended order.

## Don't re-break these

- Don't add `EXECUTION_GUIDE.md`, `IMPLEMENTATION_PLAN.md`, a bare `samples` line, `backend/demo_segment.py`, or `backend/tests/test_segmentation.py` to `.gitignore` — that exact mistake silently dropped real deliverables from version control for most of this project's history (see `SESSION_HANDOVER.md` §4).
- The frontend's sample data (`frontend/src/data/sampleHouse1.ts`, `frontend/public/samples/*.jpg`) is derived from a **real** `backend/demo_segment.py` / `demo_render.py --preview` run, not invented mock data. Keep it that way — see `SESSION_HANDOVER.md` §6 for how to regenerate or extend it.
- After any frontend change to the wizard flow, verify by actually driving it in a browser (Playwright / `chromium-cli`), not just `npm run build`. Type-checking has already let real bugs through once this project (see `SESSION_HANDOVER.md` §5).
