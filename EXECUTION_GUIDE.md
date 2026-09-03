# Execution & Testing Guide
### AI-Based Exterior House Renovation & Cost Estimation System

---

## Prerequisites: One-Time Environment Setup

Run these **once** before starting any phase.

### Step 1 — Create Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### Step 2 — Install PyTorch with CUDA (RTX 3050, CUDA 13.0)
```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

Verify GPU is detected:
```powershell
python -c "import torch; print(torch.cuda.get_device_name(0))"
# Expected: NVIDIA GeForce RTX 3050 Laptop GPU
```

### Step 3 — Install Project Dependencies
```powershell
pip install -r backend/requirements.txt
```

Contents of `requirements.txt`:
```
ultralytics          # Phase 2: FastSAM segmentation
diffusers            # Phase 3: SD 1.5 inpainting pipeline
transformers         # Phase 3: MiDaS depth model + SD tokenizer
controlnet-aux       # Phase 3: Canny edge preprocessing
accelerate           # Phase 3: fp16 inference optimization
opencv-python        # Phase 2 & 3: image processing
Pillow               # All phases: image I/O
piexif               # Phase 2: EXIF metadata reader
numpy                # All phases: array math
fastapi              # Phase 5: web server
uvicorn              # Phase 5: ASGI server
celery               # Phase 5: async task queue
redis                # Phase 5: Celery message broker
weasyprint           # Phase 5: PDF report generation
pytest               # All phases: unit testing
```

### Step 4 — Initialise Git Branches
```powershell
git init
git add .
git commit -m "initial project scaffold"
git branch phase-1/calculation-engine
git branch phase-2/segmentation
git branch phase-3/renderer
git branch phase-4/frontend
git branch phase-5/integration
```

---

## Phase 1 — Core Calculation Engine

### Switch Branch
```powershell
git checkout phase-1/calculation-engine
```

### How to Test
```powershell
python backend/demo_calculate.py --area 1200 --material "weatherproof_paint"
python backend/demo_calculate.py --area 800 --material "stone_cladding" --openings 120
pytest backend/tests/test_materials.py -v
pytest backend/tests/test_area_estimator.py -v
pytest backend/tests/test_boq.py -v
```

### Expected Output (Terminal)
```
=== Bill of Quantities ===
Zone     : Main Wall
Material : Weatherproof Acrylic Paint
Gross Area    : 1200.0 sq ft
Deductions    : 0.0 sq ft
Net Area      : 1200.0 sq ft
Wastage (10%) : 120.0 sq ft
Gross Qty     : 18.46 liters
Material Cost : ₹30,000
Labor Cost    : ₹14,400
─────────────────────────
Line Total    : ₹44,400
Grand Total   : ₹46,620 (incl. 5% contingency)
```

### What to Check
- [ ] Material rates match the catalog table in `IMPLEMENTATION_PLAN.md`
- [ ] Window deductions correctly reduce net area
- [ ] Wastage factor adds 10–15% to gross quantity
- [ ] Grand total includes 5% contingency

---

## Phase 2 — AI Segmentation Module

### Switch Branch
```powershell
git checkout phase-2/segmentation
```

### How to Test
```powershell
python backend/demo_segment.py --image house.jpg
python backend/demo_segment.py --image house.jpg --output output/
```

### Expected Output (Terminal + Files)
```
=== Zone Detection Results ===
Zone 1: wall            → 842.3 sq ft  (net, after window deductions)
Zone 2: window          → 96.0 sq ft   (protected — locked from renovation)
Zone 3: pillar          → 48.5 sq ft
Zone 4: balcony railing → 24.2 Rft (linear)

Output saved:
  output/zones.json
  output/wall_mask.png
  output/window_mask.png
  output/pillar_mask.png
  output/overlay_preview.png
