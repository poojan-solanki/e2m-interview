# AI-Based Exterior House Renovation & Cost Estimation System
### Definitive Implementation Plan — Merged & Consolidated

---

## What Are We Building?

A web-based platform where a homeowner:
1. Uploads a photo of their house exterior
2. Sees AI-identified zones (walls, windows, balcony, pillars)
3. Picks materials (paint, tiles, stone, glass railings)
4. Sees a redesigned visual of their own house
5. Gets a cost breakdown and downloadable contractor report

---

## Hardware & Environment

- **OS:** Windows 11 / **Python:** 3.12
- **GPU:** NVIDIA GeForce RTX 3050 Laptop GPU — **4 GB VRAM** / CUDA 13.0
- **Design Philosophy:** Simple, sober, minimal code. Easy to read, debug, and explain to the interview panel.

---

## Requirement → Phase Mapping

| Original Requirement | Covered In |
|---|---|
| 5.1 Media Upload + Quality Check | Phase 1 (validation), Phase 4 (frontend) |
| 5.2 Exterior Structure Identification | **Phase 2** (Segmentation) |
| 5.3 Design & Material Selection | Phase 1 (catalog), Phase 4 (frontend) |
| 5.4 Renovation Visualization | **Phase 3** (Inpainting + ControlNet) |
| 5.5 Surface Area Estimation | Phase 1 (area estimator) + Phase 2 (pixel→metric) |
| 5.6 Material Quantity Calculation | Phase 1 (BoQ calculator) |
| 5.7 Cost Estimation (editable rates) | Phase 1 (BoQ), Phase 4 (live editable table) |
| 5.8 Downloadable Report | Phase 5 (PDF generator) |

---

## Technical Decisions & Clarifications

### Comment 1 — Segmentation, Rendering & ControlNet

#### Segmentation: Ultralytics FastSAM (Updated from SAM 2)

Mask R-CNN (2020-era) requires a pre-labeled house dataset — too much setup work upfront.
SAM 2 was our next choice, but for this project we use **Ultralytics FastSAM** instead:

| | SAM 2 (Meta Official Repo) | Ultralytics FastSAM ✅ |
|---|---|---|
| Windows Setup | Requires `ninja`, `flash-attn-3`, manual CUDA build | `pip install ultralytics` — done in 30 seconds |
| VRAM on RTX 3050 | 4–8 GB (risky on 4 GB) | ~1.2 GB (safe, leaves room for rendering) |
| Text Prompts | Needs separate Grounding DINO pairing | Built-in CLIP text prompts: `"wall"`, `"window"` |
| Output Format | Raw PyTorch tensors | `.masks.xy` polygon coordinates, ready for canvas UI |

**How it works:**
```python
from ultralytics import FastSAM
model = FastSAM("FastSAM-s.pt")
results = model("house.jpg", device="cuda",
                texts=["wall", "window", "balcony railing", "pillar"])
masks = results[0].masks.xy  # List of polygon coordinates per zone
```

---

#### Is Stable Diffusion Inpainting Deprecated? What about FLUX.1 Fill?

**SD Inpainting is NOT deprecated.** FLUX.1 Fill is the current SOTA open-weight inpainting model (Black Forest Labs, 2024) and maintains house structure better. However:

| | FLUX.1 Fill | SD 1.5 Inpainting ✅ (Local) |
|---|---|---|
| VRAM Required | **24 GB minimum** — crashes RTX 3050 | **~3.2 GB in fp16** — fits RTX 3050 perfectly |
| Speed on RTX 3050 | Will OOM crash | 5–8 seconds per render |
| Cost | Fal.ai API ~₹3–8/render | Free (local) |

**Decision:** Use **SD 1.5 Inpainting in fp16** locally on the RTX 3050. Keep FLUX.1 Fill as an optional API call for higher-quality renders when a cloud GPU is available.

---

#### How Does ControlNet Help?

ControlNet is a **"guide rail" for AI image generation**. Without it, asking AI to add stone cladding will:
- Change the shape of windows
- Move the balcony location
- Invent architectural features that don't exist

ControlNet **locks the structure of the building** while only changing materials:
1. Extracts structural lines from the house image (Canny edge map + MiDaS depth map)
2. Feeds these as rigid structural constraints to SD/FLUX
3. The AI renders new materials **only within those locked structural boundaries**

**Analogy:** ControlNet is like a coloring book template. The AI colors textures however it wants, but cannot draw outside the existing outlines.

**Current status (2026):** ControlNet is still the industry standard for architecture workflows. The Canny and Depth variants are specifically suited for facade redesign.

