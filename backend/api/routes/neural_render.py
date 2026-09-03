"""POST /api/render/neural/jobs — real ControlNet+SD facade render. GPU required,
slow (~4-5 min PER distinct material).

Multi-material: different zones can be assigned different materials (see
/api/render/preview's docstring for the same pattern at the CPU-preview tier). Since
each material needs its own text prompt, one full ControlNet+SD pass runs per
distinct material — each scoped to only that material's zones via build_scoped_mask —
and the results are composited together afterward (cheap, no GPU). A house with 3
distinct materials assigned takes roughly 3x as long as a single-material render;
current_material_index/total_materials/current_material_id on the job status let the
frontend show real per-material progress instead of one opaque wait.

Job-based (not a single blocking request): a many-minute POST risks browser/proxy
timeouts and gives no progress feedback. Job status lives in the `render_jobs`
Supabase table (not an in-memory dict) so it survives a backend restart and is
queryable directly.

Runs backend/demo_render.py as a subprocess into a throwaway temp directory per
material pass — same reason /api/segment shells out to demo_segment.py rather than
loading the model in-process (see that module's docstring). The source image and
zone masks are downloaded from Supabase into the temp dir only for the subprocess's
file-path based CLI to consume; every result is uploaded back to Supabase Storage and
each pass's temp directory is deleted immediately after — nothing persists on local
disk.
"""

import tempfile
import time
import uuid
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, BackgroundTasks, HTTPException
from PIL import Image

from backend.api import supabase_client as db
from backend.api.house_assets import ROOT_DIR, build_scoped_mask, get_house, get_zones
from backend.api.logging_config import get_logger
from backend.api.schemas import NeuralRenderJobCreated, NeuralRenderJobRequest, NeuralRenderJobStatus
from backend.api.subprocess_utils import run_streaming
from backend.engine.materials_catalog import get_material
from backend.renderer.before_after_exporter import generate_before_after_comparison

router = APIRouter()
logger = get_logger("neural_render")

RENDER_TIMEOUT_SEC = 600  # 10 min ceiling per material pass; measured ~270s for 15 steps this session
NUM_INFERENCE_STEPS = 15  # fast mode — measured ~18s/step on this RTX 3050