```

### What to Check
- [ ] `zones.json` has schema: `[{id, label, polygon, area_sqft, mask_path}]`
- [ ] Window mask covers only windows (not walls)
- [ ] `overlay_preview.png` shows correctly coloured overlays on the house

### GPU VRAM During Run
```powershell
nvidia-smi   # should show ~1.2 GB VRAM used
```

---

## Phase 3 — Rendering Module

### Switch Branch
```powershell
git checkout phase-3/renderer
```

> First run downloads ~4 GB of models to `~/.cache/huggingface/` automatically.

### How to Test
```powershell
python backend/demo_render.py --image house.jpg --masks output/zones.json --material stone_cladding
python backend/demo_render.py --image house.jpg --masks output/zones.json --material weatherproof_paint
python backend/demo_render.py --image house.jpg --masks output/zones.json --material glass_railing
```

### Expected Output
```
Loading ControlNet guides...    [Canny ✓]  [Depth ✓]
Building inpainting pipeline... [SD 1.5 fp16 ✓]
Running inference (30 steps)... [████████████████] 100%  ~7.2s

Output saved:
  output/house_redesigned.png
  output/comparison.png
```

### What to Check
- [ ] Windows in `house_redesigned.png` are pixel-identical to the original
- [ ] Selected material texture is visible on walls/pillars
- [ ] No hallucinated architectural features
- [ ] `comparison.png` shows clear before/after

### GPU VRAM During Run
```powershell
nvidia-smi   # should show ~3.2 GB VRAM used
```

> [!IMPORTANT]
> If you see `CUDA Out of Memory`: run with `--steps 20` to reduce peak VRAM.

---

## Phase 4 — Frontend Prototype

### Switch Branch
```powershell
git checkout phase-4/frontend
```

### How to Test
```powershell
start frontend/index.html   # Opens in default browser. No server needed.
```

### 5-Step Walkthrough

| Step | What to Do | What to Verify |
|---|---|---|
| **1. Upload** | Click upload, select any house photo | Photo preview appears, quality indicator shows |
| **2. Zones** | Zone detection runs (mock data) | Colored overlays appear on the photo canvas |
| **3. Materials** | Click a zone → pick material from catalog | Zone label updates to selected material |
| **4. Visualize** | Click "Generate Render" | Before/after slider appears |
| **5. Report** | Edit a material rate in the BoQ table | Grand total recalculates live. Download report. |

### What to Check
- [ ] Dark/light theme toggle works
- [ ] Zone polygons are clickable
- [ ] Before/after slider drags smoothly
- [ ] BoQ recalculates when rates are edited
- [ ] Downloaded report contains photo + BoQ table

---

## Phase 5 — Integration & API Layer

### Switch Branch
```powershell
git checkout phase-5/integration
```

### Start Redis
```powershell
redis-server
```

### Start Celery Worker (second terminal)
```powershell
.\venv\Scripts\activate
celery -A backend.tasks worker --loglevel=info -P threads
```

### Start FastAPI Server (third terminal)
```powershell
.\venv\Scripts\activate
uvicorn backend.app:app --reload --port 8000
```

### Test API Endpoints
```powershell
curl -X POST http://localhost:8000/upload -F "file=@house.jpg"
curl -X POST http://localhost:8000/segment -H "Content-Type: application/json" -d "{\"image_id\": \"abc123\"}"
curl -X POST http://localhost:8000/render -H "Content-Type: application/json" -d "{\"image_id\": \"abc123\", \"material\": \"stone_cladding\"}"
curl http://localhost:8000/render/{task_id}
curl http://localhost:8000/report/abc123 --output report.pdf
```

### Full Browser Test
1. Open `frontend/index.html`
2. Upload a house photo → calls real `/upload`
3. Zone detection → calls real `/segment` (FastSAM)
4. Render → calls real `/render` (SD 1.5 + ControlNet)
5. Download PDF contractor report

---

## Troubleshooting Quick Reference

| Problem | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: torch` | PyTorch not installed or wrong venv | Activate venv, reinstall PyTorch |
| `CUDA Out of Memory` | Too much VRAM used | Close Chrome/games. Use `--steps 20` |
| FastSAM returns empty masks | Low contrast or small photo | Use min 1024×768 resolution photo |
| `EXIF data not found` | WhatsApp stripped metadata | System auto-falls back to door calibration |
| Celery not processing | Redis not running | Start `redis-server` first |
| PDF report blank images | Relative image paths | Use `os.path.abspath()` in template |