**Full Rendering Pipeline:**
```
Original House Photo
        │
        ├──► Canny Edge Extraction  ──────────┐
        │                                     │
        └──► MiDaS Depth Map  ────────────────┼──► ControlNet + SD 1.5 Inpainting
                                              │             │
FastSAM Zone Masks (Wall / Pillar / Railing)──┘             │
Windows + Doors = EXCLUDED (pixel-locked) ──────────────────┘
                                                            ▼
                                               Redesigned House Image
                                               (Structure 100% preserved)
```

---

#### GPU Budget Per Phase

| Phase | Operation | GPU Needed? | VRAM | Cost |
|---|---|---|---|---|
| Segmentation (FastSAM) | Detect walls, windows | Yes, once | ~1.2 GB | Free (local) |
| Rendering (SD 1.5 fp16) | Redesign with material | Yes, on demand | ~3.2 GB | Free (local) |
| Area Estimation | Pinhole math | No (CPU) | 0 | Free |
| BoQ / Cost Calc | Formula math | No (CPU) | 0 | Free |

> Both segmentation and rendering fit within the 4 GB budget when run sequentially.

---

### Comment 2 — EXIF Data & Area Estimation

#### Physics & Formula Correction

The original FOV formula computes the entire frame width, not the house object width. The correct direct optical relationship (pinhole camera model) is:

$$\text{Real Dimension (m)} = \frac{\text{Pixel Dimension} \times D}{f_{\text{pixels}}}$$

where:

$$f_{\text{pixels}} = \frac{f_{\text{mm}} \times \text{Image Width (px)}}{\text{Sensor Width (mm)}}$$

#### Critical EXIF Limitations

> [!WARNING]
> **The Quadratic Error Trap (D²):** Smartphone GPS has ±5–10 m horizontal error. At 15 m distance, a 5 m GPS error is a 33% error in D. Because area scales as D², that produces a **~77% error in calculated wall area and cost**.
>
> **Metadata Stripping:** >90% of photos shared via WhatsApp or Telegram have EXIF completely stripped.

#### 3-Tier Cascading Engine (Our Solution)

1. **Tier 1 — Primary Anchor:** Reference Object Calibration (auto-detect standard entrance door = 2.1 m × 0.9 m, or floor height = 3.0 m). Works on **every** photo, even without EXIF.
2. **Tier 2 — Secondary Cross-Check:** If EXIF focal length is present and user provides estimated distance D, cross-validate the scale using the pinhole formula.
3. **Tier 3 — Safety Net:** On-screen interactive 2-point calibration ruler for manual user override.

#### Civil Opening Deduction Rule

$$\text{Net Workable Area} = \text{Gross Wall Area} - \sum \text{Window \& Door Areas}$$

#### What EXIF Cannot Do
- Cannot work if the photo was cropped or compressed (Instagram, WhatsApp, etc.)
- Cannot handle extreme fish-eye/wide-angle lenses without distortion correction
- Cannot estimate depth for oblique angles without vanishing point homography

---

### Comment 3 — Design Choices (Decisions Made)

**Choice A — Segmentation:**
> ✅ **Semi-automatic** — FastSAM gives an automatic first guess per zone. User can click to correct missed areas on an interactive canvas.

**Choice B — Rendering:**
> ✅ **AI-rendered output** — SD 1.5 Inpainting + ControlNet locally on the RTX 3050. This is the mandatory deliverable per Requirement 5.4 ("realistically apply textures/colors/materials").

**Choice C — Prototype Architecture:**
> ✅ **Phased** — Phase 4 frontend works standalone in browser with mock data. Phase 5 wires it to the real FastAPI backend.

---

### Comment 4 — UI Theme
✅ Full dark/light mode toggle with system preference detection. Premium color palette: warm neutrals, architectural slate tones, contrast accents. No plain primary colors.

---

### Comment 5 — Branch Structure
✅ Each phase has its own Git branch, its own testable CLI entry point, and zero dependency on later phases.

---

## Phased Delivery Plan (Branched & Independently Testable)

Each phase has a **clear deliverable** you can test and give feedback on before the next phase begins.

```
PHASE 1: Core Calculation Engine (Python, no AI, no UI)
   └── Test: python demo_calculate.py --area 1200 --material "weatherproof_paint"

PHASE 2: AI Segmentation Module (Ultralytics FastSAM, no UI)
   └── Test: python demo_segment.py --image house.jpg

PHASE 3: Rendering Module (SD 1.5 + ControlNet, no UI)
   └── Test: python demo_render.py --image house.jpg --masks zones.json --material stone_cladding

PHASE 4: Frontend Prototype (HTML/JS only, no backend)
   └── Test: Open index.html in browser — zero setup required

PHASE 5: Integration (Frontend → Backend API)
   └── Test: Full end-to-end flow in browser
```

