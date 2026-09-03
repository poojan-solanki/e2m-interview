# AI-Based Exterior House Renovation & Cost Estimation System

![Sample house exterior](sample_outputs/image.png)

An end-to-end computer-vision and generative AI platform for residential facade renovations. Homeowners and civil contractors upload an exterior house photo, and the system:
1. **Perceives Architectural Structure**: Automatically identifies walls, windows, balconies, porch pillars, and roof trims using **Meta SAM 3** (Segment Anything Model 3).
2. **Guarantees Protected Openings**: Isolates glass windows, vehicles, and workers, strictly locking them so paint, tiles, or stone are never erroneously rendered over them.
3. **Calculates Metric Takeoffs**: Performs pixel-to-metric spatial calibration, calculates gross wall surfaces, and applies standard civil deductions (IS 1200) for window openings.
4. **Estimates Construction BoQ**: Generates itemized Bills of Quantities (primer, paint liters, labor rates, scaffolding, contingency) using real-world Indian market rates (INR / Ahmedabad benchmark).
5. **Renders Photorealistic Visuals**: Uses **ControlNet Canny edge guidance** and **Stable Diffusion Inpainting** (with DPM-Solver Multistep scheduling) to apply authentic materials (split-face granite stone, teak wood louvers, textured stucco, weatherproof paint, vitrified tiles) while enforcing a **100% mathematical pixel-lock** on all protected elements.
6. **Engineered for 4 GB Consumer GPUs**: Built specifically for consumer hardware (NVIDIA RTX 3050 4GB VRAM) using FP16 precision, model CPU offloading, and adaptive resolution scaling.

---

## Workspace Setup (Side-by-Side Repositories)

This project integrates Meta's SAM 3 foundation model. The repositories should be set up side-by-side in the same parent directory:

```text
workspace/
├── sam3/                  <-- Meta's SAM 3 repository (git clone)
└── e2m-project/           <-- This repository
```

### 3-Step Setup:
```powershell
# 1. Clone Meta's SAM 3 repository
git clone https://github.com/facebookresearch/sam3.git

# 2. Clone this project
git clone <your-repo-url> e2m-project

# 3. Enter project directory and sync dependencies
cd e2m-project
uv sync
```

`uv sync` automatically links the adjacent `../sam3` package into your virtual environment in editable mode (`sam3 = { path = "../sam3", editable = true }`).

### Model Checkpoint:
Place the pre-downloaded SAM 3 checkpoint at:
```text
e2m-project/weights/sam3.pt
```
*(Model weights: ~3.45 GB. Kept in `weights/` and ignored by git. ControlNet and Stable Diffusion inpainting weights download automatically on first run to Hugging Face cache).*

---

## File-by-File Codebase Architecture

