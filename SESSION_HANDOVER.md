# Complete Session Handover & Architecture Context
### AI-Based Exterior House Renovation & Cost Estimation System

> **Document Purpose**: This document provides an exhaustive, zero-context-loss record of all work accomplished, architectural decisions, mathematical formulas, bugs solved, and exact setup instructions so you can seamlessly resume on your office PC.

---

## 1. Executive Summary & Current Status

* **Branch Structure**:
  * `phase-1/calculation-engine`: Completed & tested (24 unit tests).
  * `phase-2/segmentation`: Completed & tested & pushed (19 unit tests).
  * `phase-3/renderer`: Completed, verified with photorealistic stone cladding & auto-pipeline (8 unit tests).
* **Automated Unit Tests**: **51/51 PASSED** across all modules in ~12 seconds (`uv run pytest backend/tests/ -v`).
* **Hardware Target**: Engineered specifically for consumer laptops with **4 GB VRAM (NVIDIA RTX 3050)**. Peak VRAM never exceeds **~2.5 GB**.

---

## 2. Work Accomplished by Phase

### Phase 1: Core Calculation Engine (`backend/engine/`)
* **Civil Materials Catalog** ([`backend/engine/materials_catalog.py`](file:///p:/Syncthing/personal-progs/e2m-project/backend/engine/materials_catalog.py)):
  * 7 architectural materials: `weatherproof_paint`, `textured_stucco`, `stone_cladding`, `vitrified_tiles`, `wpc_panels`, `glass_railing`, `metal_railing`.
  * Real-world Ahmedabad / Gujarat contractor market rates (₹25–₹220/sqft material, ₹12–₹65/sqft labor).
  * Coverage ratios, wastage factors (5%–15%), and consumption units (liters, kg, sqft, Rft).
* **Metrology & Deductions** ([`backend/engine/area_estimator.py`](file:///p:/Syncthing/personal-progs/e2m-project/backend/engine/area_estimator.py)):
  * 3-tier optical calibration: Tier 1 (Reference entrance door = 2.1m height), Tier 2 (Pinhole EXIF cross-validation), Tier 3 (2-point manual ruler).
  * Shoelace formula for polygon area: $A = \frac{1}{2} |\sum (x_i y_{i+1} - x_{i+1} y_i)|$.
  * IS 1200 civil opening deduction rule: $\text{Net Area} = \text{Gross Wall} - \sum \text{Openings}$.
* **BoQ Financial Calculator** ([`backend/engine/boq_calculator.py`](file:///p:/Syncthing/personal-progs/e2m-project/backend/engine/boq_calculator.py)):
  * Line item calculations: base cost, wastage quantities, labor charges, scaffolding, and 5% contingency.
* **Report Generator** ([`backend/engine/report_generator.py`](file:///p:/Syncthing/personal-progs/e2m-project/backend/engine/report_generator.py)):
  * Exports ASCII terminal summary tables, structured `sample_boq.json`, and printable `sample_report.html` contractor quotes.

---

### Phase 2: AI Architectural Segmentation (`backend/segmentation/`)
* **Foundation Model**: Integrated **Meta SAM 3** (Segment Anything Model 3).
* **Concept Prompting**: Zero-shot architectural queries (`"exterior wall"`, `"window"`, `"porch column"`, `"balcony"`, `"roof overhang"`, `"car"`, `"person"`, `"sky"`).
* **Car-Window Subtraction**: Subtracts detected car masks from window detections so car windshields and side glass are never misclassified as house windows.
* **Foreground Isolation**: Isolates cars and workers on ladders and subtracts them from paintable wall takeoffs.
* **Closed External Polygons**: Uses `cv2.findContours` and `cv2.approxPolyDP` to guarantee closed, clean polygons with **zero diagonal artifacts**.
* **Strict 2-Pass Mask Generation** ([`backend/segmentation/zone_exporter.py`](file:///p:/Syncthing/personal-progs/e2m-project/backend/segmentation/zone_exporter.py)):
  * **Pass 1**: Union all renovatable surfaces (walls, pillars, parapets).
  * **Pass 2**: Strictly subtract all protected openings (windows, doors) with a 2-pixel dilation buffer (`cv2.dilate`) to guarantee outer wooden frames and mullions can **never be overwritten by wall polygons**.
* **Export Artifacts**: Saves individual `zone_XX_*_mask.png`, `output/renovation_inpaint_mask.png`, `output/zones.json`, and color-coded `output/overlay_preview.png`.

---

### Phase 3: AI Rendering Module (`backend/renderer/`)
* **Architectural Inpainter** ([`backend/renderer/inpainter.py`](file:///p:/Syncthing/personal-progs/e2m-project/backend/renderer/inpainter.py)):
  * Wraps `StableDiffusionControlNetInpaintPipeline` (`runwayml/stable-diffusion-inpainting` in `fp16`) with `lllyasviel/control_v11p_sd15_canny`.
  * **Memory Optimization**: Uses `pipe.enable_model_cpu_offload()` and `pipe.enable_attention_slicing()`, running comfortably in **~2.4 GB VRAM**.
  * **Scheduler Upgrade**: Uses `DPMSolverMultistepScheduler(use_karras_sigmas=True)` for sharp architectural masonry.
  * **Tuned ControlNet Scale**: Set to `0.5`–`0.65` so rich stone/stucco/wood textures emerge cleanly while building perspective and angles remain rigid.
* **100% Mathematical Pixel-Lock**:
  * Post-diffusion compositing: `result = np.where(inpaint_mask > 128, generated_pixels, original_pixels)`.
  * Guarantees all window glass, frames, reflections, cars, and workers are **100% identical to the original photo**.
* **Material Prompter** ([`backend/renderer/material_prompter.py`](file:///p:/Syncthing/personal-progs/e2m-project/backend/renderer/material_prompter.py)):
  * Translates material catalog keys into photorealistic architectural prompts with negative prompts filtering out CGI gloss, cartoon styles, and distorted windows.
* **Side-by-Side Exporter** ([`backend/renderer/before_after_exporter.py`](file:///p:/Syncthing/personal-progs/e2m-project/backend/renderer/before_after_exporter.py)):
  * Stitches original photo and redesigned visual with an architectural divider line and `BEFORE [ ORIGINAL ]` / `AFTER [ AI RENOVATION ]` badges.
* **Auto-Pipeline Guard** ([`backend/demo_render.py`](file:///p:/Syncthing/personal-progs/e2m-project/backend/demo_render.py)):
  * Accepts **any photo**. If a matching mask doesn't exist for the image resolution, it **automatically runs SAM 3 segmentation in the background**, protects the windows, and proceeds straight into inpainting.

---

## 3. Critical Bugs Encountered & Solutions Applied

| Issue Encountered | Root Cause | Exact Solution Implemented |
|---|---|---|
| **Python 3.14 NumPy Solver Collision** | Python 3.14 had no prebuilt binary wheels for NumPy 1.26, causing meson C-compilation failures. | Pinned `.python-version` to `3.12.4` and locked NumPy to `>=1.26,<2` (strict requirement for SAM 3). |
| **Meta SAM 3 State Mutation Bug** | `processor.set_text_prompt(prompt, state)` mutates internal state in-place. Successive loop calls reused previous tensors, causing identical masks. | Implemented immediate detach to CPU numpy arrays + `processor.reset_all_prompts(inference_state)` between queries. |
| **16.6 MP (5000x3333) GPU OOM Crash** | Processing a raw 16MP image attempted to allocate a 7.5 GB tensor on a 4.0 GB RTX 3050 GPU. | Implemented **Adaptive Resolution Scaling**: downscales to max 1280px for inference (VRAM drops to ~1.2 GB), then upscales detected polygon coordinates back to original size with 1:1 precision. Added `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`. |
| **Glitchy Window Overlap in Rendering** | In single-pass mask assembly, the wall polygon came after the window in the loop, overwriting the window cutout with white (inpaint). | Restructured mask generation into a **strict 2-pass hierarchy** in `zone_exporter.py`: Pass 1 unions all walls; Pass 2 subtracts all windows with a 2px dilation safety buffer. |
| **Faint / Subtle Stone Texture** | ControlNet conditioning scale was set too high (`0.8`), forcing the model to reproduce the original smooth white plaster. | Tuned ControlNet scale to `0.5`–`0.65` and upgraded diffusion scheduler to `DPMSolverMultistepScheduler(use_karras_sigmas=True)`. |
| **Dimension Mismatch Between Images** | Testing a new image reused an existing mask from a previously segmented image of a different resolution. | Added automatic validation guard and built the **Auto-Pipeline** in `demo_render.py` to auto-segment any new image on the fly. |

---

## 4. Setup Guide for Office PC (From Scratch)

Follow these exact steps when setting up the project on your office computer:

### Step 1: Clone Repositories Side-by-Side
Open a workspace folder (e.g. `C:\Projects` or `D:\Workspace`):
```powershell
# 1. Clone Meta's SAM 3 foundation repo
git clone https://github.com/facebookresearch/sam3.git

# 2. Clone this project alongside it
git clone https://github.com/poojan-solanki/e2m-interview.git e2m-project

# Directory structure should be:
# Workspace/
# ├── sam3/
# └── e2m-project/
```

### Step 2: Install uv & Sync Dependencies
```powershell
cd e2m-project

# Switch to the Phase 3 branch
git checkout phase-3/renderer

# Sync all dependencies (uv automatically links ../sam3 in editable mode)
uv sync
```

### Step 3: Place SAM 3 Checkpoint
Copy or place `sam3.pt` (~3.45 GB) into:
```text
e2m-project/weights/sam3.pt
```
*(If you already have it cached from Hugging Face on your office machine, the system will automatically find it).*

### Step 4: Verify Full Test Suite
```powershell
uv run pytest backend/tests/ -v
```
*Expected: All 51 tests pass in ~12 seconds.*

---

## 5. Quick Reference CLI Commands

```powershell
# 1. Run BoQ Cost Calculation on Sample 2-Story House (Phase 1)
uv run python backend/demo_calculate.py --sample-house

# 2. Run SAM 3 Facade Segmentation on Any Photo (Phase 2)
uv run python backend/demo_segment.py --image samples/image.png --output output/

# 3. Run AI Facade Renovation (Phase 3 - Auto-Pipeline)
# Stone Cladding:
uv run python backend/demo_render.py --image samples/image.png --material stone_cladding --steps 20

# Teak Wood Louvers:
uv run python backend/demo_render.py --image samples/image.png --material wpc_panels --style "modern villa with vertical fluted dark teak wood louvers" --control-scale 0.5

# Terracotta Textured Stucco:
uv run python backend/demo_render.py --image samples/image.png --material textured_stucco --style "warm Tuscan terracotta rustic textured stucco"

# Any new image (auto-segments and renders in one go):
uv run python backend/demo_render.py --image "samples/image copy 2.png" --material stone_cladding
```

---

## 6. What Remains for Future Phases

* **Phase 4: Interactive Web Dashboard (Single-Page App)**
  * Upload photo with drag-and-drop.
  * Interactive canvas showing color-coded architectural zones.
  * Material selector per zone (e.g. pick stone for pillar, paint for wall).
  * Interactive Before/After drag slider (using `output/comparison.png`).
  * Live editable BoQ table recalculating total costs in INR when contractor rates are edited.
  * Dark / Light mode architectural theme.
* **Phase 5: FastAPI REST API & PDF Generation**
  * FastAPI endpoints: `/api/v1/segment`, `/api/v1/render`, `/api/v1/calculate-boq`.
  * Background task handling for diffusion inference.
  * Automated contractor PDF quote export via WeasyPrint.
  * Docker container deployment.