---

### Phase 1 — Core Calculation Engine
**Branch:** `phase-1/calculation-engine`

**What it does:**
- Takes surface dimensions (from user input or later from segmentation)
- Applies material coverage ratios and wastage
- Outputs a Bill of Quantities (BoQ) and cost breakdown in INR (₹)
- Generates a contractor-ready text/HTML report

**Testable via:** `python demo_calculate.py --area 1200 --material "weatherproof_paint"`

**INR Rates (Ahmedabad / Gujarat market):**

| Material | Coverage | Wastage | Material Rate | Labor Rate |
|---|---|---|---|---|
| Weatherproof Acrylic Paint | 65 sq ft / liter (2 coats + primer) | 10% | ₹25/sq ft | ₹12/sq ft |
| Textured Stucco Finish | 25 sq ft / kg | 10% | ₹45/sq ft | ₹18/sq ft |
| Natural Granite/Slate Cladding | 1 sq ft + 4.5 kg adhesive/m² | 15% | ₹220/sq ft | ₹65/sq ft |
| Exterior Vitrified Tiles | Tile count + grout | 10% | ₹85/sq ft | ₹35/sq ft |
| Frameless Glass Railing (SS 304) | Linear Rft, post every 4 ft | 5% | ₹1,400/Rft | ₹300/Rft |
| Powder-Coated Metal Railing | Linear Rft | 5% | ₹650/Rft | ₹180/Rft |

**Exact Steps to Build Phase 1:**
1. Create `backend/engine/materials_catalog.py` — a Python dict or dataclass for every material: keys are `id`, `name`, `unit`, `coverage_per_unit`, `wastage_factor`, `material_rate_inr`, `labor_rate_inr`.
2. Create `backend/engine/area_estimator.py` — implement `calculate_scale_factor(door_height_px, image_height_px)` using Tier 1 reference calibration. Implement `compute_net_area(gross_area_sqft, openings_list)` applying the deduction rule.
3. Create `backend/engine/boq_calculator.py` — implement `calculate_boq(zone_areas, material_selections)` that loops over each zone, looks up the material from the catalog, applies `gross_qty = net_area × (1 + wastage)`, computes `cost = gross_qty × (material_rate + labor_rate)`, and returns an itemized list.
4. Create `backend/engine/report_generator.py` — implement `generate_report(boq_items, original_image_path, render_image_path)` that returns an HTML string with a summary table.
5. Create `backend/tests/` with `test_materials.py`, `test_area_estimator.py`, `test_boq.py` — write pytest cases for each formula.
6. Create `backend/demo_calculate.py` — a `argparse` CLI that accepts `--area`, `--material`, and prints the itemized BoQ to the terminal.

**Files:**
```
backend/
├── engine/
│   ├── materials_catalog.py     # All materials, coverage, rates (INR), wastage
│   ├── area_estimator.py        # Pinhole projection + reference door calibration
│   ├── boq_calculator.py        # Net area deductions, wastage, cost formula engine
│   └── report_generator.py      # HTML/text BoQ report output
├── tests/
│   ├── test_materials.py
│   ├── test_area_estimator.py
│   └── test_boq.py
└── demo_calculate.py
```

**No GPU needed. No UI. Pure logic. Fully testable with pytest.**

---

### Phase 2 — AI Segmentation Module
**Branch:** `phase-2/segmentation`
**Depends on:** Phase 1 (uses materials catalog for zone labeling)

**What it does:**
- Accepts a house photo (JPEG/PNG)
- Validates image quality (blur check via Laplacian variance)
- Reads EXIF metadata (focal length, sensor size, GPS) if available
- Runs Ultralytics FastSAM to detect: Main Walls, Windows, Balcony, Pillars, Parapet, Accent Zone
- Estimates real-world metric area per zone using Tier 1 reference calibration
- Returns: JSON with zone labels + polygon masks + estimated net areas (sq ft)

**Testable via:** `python demo_segment.py --image house.jpg`
Outputs: `zones.json`, `wall_mask.png`, `window_mask.png`, etc.