```text
e2m-project/
├── backend/
│   ├── engine/                     # Phase 1: Metrology & Civil Cost Calculation
│   │   ├── materials_catalog.py    # 7 architectural materials, coverage, wastage & Ahmedabad INR rates
│   │   ├── area_estimator.py       # Shoelace formula, 3-tier optical calibration, opening deductions
│   │   ├── boq_calculator.py       # Itemized takeoff, material quantities, labor, scaffolding & contingency
│   │   └── report_generator.py     # Multi-format exports: ASCII terminal table, JSON BoQ, HTML quote
│   │
│   ├── segmentation/               # Phase 2: Meta SAM 3 Vision-Language Segmentation
│   │   ├── segmenter.py            # SAM 3 processor, prompt loop with reset, vehicle/person exclusion, adaptive scaling
│   │   ├── area_calculator.py      # Polygon shoelace pixel-to-metric takeoff & scale calibration
│   │   ├── zone_exporter.py        # Strict 2-pass mask generation, 2px window dilation guard, zones.json export
│   │   ├── quality_checker.py      # Laplacian blur check, brightness/contrast normalization
│   │   └── exif_reader.py          # Camera focal length & sensor size EXIF metadata extractor
│   │
│   ├── renderer/                   # Phase 3: Generative AI Inpainting & ControlNet Guidance
│   │   ├── inpainter.py            # SD Inpainting + ControlNet Canny, DPM-Solver, CPU offload, 100% pixel lock
│   │   ├── controlnet_guide.py     # Gaussian-smoothed OpenCV Canny hysteresis edge map extractor
│   │   ├── material_prompter.py    # Material-to-prompt translator, architectural negative prompts, style modifiers
│   │   └── before_after_exporter.py# Side-by-side composite generator with divider line and Before/After badges
│   │
│   ├── demo_calculate.py           # Phase 1 CLI: Run BoQ financial calculations & HTML quotes
│   ├── demo_segment.py             # Phase 2 CLI: Run SAM 3 architectural segmentation & export masks
│   ├── demo_render.py              # Phase 3 CLI: Auto-Pipeline rendering for any photo with material options
│   │
│   └── tests/                      # Automated Unit Test Suite (51 Tests)
│       ├── test_materials.py       # Catalog rates, consumption math, coverage positive tests (7 tests)
│       ├── test_area_estimator.py  # Optical projection, shoelace formula, opening deduction tests (11 tests)
│       ├── test_boq.py             # Single/multi-zone BoQ math, rate overrides, summary checks (6 tests)
│       ├── test_segmentation.py    # Quality checker, EXIF reader, polygon geometry, SAM 3 logic (19 tests)
│       └── test_renderer.py        # Canny edge generator, prompt coverage, pixel-lock proof (8 tests)
│
├── samples/                        # Sample house photos for testing
│   ├── image.png                   # Primary 2-story residential house test photo (1200x900)
│   └── sample_house.jpg            # Elevation test image (59 KB)
│
├── Dockerfile                      # Production container build with CUDA 13.0, WeasyPrint, and SAM 3
├── .dockerignore                   # Ignores .venv, large weights, and outputs from Docker context
├── pyproject.toml                  # Python 3.12, strict dependencies, and cu130 PyTorch wheel index
└── README.md                       # Comprehensive system documentation
```

---

## Complete Execution & Command Flow

### 1. Automated Test Suite (All 51 Tests)
Verify the entire mathematical and model pipeline across all three phases:
```powershell
uv run pytest backend/tests/ -v
```
*Expected: 51 passed in ~12 seconds.*

---

### 2. Phase 1: Cost Estimation & BoQ Takeoffs
Generate an itemized contractor cost sheet and printable HTML quote:
```powershell
# Run sample 2-story house calculation
uv run python backend/demo_calculate.py --sample-house

# Run custom calculation with specific area and material
uv run python backend/demo_calculate.py --area 1200 --material stone_cladding --openings 120
```
Generates `sample_boq.json` and `sample_report.html` with material liters/kg, labor rates, and scaffolding.

---

### 3. Phase 2: SAM 3 Facade Segmentation
Extract architectural zones, polygon contours, and binary inpaint masks from any photo:
```powershell
uv run python backend/demo_segment.py --image samples/image.png --output output/
```
Generates in `output/`:
* `output/overlay_preview.png`: Color-coded visual breakdown of all architectural zones.
* `output/renovation_inpaint_mask.png`: Binary mask with strictly locked windows, vehicle, painter, and sky.
* `output/zones.json`: Detailed takeoffs with real-world square footage and polygon coordinates.
* `output/zone_XX_*_mask.png`: Individual binary masks for every detected element.

---

### 4. Phase 3: AI Facade Renovation & Rendering (Auto-Pipeline)
`demo_render.py` features an **Auto-Pipeline Guard**: you can pass **any image**, and it will automatically run segmentation if a matching mask doesn't exist, protect the windows, and render the renovation.

#### A. Natural Split-Face Granite & Slate Stone Cladding
```powershell
uv run python backend/demo_render.py --image samples/image.png --material stone_cladding --steps 20
```

