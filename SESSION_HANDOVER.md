# Complete Session Handover & Architecture Context
### AI-Based Exterior House Renovation & Cost Estimation System

> **Document purpose**: Zero-context-loss record of everything done, decided, and broken/fixed, so a fresh Claude Code session (or you) can resume on another PC with no re-discovery work. Rewritten 2026-09-03 after Phase 4 (frontend) + a full git/branch cleanup. If you're a Claude session reading this cold: read this whole file before touching anything, then skip straight to §9 "What Remains" — that's the actual next task.

---

## 0. TL;DR — start here

- **Everything is committed and pushed.** `main` on `origin` (`https://github.com/poojan-solanki/e2m-interview`) has all of Phase 1–4. Working tree is clean. `git branch -vv` to confirm.
- **Phases 1, 2, 3, 4 are done and tested.** Phase 5 (FastAPI integration) has not been started — that's the next task.
- **This session ran on a machine with no NVIDIA GPU.** SAM 3 segmentation and neural ControlNet rendering were never actually executed here — they *cannot* run without CUDA (see §2). If you're now on the RTX 3050 machine, that's the first thing to verify still works, since it's genuinely untested since the Phase 3 commit.
- **First commands to run on a fresh checkout:**
  ```bash
  uv sync
  uv run pytest backend/tests/ -v          # expect 55 passed
  cd frontend && npm install && npm run dev  # http://localhost:3000
  ```
- **Don't re-add these `.gitignore` lines** — they silently deleted real deliverables from version control for most of this project's history and were removed in commit `be47c51`: `EXECUTION_GUIDE.md`, `IMPLEMENTATION_PLAN.md`, a bare `samples` line, `backend/demo_segment.py`, `backend/tests/test_segmentation.py`. See §4.

---

## 1. Executive Summary & Current Status

* **Branches** (all pushed to `origin`, all currently identical except the two genuine historical checkpoints):
  * `phase-1/calculation-engine` — genuine checkpoint, frozen at end of Phase 1.
  * `phase-2/segmentation` — genuine checkpoint, frozen at end of Phase 2.
  * `phase-3/renderer`, `phase-4/frontend`, `phase-5/integration`, `main` — all point at the same latest commit (`f664c47` as of this writing). `phase-4/frontend` and `phase-5/integration` used to be stale (frozen at the very first commit since project init and never advanced) — they're fixed now, see §4.
* **Tests**: `uv run pytest backend/tests/ -v` → **55/55 passed** in ~6–15s (Python backend only; the frontend has no test suite yet, verified manually via a scripted browser walkthrough instead — see §6).
* **Hardware target**: built for a 4 GB VRAM NVIDIA RTX 3050 laptop. Peak VRAM should stay under ~2.5 GB when it runs on that hardware.
* **What a fresh clone gets you**: full backend (calc engine, SAM 3 segmentation, ControlNet+SD renderer, CPU instant-preview tier) and a working Next.js frontend wired to *real* backend-derived data — not mocks pretending to be real.

---

## 2. CRITICAL: GPU vs. non-GPU environment

This matters more than it sounds like. Two very different classes of machine will run this repo:

| Capability | Needs GPU? | Status this session (no-GPU machine) |
|---|---|---|
| Phase 1 calc engine (`demo_calculate.py`, BoQ math) | No | Fully verified |
| Phase 2 SAM 3 segmentation (`demo_segment.py`) | **Yes — hard requirement** | **Could not run at all**, not even slowly. See below. |
| Phase 3 Tier-1 instant preview (`demo_render.py --preview`) | No (CPU, <50ms) | Fully verified, used to generate real frontend sample data |
| Phase 3 Tier-2 neural render (`demo_render.py` without `--preview`, i.e. SD+ControlNet) | **Yes — hard requirement** | Could not run |
| Phase 4 frontend (Next.js) | No | Fully verified live in a browser |