**Exact Steps to Build Phase 2:**
1. Create `backend/segmentation/segmenter.py` — load `FastSAM("FastSAM-s.pt")`. Run `model(image_path, device="cuda", texts=["wall", "window", "balcony railing", "pillar"])`. Extract polygon coordinates from `results[0].masks.xy`. Label each polygon with its closest matching text concept. Return list of `{label, polygon_points, bounding_box_px}`.
2. Create `backend/segmentation/exif_reader.py` — use `Pillow` to open the image and read `._getexif()`. Extract focal length, sensor width, and GPS tags if present. Return a dict — all fields optional (may be None if stripped).
3. Create `backend/segmentation/area_calculator.py` — take polygon pixel coordinates + scale factor from Phase 1 `area_estimator.py`. Compute polygon area in pixels using the shoelace formula `A = 0.5 × |Σ(xᵢyᵢ₊₁ - xᵢ₊₁yᵢ)|`. Convert to sq ft using the scale factor. Apply window deduction for `wall` zones.
4. Create `backend/segmentation/zone_exporter.py` — save each mask as a binary PNG (white = zone, black = everything else). Write `zones.json` with schema: `[{id, label, polygon, area_sqft, mask_path}]`.
5. Create `backend/demo_segment.py` — CLI that accepts `--image`, runs the full segmentation pipeline, prints zone summary table, and saves all outputs to an `output/` folder.

**Files:**
```
backend/segmentation/
├── segmenter.py             # Ultralytics FastSAM — text prompts → polygon masks
├── exif_reader.py           # Extract focal length, sensor size, GPS from EXIF
├── area_calculator.py       # Shoelace formula + pinhole scale → metric areas
└── zone_exporter.py         # Save mask PNGs + zones.json
tests/
└── test_segmentation.py
demo_segment.py
```

**Runs on RTX 3050 (~1.2 GB VRAM). Can run on CPU slowly if no GPU.**

---

### Phase 3 — Rendering Module
**Branch:** `phase-3/renderer`
**Depends on:** Phase 2 (uses segmentation masks)

**What it does:**
- Takes house image + zone masks + selected material name
- Extracts Canny edge map + MiDaS depth map from the original photo (for ControlNet)
- Runs SD 1.5 Inpainting fp16 + ControlNet locally on the RTX 3050
- Keeps windows, doors, and roofline pixel-perfect (excluded from the inpaint mask)
- Returns the redesigned house image + side-by-side comparison

**Testable via:** `python demo_render.py --image house.jpg --masks zones.json --material stone_cladding`
Outputs: `house_redesigned.png`, `comparison.png`

**Exact Steps to Build Phase 3:**
1. Create `backend/renderer/controlnet_guide.py` — load the input image with OpenCV. Run `cv2.Canny()` to extract edge map. Load `Intel/dpt-large` (MiDaS) from HuggingFace to generate a depth map. Resize both to match the input image. Return both as PIL Images.
2. Create `backend/renderer/material_prompter.py` — a dict mapping material IDs to optimized SD prompts. E.g., `"stone_cladding"` → `"modern house exterior, natural split-face granite stone cladding on walls, 8k architectural photo, photorealistic, sharp detail"`.
3. Create `backend/renderer/inpainter.py` — load `runwayml/stable-diffusion-inpainting` and the ControlNet Canny model in `torch.float16`. Build the `StableDiffusionControlNetInpaintPipeline`. Call `pipeline(prompt, image, mask_image, control_image, num_inference_steps=30)`. The mask must cover only the selected renovation zones (walls/pillars), with windows and doors set to black (protected).
4. Create `backend/renderer/before_after_exporter.py` — side-by-side PIL `Image.new()` combining original + redesigned images with a thin divider line.
5. Create `backend/demo_render.py` — CLI accepting `--image`, `--masks` (zones.json), `--material`. Runs the full pipeline and saves outputs.

**Files:**
```
backend/renderer/
├── inpainter.py             # SD 1.5 fp16 inpainting pipeline (local, RTX 3050)
├── controlnet_guide.py      # Canny edge + MiDaS depth map extraction
├── material_prompter.py     # material id → optimized SD text prompt
└── before_after_exporter.py # Side-by-side comparison image generator
tests/
└── test_renderer.py
demo_render.py
```

**Requires RTX 3050 GPU (~3.2 GB VRAM). FLUX.1 Fill via Fal.ai API is an optional higher-quality alternative.**

---

### Phase 4 — Frontend Prototype
**Branch:** `phase-4/frontend`
**Depends on:** Understands Phase 1–3 data contracts, mocks API responses

