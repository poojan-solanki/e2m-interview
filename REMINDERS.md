# Project Reminders & Task Tracker
### AI-Based Exterior House Renovation & Cost Estimation System

> This document tracks pending reminders, temporary test files, and follow-up tasks so nothing gets forgotten.

---

## Active Reminders & Clean-up Items

| ID | Item / Task | Category | Created At | Status | Action Needed |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **REM-001** | `sample_report.html` & `sample_boq.json` in workspace root | Clean-up | Phase 1 (Initial Test) | 🟡 **Pending User Review** | You kept these files to test and inspect the generated contractor report and JSON. Delete or move them once you're satisfied with your testing. |
| **REM-002** | Docker Production Build & Missing Libraries | Deployment | Phase 2 (SAM 3 Setup) | 🟢 **Documented & Configured** | Dockerfile builds SAM 3 with PyTorch CUDA runtime, volume mounts for weights/output, and required libraries. |

---

## Phase-by-Phase Roadmap Checklist

- [x] **Phase 1: Core Calculation Engine**
  - [x] Materials catalog with Ahmedabad INR rates (`backend/engine/materials_catalog.py`)
  - [x] Area metrology, door calibration & opening deductions (`backend/engine/area_estimator.py`)
  - [x] BoQ & Takeoff financial calculator (`backend/engine/boq_calculator.py`)
  - [x] Report generator: ASCII, JSON, HTML (`backend/engine/report_generator.py`)
  - [x] CLI testing script (`backend/demo_calculate.py`)
  - [x] 24 unit tests passed (`backend/tests/`)

- [x] **Phase 2: AI Segmentation Module (Meta SAM 3)**
  - [x] Zero-shot architectural text prompts (`"exterior wall"`, `"window"`, `"porch column"`, `"balcony"`, `"roof overhang"`)
  - [x] Adaptive resolution scaling for 16MP / 4K images with 1:1 polygon restoration (0 OOM errors on 4GB GPU)
  - [x] Foreground vehicle & person isolation with car-window subtraction
  - [x] Mask export to binary PNGs, `output/renovation_inpaint_mask.png`, and `output/zones.json`
  - [x] 19 unit tests passed (`backend/tests/test_segmentation.py`)

- [x] **Phase 3: AI Rendering Module (SD 1.5 + ControlNet / Local RTX 3050)**
  - [x] Canny edge extraction (`backend/renderer/controlnet_guide.py`)
  - [x] Architectural material prompt engineer (`backend/renderer/material_prompter.py`)
  - [x] Multi-zone inpainting pipeline in `fp16` with model CPU offload (`backend/renderer/inpainter.py`)
  - [x] 100% pixel lock mathematical composite on windows, doors, car, and painter
  - [x] Before/After side-by-side export with architectural badges (`backend/renderer/before_after_exporter.py`)
  - [x] CLI demo script (`backend/demo_render.py`)
  - [x] 8 unit tests passed (`backend/tests/test_renderer.py`)

- [ ] **Phase 4: Interactive Web Dashboard (Single-Page App)**
  - [ ] Image upload preview & quality validation
  - [ ] Interactive canvas zone overlay & material selector
  - [ ] Before/After split slider
  - [ ] Dynamic BoQ table with live rate overrides
  - [ ] Dark/Light theme toggle with architectural palette

- [ ] **Phase 5: Integration & PDF Export**
  - [ ] FastAPI REST endpoints
  - [ ] Asynchronous rendering task handling
  - [ ] Downloadable contractor PDF report generation

---

## Quick Reference CLI Commands

```powershell
# Phase 1: BoQ & Cost Calculation demo
uv run python backend/demo_calculate.py --sample-house

# Phase 2: SAM 3 Facade Segmentation demo
uv run python backend/demo_segment.py --image samples/image.png --output output/

# Phase 3: ControlNet Architectural Rendering demo
uv run python backend/demo_render.py --image samples/image.png --material stone_cladding

# Run All Automated Unit Tests (51 Tests across all modules)
uv run pytest backend/tests/ -v
```
