# AI-Based Exterior House Renovation & Cost Estimation System

An intelligent computer-vision and generative AI platform for residential facade renovations. 
Homeowners and civil contractors upload an exterior house photo, and the system:
1. **Parses Facade Architecture**: Automatically identifies walls, windows, balconies, porch pillars, and roof overhangs using **Meta SAM 3** (Segment Anything Model 3).
2. **Excludes Obstructions**: Isolates foreground vehicles and personnel so paint is never applied over windows, cars, or workers.
3. **Calculates Metric Takeoffs**: Performs pixel-to-metric spatial calibration, calculates gross wall surfaces, and applies standard civil deductions (e.g. IS 1200) for window openings.
4. **Estimates Construction BoQ**: Generates itemized Bills of Quantities (primer, paint liters, labor rates, scaffolding, contingency) with real-world Indian market rates (INR / Ahmedabad benchmark).
5. **Generates Inpainting Masks**: Produces binary masks ready for generative inpainting (Phase 3).

---

## Workspace Setup (Side-by-Side Repositories)

This project uses Meta's SAM 3 foundation model. The repositories should be set up side-by-side in the same parent directory:

```text
workspace/
├── sam3/                  <-- Meta's SAM 3 repository
└── e2m-project/           <-- This repository
```

### Quick Setup Steps for Anyone:

```powershell
# 1. Clone Meta's SAM 3 repository
git clone https://github.com/facebookresearch/sam3.git

# 2. Clone this project
git clone <your-repo-url> e2m-project

# 3. Enter project directory and sync dependencies
cd e2m-project
uv sync
```

`uv sync` will automatically link the adjacent `../sam3` package into your virtual environment in editable mode (`sam3 = { path = "../sam3", editable = true }`).

---

## Model Checkpoint

Place the pre-downloaded SAM 3 checkpoint at:
```text
e2m-project/weights/sam3.pt
```
*(Model weights: ~3.45 GB. Kept in `weights/` and ignored by git).*

---

## Running the System

### 1. Run Automated Tests
```powershell
uv run pytest backend/tests/ -v
```
Runs the full test suite (43 passing unit tests covering quality validation, EXIF parsing, geometry metrology, BoQ takeoff math, and SAM 3 segmentation).

### 2. Run Facade Segmentation CLI
```powershell
uv run python backend/demo_segment.py --image samples/image.png --output output/
```
Generates the following in `output/`:
* `output/overlay_preview.png`: Color-coded visual breakdown of all architectural zones.
* `output/renovation_inpaint_mask.png`: Binary mask with locked/protected windows and foreground.
* `output/zones.json`: Structured takeoff metadata with real-world square footage and polygon coordinates.

### 3. Run BoQ & Cost Estimation Demo
```powershell
uv run python backend/demo_calculate.py --sample-house
```
Generates itemized contractor cost sheets, material consumption, and printable HTML contractor reports.

---

## Docker Deployment

To build and run the containerized segmentation engine:

```bash
# Build the Docker image
docker build -t e2m-segmenter .

# Run segmentation inside Docker with GPU support
docker run --gpus all \
    -v $(pwd)/weights:/app/weights \
    -v $(pwd)/output:/app/output \
    e2m-segmenter
```