**What it does:**
- Full 5-step UI workflow matching Requirements 5.1–5.8
- Uses mock/sample data to simulate segmentation and rendering
- Calculates BoQ and costs entirely in JavaScript (offline — no backend needed)
- Before/after split slider viewer (Requirement 5.4)
- Downloadable HTML report (Requirement 5.8)
- User can edit material rates and see live recalculated costs (Requirement 5.7)

**Testable via:** Open `index.html` in browser — **zero setup required.**

**Exact Steps to Build Phase 4:**
1. Create `frontend/index.html` — a 5-step wizard UI: (1) Upload photo, (2) View detected zones with colored overlays, (3) Material picker per zone, (4) Before/after slider, (5) BoQ table + export.
2. Create `frontend/app.js` — implement: image upload preview, canvas polygon drawing with color-coded zone overlays (mock data), material picker updating the overlay color/texture, a before/after drag slider using `clip-path`, a live BoQ table recalculating costs when material rates are edited, and a "Download Report" button generating an HTML blob.
3. Create `frontend/styles.css` — dark/light theme toggle via CSS custom properties (`--bg-color`, `--text-color`, `--accent`), premium architectural palette (warm stone #C8A882, slate #64748B, deep charcoal #1C1C1E, warm white #F5F0EB).

**Files:**
```
frontend/
├── index.html
├── app.js
└── styles.css
```

---

### Phase 5 — Integration & API Layer
**Branch:** `phase-5/integration`
**Depends on:** Phases 1–4

**What it does:**
- FastAPI server wiring all backend modules into clean REST endpoints
- Frontend calls real API instead of mock data
- Celery + Redis task queue for async rendering (non-blocking UI during AI render)
- PDF report generation with: original image, redesigned image, materials list, BoQ breakdown
- Full end-to-end user flow per Requirement 5.8

**Exact Steps to Build Phase 5:**
1. Create `backend/app.py` — define FastAPI routes: `POST /upload` (validate + save image), `POST /segment` (run Phase 2 segmenter, return zones.json), `POST /render` (queue render task, return task ID), `GET /render/{task_id}` (poll render status + return image URL), `POST /boq` (run Phase 1 BoQ calculator with zone areas), `GET /report/{project_id}` (generate + return PDF).
2. Create `backend/tasks.py` — Celery tasks wrapping Phase 3 `inpainter.py` so rendering is non-blocking.
3. Create `backend/pdf_generator.py` — use WeasyPrint to generate a styled PDF from an HTML template containing: project title, original photo, redesigned photo, materials table, itemized BoQ, grand total, and legal disclaimer ("Estimates are advisory").
4. Update `frontend/app.js` to replace all mock data calls with real `fetch()` calls to the FastAPI endpoints.

**Files:**
```
backend/
├── app.py
├── tasks.py
└── pdf_generator.py
```

---

## Final File Structure

```
e2m-project/
├── backend/
│   ├── engine/
│   │   ├── materials_catalog.py
│   │   ├── area_estimator.py
│   │   ├── boq_calculator.py
│   │   └── report_generator.py
│   ├── segmentation/
│   │   ├── segmenter.py
│   │   ├── exif_reader.py
│   │   ├── area_calculator.py
│   │   └── zone_exporter.py
│   ├── renderer/
│   │   ├── inpainter.py
│   │   ├── controlnet_guide.py
│   │   ├── material_prompter.py
│   │   └── before_after_exporter.py
│   ├── tests/
│   │   ├── test_materials.py
│   │   ├── test_area_estimator.py
│   │   ├── test_boq.py
│   │   ├── test_segmentation.py
│   │   └── test_renderer.py
│   ├── app.py
│   ├── tasks.py
│   ├── pdf_generator.py
│   ├── demo_calculate.py
│   ├── demo_segment.py
│   ├── demo_render.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── IMPLEMENTATION_PLAN.md
├── EXECUTION_GUIDE.md
└── README.md
```

---

## Open Questions (To Be Decided Before Building Starts)

1. **Which Phase to start with first?**
   - Phase 1 (Calculation Engine — pure Python, testable immediately, no AI)
   - Phase 4 (Frontend Prototype — open in browser, see the UI first)

2. **For Phase 3 rendering — primary approach?**
   - Local SD 1.5 fp16 on your RTX 3050 (free, 5–8 sec/render, fits 4 GB VRAM)
   - FLUX.1 Fill via API (Fal.ai / Segmind free tier — better quality, ~10 sec, no GPU load)

3. **EXIF-based area estimation — include?**
   - Yes — extract EXIF and cross-validate with Tier 1 reference calibration
   - No — keep it simple with reference calibration only (door = 2.1 m)
