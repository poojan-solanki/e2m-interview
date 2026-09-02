# Project Reminders & Task Tracker
### AI-Based Exterior House Renovation & Cost Estimation System

> This document tracks pending reminders, temporary test files, and follow-up tasks so nothing gets forgotten.

---

## Active Reminders & Clean-up Items

| ID | Item / Task | Category | Created At | Status | Action Needed |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **REM-001** | `sample_report.html` & `sample_boq.json` in workspace root | Clean-up | Phase 1 (Initial Test) | 🟡 **Pending User Review** | You kept these files to test and inspect the generated contractor report and JSON. Delete or move them once you're satisfied with your testing. |

---

## Phase-by-Phase Roadmap Checklist

- [x] **Phase 1: Core Calculation Engine**
  - [x] Materials catalog with Ahmedabad INR rates (`backend/engine/materials_catalog.py`)
  - [x] Area metrology, door calibration & opening deductions (`backend/engine/area_estimator.py`)
  - [x] BoQ & Takeoff financial calculator (`backend/engine/boq_calculator.py`)
  - [x] Report generator: ASCII, JSON, HTML (`backend/engine/report_generator.py`)
  - [x] CLI testing script (`backend/demo_calculate.py`)
  - [x] 24 unit tests passed (`backend/tests/`)

- [ ] **Phase 2: AI Segmentation Module (Ultralytics FastSAM)**
  - [ ] Text-prompted zone segmentation (`"wall"`, `"window"`, `"pillar"`, `"balcony railing"`)
  - [ ] Mask export to binary PNGs and polygon coordinates
  - [ ] Net workable area calculation from segmented masks
  - [ ] CLI demo script (`demo_segment.py`)

- [ ] **Phase 3: AI Rendering Module (SD 1.5 + ControlNet / Local RTX 3050)**
  - [ ] Canny edge extraction & MiDaS depth map guide
  - [ ] Multi-zone inpainting pipeline in `fp16`
  - [ ] Protected window/door masking (100% pixel lock)
  - [ ] Before/After side-by-side export

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
# Phase 1 CLI demo
uv run python backend/demo_calculate.py --sample-house

# Phase 1 unit tests
uv run pytest backend/tests/ -v

# View sample HTML report in browser
start sample_report.html
```