#### B. Modern Luxury Dark Teak / Walnut WPC Louvers (Vertical Slats)
```powershell
uv run python backend/demo_render.py --image samples/image.png --material wpc_panels --style "contemporary architectural villa with vertical fluted dark teak wood louvers" --control-scale 0.5
```

#### C. Warm Mediterranean / Terracotta Textured Stucco
```powershell
uv run python backend/demo_render.py --image samples/image.png --material textured_stucco --style "warm Tuscan terracotta rustic textured stucco with earthy plaster finish"
```

#### D. Sleek Matte Charcoal Vitrified Porcelain Panels
```powershell
uv run python backend/demo_render.py --image samples/image.png --material vitrified_tiles --style "large format matte charcoal grey porcelain exterior facade panels"
```

#### E. Smooth Weatherproof Exterior Emulsion
```powershell
uv run python backend/demo_render.py --image samples/image.png --material weatherproof_paint --style "modern warm ivory and sage green weatherproof exterior paint"
```

#### CLI Options Reference for `demo_render.py`:
| Argument | Default | Description |
|---|---|---|
| `--image` | `samples/image.png` | Path to exterior residential house photo |
| `--material` | `stone_cladding` | Material key (`stone_cladding`, `weatherproof_paint`, `textured_stucco`, `vitrified_tiles`, `wpc_panels`, `glass_railing`, `metal_railing`) |
| `--style` | `None` | Custom architectural style modifier injected into the prompt |
| `--control-scale` | `0.65` | ControlNet conditioning weight (`0.45`–`0.70`). Lower values allow richer textures; higher values enforce stricter line rigidity |
| `--steps` | `25` | Number of DPM-Solver denoising steps (20 is fast and sharp) |
| `--guidance` | `7.5` | Classifier-free guidance scale |
| `--output` | `output/` | Destination directory for rendered visuals |
| `--list-materials` | Flag | Displays all available material presets |

#### Generated Visual Artifacts in `output/`:
* `output/house_redesigned_<material>.png`: High-resolution renovated facade visual.
* `output/comparison.png`: Side-by-side Before/After composite with architectural divider and badges.
* `output/control_canny.png`: Structural Canny wireframe condition map.

---

## Technical Innovations & 4 GB VRAM Strategy

1. **Adaptive 16MP Resolution Scaling**:
   When processing ultra-high-resolution smartphone photos (e.g. 5000x3333 / 16.6 MP), SAM 3 would normally exceed 7.5 GB VRAM. Our adaptive scaler resizes the image to max 1280px for inference, then upscales the detected polygon coordinates back to original resolution with 1:1 precision.
2. **Strict 2-Pass Mask Assembly Hierarchy**:
   * **Pass 1**: Unions all renovatable wall surfaces into the mask.
   * **Pass 2**: Strictly subtracts all protected openings (windows, doors, vehicles, workers) with a 2-pixel dilation guard. This guarantees that walls **can never overwrite or clip window glass**.
3. **100% Mathematical Pixel-Lock**:
   Post-diffusion, the original image pixels are directly pasted over any non-renovated regions (`mask == 0`), ensuring windows, car glass, and sky remain **100% identical to the original photo with zero hallucination or bleeding**.
4. **Model CPU Offloading**:
   Utilizes `pipe.enable_model_cpu_offload()` and attention slicing to dynamically swap UNet, VAE, and ControlNet between system RAM and GPU VRAM, keeping peak memory consumption under **~2.5 GB**.

---

## Docker Deployment

To build and run the complete containerized application:

```bash
# Build the Docker image
docker build -t e2m-renovation-engine .

# Run segmentation & rendering inside Docker with GPU passthrough
docker run --gpus all \
    -v $(pwd)/weights:/app/weights \
    -v $(pwd)/output:/app/output \
    e2m-renovation-engine
```