**Why SAM 3 segmentation hard-fails without a GPU**: it's not just slow on CPU — `sam3/model_builder.py`'s `_create_position_encoding()` calls `torch.zeros(..., device="cuda")` unconditionally (in the vendored `../sam3` repo, not this project's own code), so model loading itself throws `RuntimeError: Found no NVIDIA driver` before any inference happens. If you want CPU-only segmentation to actually work, that's an upstream `sam3` patch, not something fixable in this repo alone. Don't waste time trying `--device cpu` flags on `demo_segment.py`; there's no such flag and it wouldn't matter if there were.

**Practical consequence for this session's frontend work**: I couldn't generate a *new* segmentation. Instead the frontend's sample data reuses the one real segmentation result that already existed in the repo — see §6.

**First thing to do on the GPU machine**: confirm the untested-since-Phase-3 stuff still works —
```bash
uv run python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
uv run python backend/demo_segment.py --image samples/image.png --output output/
uv run python backend/demo_render.py --image samples/image.png --material stone_cladding --steps 20
```

---

## 3. Work Accomplished by Phase

### Phase 1: Core Calculation Engine (`backend/engine/`)
- **Materials catalog** (`materials_catalog.py`): 7 materials (`weatherproof_paint`, `textured_stucco`, `stone_cladding`, `vitrified_tiles`, `wpc_panels`, `glass_railing`, `metal_railing`), Ahmedabad/Gujarat INR rates (₹25–₹220/sqft material, ₹12–₹65/sqft labor), wastage 5–15%.
- **Metrology** (`area_estimator.py`): 3-tier calibration (reference door 2.1m → EXIF pinhole cross-check → manual 2-point ruler), shoelace polygon area, IS 1200 opening-deduction rule.
- **BoQ calculator** (`boq_calculator.py`): the canonical cost formula — **material cost is charged on wastage-inflated gross area; labor cost is charged on net (as-installed) area**. This asymmetry is easy to get wrong when porting the logic elsewhere (I ported it to TypeScript in Phase 4 and verified it against this exact rule).
- **Report generator** (`report_generator.py`): ASCII/JSON/HTML output.

### Phase 2: SAM 3 Segmentation (`backend/segmentation/`)
- Zero-shot architectural concept prompting via Meta SAM 3 (`"exterior wall"`, `"window"`, `"balcony"`, `"porch column"`, `"roof overhang"`, plus `"building facade"` added this session — see below).
- Car/person foreground exclusion, car-window subtraction, closed-polygon contours.
- Strict 2-pass mask hierarchy (`zone_exporter.py`): union renovatable surfaces, then subtract protected openings with a 2px dilation guard — walls can never overwrite window glass.
- **This session's fix**: `segmenter.py` now unions `"exterior wall"` OR `"building facade"` into the wall mask (previously only `"exterior wall"`), so raw/unfinished masonry or commercial facades get detected as walls too, not just painted finished walls. Also fixed a loop bug (`for prompt in eval_order` → `for prompt in prompt_outputs`) that could silently skip prompt outputs.

### Phase 3: AI Rendering (`backend/renderer/`)
- **Neural path** (`inpainter.py`): `StableDiffusionControlNetInpaintPipeline` (SD 1.5 inpainting + ControlNet Canny) in fp16, `DPMSolverMultistepScheduler(use_karras_sigmas=True)`, ControlNet scale 0.5–0.65, model CPU offload + attention slicing (~2.4 GB VRAM).
- **This session's optimization suite** (`PHASE_3_OPTIMIZATION_TESTING_GUIDE.md` has full detail):
  - **New: Tier-1 instant CPU preview** (`instant_preview.py`) — procedural material synthesis with LAB luminance transfer against real shadows/daylight, same 100% pixel-lock guarantee, **sub-50ms, zero GPU/VRAM**. This is what made real, working frontend sample data possible without a GPU.
  - `inpainter.py`: VAE tiling/slicing, TF32 on Ampere+, CUDA cache cleanup, a `fast_mode` (15 steps) path.
  - `demo_render.py`: new `--preview` (Tier-1) and `--fast` (Tier-2, 15-step) CLI flags.
- **100% pixel-lock**: post-diffusion, `result = np.where(mask > 128, generated, original)` — windows/doors/cars/sky are always bit-identical to the source photo.
- **Auto-pipeline**: `demo_render.py` auto-runs segmentation if no matching mask exists for the given image's resolution.

### Phase 4: Frontend (`frontend/`) — built this session
Next.js 16 (App Router) + TypeScript + Tailwind v4, deliberately lean: only `motion`, `react-compare-slider`, `lucide-react`, `clsx`/`tailwind-merge` — no shadcn/ui, no Aceternity, no Magic UI registries (that was a deliberate scope call made under time pressure; see §6 for why).

Full detail in §6 below since this is the newest, least-documented-elsewhere part of the project.

---

## 4. The git/branch archaeology (read this before touching branches)

Two separate, unrelated problems, both discovered and fixed this session:

**Problem A — stale branches.** `main`, `phase-4/frontend`, `phase-5/integration` were created once at project init (`git branch phase-1/... phase-2/... phase-3/... phase-4/... phase-5/...` all run right after the very first commit, per `EXECUTION_GUIDE.md`'s setup steps) and then simply never advanced, while `phase-1 → phase-2 → phase-3` grew as a clean **linear** chain (each branch tip is a strict ancestor of the next — no divergence, ever). So `main` was 3 phases behind reality with zero risk in fixing it: fast-forwarding is always safe when there's no divergence to reconcile.

**Problem B — silently-dropped deliverables.** A `.gitignore` block (introduced in the Phase 2 commit, plus two lines present since the *first* commit) was excluding real, finished, tested project files from ever being tracked: `backend/demo_segment.py`, `backend/tests/test_segmentation.py`, `EXECUTION_GUIDE.md`, `IMPLEMENTATION_PLAN.md`, and even the two canonical `samples/` photos that `README.md` documents. **None of these were ever committed on any branch, ever** — despite `REMINDERS.md` marking Phase 2 "done" with "19 unit tests passed". They existed on disk and worked (that's why `pytest` could find and run them), they just weren't in git history. A `git clone` of this repo from before this session would be missing the actual Phase 2 CLI entry point.

**Fix applied** (commit `be47c51`): removed the offending `.gitignore` lines (kept the legitimately-disposable ones: generated review artifacts `sample_boq.json`/`sample_report.html`, ad-hoc `samples/*copy*` test photos a human dropped in locally), added the real files, then fast-forwarded `main` onto `phase-3/renderer`'s tip (`git merge --ff-only`, zero conflicts by construction) and force-updated the two genuinely-stale `phase-4/frontend`/`phase-5/integration` pointers to match. `phase-1/calculation-engine` and `phase-2/segmentation` were **deliberately left alone** at their real historical commits (`41035c5`, `ab336ee`) — those still mean something; the other two never did.

**If you're a fresh Claude session**: don't re-introduce ignore rules for markdown docs or `backend/tests/*.py` without a very good reason and without checking `git log --all -- <path>` first to see if it's already had this exact problem.

---

## 5. Critical Bugs Encountered & Solutions (running list)

| Issue | Root Cause | Solution |
|---|---|---|
| Python 3.14 / NumPy wheel collision | No prebuilt NumPy 1.26 wheels for 3.14 | Pinned `.python-version` to 3.12.4, NumPy `>=1.26,<2` |
| SAM 3 state mutation bug | `processor.set_text_prompt()` mutates state in place; loop reuse gave identical masks | Detach to CPU numpy immediately + `reset_all_prompts()` between queries |
| 16.6MP image → GPU OOM | Raw 16MP image tried to allocate ~7.5GB tensor on a 4GB GPU | Adaptive scaling to max 1280px for inference, upscale polygons back 1:1 |
| Windows overwritten by wall mask | Single-pass mask assembly order-dependent | Strict 2-pass hierarchy: union walls, then subtract openings with 2px dilation guard |
| Faint stone texture | ControlNet scale too high (0.8), model reproduced smooth original | Tuned to 0.5–0.65, upgraded to Karras-sigma DPM-Solver |
| Dimension mismatch on new photo | Reused mask from a different-resolution photo | Auto-pipeline guard in `demo_render.py` — auto-segments if mask doesn't match |
| **SAM 3 can't even load on CPU** | Vendored `sam3/model_builder.py` hardcodes `device="cuda"` in position encoding | Not fixable here — needs a GPU machine, or an upstream patch to `../sam3` |
| **(this session) `.gitignore` silently dropped real files** | See §4 | Removed the bad rules, committed the real files, fast-forwarded `main` |
| **(this session) Material short names wrong** ("Natural Granite" instead of "Stone Cladding") | Frontend derived display names via `name.split("/")[0].trim()`, which only worked for names without a "/" | Added a proper `shortName` field to the material catalog port instead of string-splitting |
| **(this session) `react-compare-slider` badges invisible** | The library sets an explicit `z-index` on its internal layers, which beats sibling elements with `z-index: auto` regardless of DOM order | Gave the overlay badges an explicit higher `z-index` |
| **(this session) 25 balcony railings = 25 tedious individual clicks** | Original design assigned material per-zone only | Added bulk "apply to all N zones of this type" + grouped BoQ rows (see §6) |

---

## 6. Phase 4 Frontend — deep dive

### Stack & why
Next.js 16 (App Router), TypeScript, Tailwind v4, `motion` (Framer Motion's new package name), `react-compare-slider`, `lucide-react`. The original Phase 4 plan offered two options: a heavy stack (shadcn/ui + Aceternity + Magic UI registries) or a lean hand-rolled one. Under stated time pressure, went lean — same glassmorphic dark-theme visual result via plain Tailwind utility classes + inline styles, zero registry/peer-dependency risk. This was a deliberate, discussed tradeoff, not a corner cut silently.

### Design system
Dark glassmorphic theme, defined in `frontend/src/app/globals.css`: bg `#0e1015`, accent `#c8a882` (warm stone), Space Grotesk (display) + Manrope (body) via Google Fonts. A wireframe of all 6 screens was built first as a Claude Design canvas artifact (multi-artboard, published to `claude.ai/code/artifact/...`) and approved before writing real code — the frontend code matches it closely, then was pushed further on glassmorphism polish (layered gradient surfaces, ambient background glow, glowing accent states) per explicit feedback.

### The real-data pipeline (important — don't replace with fake mocks later)
Because this session had no GPU, **all frontend sample data is derived from real backend outputs**, not invented:
- `frontend/src/data/sampleHouse1.ts` — the *actual* 87-zone result of `backend/demo_segment.py` on `samples/image copy 2.png` (real polygons, areas, `recommended_materials` per zone), read from `output/zones.json` and converted with a one-off Python script (not kept in the repo — regenerate similarly if you need a second sample house). Polygon coordinates are pre-scaled to match the 1600×1200 JPEG actually served from `frontend/public/samples/`.
- `frontend/public/samples/house1-*.jpg` — real Tier-1 instant-preview renders (`demo_render.py --preview`) for 4 materials, all on that same source photo, downsampled to ~300-350KB JPEGs.
- `frontend/src/data/materials.ts` — line-for-line port of `backend/engine/materials_catalog.py`'s 7 materials (same ids, rates, wastage factors).
- `frontend/src/lib/boq.ts` — line-for-line port of `backend/engine/boq_calculator.py`'s formula, **verified against the real Python source this session**, including the gross-vs-net area asymmetry noted in §3.

**If you add a second sample house later**: the pattern is `backend/demo_segment.py --image X --output output/houseN/` → convert `zones.json` to a `sampleHouseN.ts` (see the shape of `sampleHouse1.ts`) → `backend/demo_render.py --image X --material <id> --preview --output output/houseN/` for however many material previews you want → downsample/copy into `frontend/public/samples/`.

### Architecture
```
frontend/src/
├── app/                          # layout.tsx (fonts/metadata), page.tsx (renders StudioApp), globals.css (design tokens)
├── components/studio/
│   ├── StudioApp.tsx              # wizard state machine (useState, no Redux)
│   ├── StudioHeader.tsx           # shared nav + step indicator
│   ├── steps/Step1Upload.tsx      # landing, drag-drop preview, sample house card
│   ├── steps/Step2Zones.tsx       # sidebar zone list + stats + ZoneCanvas
│   ├── canvas/ZoneCanvas.tsx      # <canvas> polygon overlay, REAL point-in-polygon hit-testing
│   ├── steps/Step3Materials.tsx   # material grid, bulk-apply toggle, live preview
│   ├── steps/Step4Comparison.tsx  # react-compare-slider before/after
│   ├── steps/Step5BoQ.tsx         # live-editable grouped BoQ table + cost summary
│   └── report/ReportModal.tsx     # printable contractor quote (window.print())
├── data/{materials,sampleHouse1}.ts
├── lib/{boq,utils}.ts
└── types/index.ts
```

### UX decisions made under real testing (not assumed — found by actually clicking through it)
- **Bulk zone assignment**: the real segmentation has 87 zones (56 windows/protected, 3 walls, 25 balcony railings, 3 roof parapets). Assigning a material to 25 railings one at a time was untenable, so `Step3Materials` has an "Apply to all N {type} at once" toggle (default on) that assigns to every zone sharing the selected zone's label. `StudioApp.assignMaterial`/`setRateOverride` both take `zoneIds: string[]`, not a single id.
- **Grouped BoQ rows**: correspondingly, `lib/boq.ts`'s `groupBoQItems()` collapses same-label/same-material line items into one display row (e.g. "Balcony Railings ×25") while still summing real per-zone costs underneath — not a shortcut, mathematically identical to itemizing.
- **Data-driven "Recommended" material badges**: uses each zone's real `recommendedMaterials` from the segmentation output rather than a hardcoded "Popular" tag.
- **Smart default zone selection**: on loading a house, auto-selects the largest assignable zone (usually the main wall) rather than array order (which happened to be a random small balcony railing — confusing first impression).
- **Honest "AI Render" tab**: Step 4's comparison screen has "Instant Preview" (real, works) and "AI Render" tabs; the AI Render tab explicitly tells the user this machine has no GPU and shows the instant preview instead, rather than faking a neural result.
- **Upload flow scope**: dragging in your own photo shows a live preview + a note that continuing past Step 1 requires a sample house (no live backend yet to run real segmentation on an arbitrary upload — that's Phase 5).

### Verification method (repeat this after any frontend change, don't just trust `npm run build`)
`npm run build`/`npm run lint` passing does **not** mean the UI works — used a scripted Playwright walkthrough (headless Chromium via `npx playwright install chromium`, no `--with-deps` since this machine has no sudo) that actually clicks through all 5 steps, screenshots each, and checks `console --errors`. This caught 3 real bugs that type-checking missed: wrong material names from a fragile string-split, invisible before/after badges from a z-index conflict, and low-contrast badge text against a specific photo's bright sky. **Don't skip this step** — re-run a similar walkthrough after material changes to the wizard flow.

### Known limitations (intentional, not oversights)
- Only one real sample house (the 87-zone one). A second was deliberately not fabricated with fake data.
- No dark/light theme toggle wired up (the header has a static moon icon) — the whole app is dark-only for now, matching the approved wireframe's default.
- No PDF generation — `ReportModal` uses the browser's native `window.print()`, which is adequate for now per the project's own "simple, sober, minimal code" philosophy; server-side WeasyPrint PDF export is a Phase 5 item.
- No backend calls at all yet — 100% client-side with the embedded real data described above.

---

## 7. Setup Guide (From Scratch, Any New PC)

```bash
# 1. Clone SAM 3 alongside this repo (sibling directories)
git clone https://github.com/facebookresearch/sam3.git
git clone https://github.com/poojan-solanki/e2m-interview.git e2m-project
# Workspace/
# ├── sam3/
# └── e2m-project/

cd e2m-project

# 2. Python backend
uv sync                              # auto-links ../sam3 in editable mode
uv run pytest backend/tests/ -v      # expect 55 passed

# 3. SAM 3 checkpoint (only needed for real segmentation, i.e. only matters on a GPU machine)
#    Place at e2m-project/weights/sam3.pt (~3.45 GB)

# 4. Frontend
cd frontend
npm install
npm run dev                          # http://localhost:3000
npm run build && npm run lint        # should both be clean
```

No branch switching needed — `main` has everything. (The docs from earlier sessions say to `git checkout phase-3/renderer`; that's now unnecessary and slightly stale advice — `main` is current.)

---

## 8. Quick Reference CLI Commands

```bash
# Phase 1: BoQ cost calculation
uv run python backend/demo_calculate.py --sample-house

# Phase 2: SAM 3 segmentation (GPU required)
uv run python backend/demo_segment.py --image samples/image.png --output output/

# Phase 3, Tier 1: instant CPU preview (<50ms, no GPU)
uv run python backend/demo_render.py --image samples/image.png --material stone_cladding --preview

# Phase 3, Tier 2: neural render (GPU required)
uv run python backend/demo_render.py --image samples/image.png --material stone_cladding --steps 20
uv run python backend/demo_render.py --image samples/image.png --material stone_cladding --fast   # 15-step fast mode

# Full test suite
uv run pytest backend/tests/ -v

# Frontend dev server
cd frontend && npm run dev
```

---

## 9. What Remains — Phase 5, and the recommended path

Per `IMPLEMENTATION_PLAN.md`, Phase 5 is: FastAPI REST endpoints, Celery+Redis async task queue, WeasyPrint PDF generation, DB persistence — replacing the frontend's embedded real-but-static data with live backend calls.

**Recommendation discussed and agreed this session** (given the original time pressure — re-evaluate if circumstances changed): **don't build the full Phase 5 as originally scoped in one shot.** Specifically:

1. **Skip Celery/Redis initially.** Build plain synchronous FastAPI endpoints first. Async task queuing only matters once the underlying GPU-dependent endpoints are proven to actually work — building queue infrastructure around an unverified pipeline is backwards.
2. **Endpoints to build, in order of how testable they are on a non-GPU machine:**
   - `POST /api/boq` — wraps `boq_calculator.py` directly. Pure CPU, fully testable anywhere, do this first.
   - `POST /api/render/preview` — wraps `instant_preview.py`. Also pure CPU, fully testable anywhere.
   - `POST /api/segment` — wraps the SAM 3 pipeline. **Only testable on the GPU machine.**
   - `POST /api/render/neural` — wraps `inpainter.py`. **Only testable on the GPU machine.**
3. **Wire the frontend's mock BoQ math and static instant-preview images to the real `/api/boq` and `/api/render/preview` endpoints first** — that's the part provable end-to-end right now, on any machine.
4. **Defer WeasyPrint PDF export and the DB layer** until the GPU-dependent endpoints are proven — `window.print()` already covers "downloadable report" adequately for now.

If you're a fresh Claude session picking this up: start with step 2's first two endpoints, verify them the same way Phase 4 was verified (actually call them, don't just trust that the code compiles), then wire the frontend to them before touching anything GPU-dependent.