def _run_render_job(job_id: str, house_id: str, assignments: dict) -> None:
    start = time.perf_counter()
    logger.info("job %s: starting — houseId=%s", job_id, house_id)
    db.update_row("render_jobs", "id", job_id, {"status": "running"})

    try:
        house = get_house(house_id)
        if house is None:
            raise RuntimeError(f"House {house_id} no longer exists")
        dims = (house["image_width"], house["image_height"])
        zones = get_zones(house_id)

        orig_image = Image.open(BytesIO(db.download_bytes(house["source_image_path"]))).convert("RGB")
        composite = np.array(orig_image)

        distinct_materials = sorted(set(assignments.values()))
        total = len(distinct_materials)
        logger.info("job %s: %d distinct material(s): %s", job_id, total, distinct_materials)
        demo_script = ROOT_DIR / "backend" / "demo_render.py"
        canny_url = None

        for i, material_id in enumerate(distinct_materials, start=1):
            pass_start = time.perf_counter()
            db.update_row(
                "render_jobs",
                "id",
                job_id,
                {"current_material_index": i, "total_materials": total, "current_material_id": material_id},
            )

            zone_ids = [zid for zid, mid in assignments.items() if mid == material_id]
            logger.info("job %s: pass %d/%d — material=%s, %d zone(s)", job_id, i, total, material_id, len(zone_ids))
            mask_array = build_scoped_mask(zones, zone_ids, dims)

            with tempfile.TemporaryDirectory(prefix=f"render_{job_id}_{i}_") as tmp:
                tmp_dir = Path(tmp)
                image_path = tmp_dir / "source.jpg"
                mask_path = tmp_dir / "mask.png"
                orig_image.save(str(image_path), format="JPEG", quality=95)
                cv2.imwrite(str(mask_path), mask_array)

                returncode, stdout, stderr = run_streaming(
                    [
                        "uv", "run", "python", str(demo_script),
                        "--image", str(image_path),
                        "--mask", str(mask_path),
                        "--material", material_id,
                        "--steps", str(NUM_INFERENCE_STEPS),
                        "--output", str(tmp_dir),
                    ],
                    cwd=str(ROOT_DIR),
                    timeout=RENDER_TIMEOUT_SEC,
                    logger=logger,
                )
                logger.info(
                    "job %s: pass %d/%d finished in %.1fs (exit %d)",
                    job_id, i, total, time.perf_counter() - pass_start, returncode,
                )

                result_path = tmp_dir / f"house_redesigned_{material_id}.png"
                if returncode != 0 or not result_path.exists():
                    logger.error("job %s: pass %d/%d failed for material=%s", job_id, i, total, material_id)
                    raise RuntimeError(
                        f"Render failed for material '{material_id}' (exit {returncode}): "
                        f"{stderr[-2000:] or stdout[-2000:]}"
                    )

                result_array = np.array(Image.open(result_path).convert("RGB").resize(dims))
                mask_bool = mask_array > 128
                composite = np.where(mask_bool[:, :, None], result_array, composite)

                # The Canny control image is derived purely from the original photo, so
                # it's identical across every material pass — only need to keep one copy.
                if canny_url is None:
                    canny_path = tmp_dir / "control_canny.png"
                    if canny_path.exists():
                        canny_url = db.upload_file(f"renders/{job_id}/control_canny.png", canny_path, "image/png")
            # tmp_dir and everything in it is gone from this point on.

        logger.info("job %s: all passes complete, compositing + uploading results", job_id)
        final_image = Image.fromarray(composite)
        buf = BytesIO()
        final_image.save(buf, format="PNG")
        rendered_url = db.upload_bytes(f"renders/{job_id}/rendered.png", buf.getvalue(), "image/png")

        comparison_img = generate_before_after_comparison(orig_image, final_image)
        buf2 = BytesIO()
        comparison_img.save(buf2, format="PNG")
        comparison_url = db.upload_bytes(f"renders/{job_id}/comparison.png", buf2.getvalue(), "image/png")

        elapsed = round(time.perf_counter() - start, 2)
        logger.info("job %s: done in %.1fs", job_id, elapsed)
        db.update_row(
            "render_jobs",
            "id",
            job_id,
            {
                "status": "done",
                "rendered_image_path": rendered_url,
                "control_canny_image_path": canny_url,
                "comparison_image_path": comparison_url,
                "elapsed_sec": elapsed,
            },
        )
    except Exception as e:
        elapsed = round(time.perf_counter() - start, 2)
        logger.error("job %s: failed after %.1fs: %s", job_id, elapsed, e)
        db.update_row(
            "render_jobs",
            "id",
            job_id,
            {"status": "error", "error_message": str(e), "elapsed_sec": elapsed},
        )


@router.post("/render/neural/jobs", response_model=NeuralRenderJobCreated, response_model_by_alias=True)
def create_neural_render_job(
    request: NeuralRenderJobRequest, background_tasks: BackgroundTasks
) -> NeuralRenderJobCreated:
    house = get_house(request.house_id)
    if house is None:
        raise HTTPException(status_code=404, detail=f"Unknown houseId: {request.house_id}")

    if not request.assignments:
        raise HTTPException(status_code=400, detail="No zones assigned a material.")

    distinct_materials = sorted(set(request.assignments.values()))
    for material_id in distinct_materials:
        try:
            get_material(material_id)
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))

    job_id = uuid.uuid4().hex
    db.insert_row(
        "render_jobs",
        {
            "id": job_id,
            "house_id": request.house_id,
            "assignments": request.assignments,
            "status": "pending",
            "total_materials": len(distinct_materials),
        },
    )

    logger.info(
        "job %s created — houseId=%s, %d zone(s) across %d material(s)",
        job_id, request.house_id, len(request.assignments), len(distinct_materials),
    )
    background_tasks.add_task(_run_render_job, job_id, request.house_id, request.assignments)

    return NeuralRenderJobCreated(job_id=job_id, status="pending")


@router.get("/render/neural/jobs/{job_id}", response_model=NeuralRenderJobStatus, response_model_by_alias=True)
def get_neural_render_job(job_id: str) -> NeuralRenderJobStatus:
    job = db.get_row("render_jobs", "id", job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown jobId: {job_id}")
    return NeuralRenderJobStatus(
        job_id=job["id"],
        status=job["status"],
        image_url=job.get("rendered_image_path"),
        error_message=job.get("error_message"),
        elapsed_sec=job.get("elapsed_sec"),
        current_material_index=job.get("current_material_index"),
        total_materials=job.get("total_materials"),
        current_material_id=job.get("current_material_id"),
    )
