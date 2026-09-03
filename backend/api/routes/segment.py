"""POST /api/segment — real SAM 3 segmentation for any uploaded photo. GPU required.

Runs backend/demo_segment.py as a subprocess into a throwaway temp directory — loading
the SAM 3 checkpoint directly inside the FastAPI/uvicorn/asyncio process reliably
segfaults this Windows/CUDA setup (reproduced as a sync endpoint, an async endpoint,
and via TestClient), so this endpoint shells out instead. Every artifact the
subprocess produces (source photo, zones.json) is uploaded to Supabase and the temp
directory is deleted before the response returns — nothing about an upload is
retained on local disk; Supabase is the only place this data lives afterward.

Deduplicated by content hash: re-uploading the same photo (e.g. clicking "Analyze"
again after navigating back to Step 1) returns the already-computed result instead
of re-running SAM 3 and creating a duplicate house.
"""

import hashlib
import json
import tempfile
import time
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from backend.api import supabase_client as db
from backend.api.house_assets import ROOT_DIR, get_zones
from backend.api.logging_config import get_logger
from backend.api.schemas import SegmentResponse, ZoneResponse
from backend.api.subprocess_utils import run_streaming

router = APIRouter()
logger = get_logger("segment")

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
SEGMENT_TIMEOUT_SEC = 180


def _zone_responses(zones: list) -> list:
    return [
        ZoneResponse(
            id=z["id"],
            label=z["label"],
            display_name=z["display_name"],
            category=z["category"],
            is_protected=z["is_protected"],
            confidence=z["confidence"],
            polygon=[tuple(pt) for pt in z["polygon"]],
            bbox=tuple(z["bbox"]),
            pixel_area=z["pixel_area"],
            gross_area_sqft=z["gross_area_sqft"],
            deductions_sqft=z["deductions_sqft"],
            net_area_sqft=z["net_area_sqft"],
            running_feet=z["running_feet"],
            recommended_materials=z["recommended_materials"],
        )
        for z in zones
    ]


@router.post("/segment", response_model=SegmentResponse, response_model_by_alias=True)
def segment_photo(file: UploadFile) -> SegmentResponse:
    logger.info("upload received: filename=%s content_type=%s", file.filename, file.content_type)

    if not file.content_type or not file.content_type.startswith("image/"):
        logger.warning("rejected non-image upload: content_type=%s", file.content_type)
        raise HTTPException(status_code=400, detail=f"Expected an image upload, got: {file.content_type}")

    raw = file.file.read()
    logger.info("upload size: %.1f KB", len(raw) / 1024)
    if len(raw) > MAX_UPLOAD_BYTES:
        logger.warning("rejected oversized upload: %d bytes", len(raw))
        raise HTTPException(status_code=400, detail=f"Upload too large ({len(raw)} bytes, max {MAX_UPLOAD_BYTES}).")

    content_hash = hashlib.sha256(raw).hexdigest()
    logger.info("content_hash=%s", content_hash[:16])
    existing = db.query("houses", {"content_hash": content_hash})
    if existing:
        house = existing[0]
        logger.info("cache hit — houseId=%s already segmented, skipping SAM 3", house["id"])
        zones = get_zones(house["id"])
        return SegmentResponse(
            house_id=house["id"],
            image_width=house["image_width"],
            image_height=house["image_height"],
            total_gross_wall_area_sqft=house["total_gross_wall_area_sqft"],
            net_paintable_wall_area_sqft=house["net_paintable_wall_area_sqft"],
            scale_factor_sqft_per_sq_pixel=house["scale_factor_sqft_per_sq_pixel"],
            calibration_method=house["calibration_method"],
            quality_warnings=house.get("quality_warnings", []),
            zones=_zone_responses(zones),
        )

    try:
        img = Image.open(BytesIO(raw)).convert("RGB")
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Could not decode image file. It may be corrupted.")

    house_id = f"upload-{uuid.uuid4().hex[:12]}"
    logger.info("cache miss — starting SAM 3 segmentation for new houseId=%s", house_id)
    demo_script = ROOT_DIR / "backend" / "demo_segment.py"

    with tempfile.TemporaryDirectory(prefix=f"segment_{house_id}_") as tmp:
        tmp_dir = Path(tmp)
        source_path = tmp_dir / "source.jpg"
        img.save(str(source_path), format="JPEG", quality=95)

        # `uv run` (not a bare sys.executable subprocess) — matches the invocation
        # that reliably completes for the SAM 3 checkpoint load; see SESSION_HANDOVER.md.
        subprocess_start = time.perf_counter()
        returncode, stdout, stderr = run_streaming(
            ["uv", "run", "python", str(demo_script), "--image", str(source_path), "--output", str(tmp_dir)],
            cwd=str(ROOT_DIR),
            timeout=SEGMENT_TIMEOUT_SEC,
            logger=logger,
        )
        logger.info("SAM 3 subprocess finished in %.1fs (exit %d)", time.perf_counter() - subprocess_start, returncode)

        zones_json_path = tmp_dir / "zones.json"
        if returncode != 0 or not zones_json_path.exists():
            logger.error("segmentation failed for houseId=%s (exit %d)", house_id, returncode)
            raise HTTPException(
                status_code=500,
                detail=f"Segmentation failed (exit {returncode}): {stderr[-2000:] or stdout[-2000:]}",
            )

        with open(zones_json_path, "r", encoding="utf-8") as f:
            result = json.load(f)

        quality = result.get("quality_report", {})
        logger.info(
            "segmentation produced %d zones, quality warnings=%s errors=%s",
            len(result.get("zones", [])), quality.get("warnings", []), quality.get("errors", []),
        )
        if quality.get("errors"):
            logger.warning("houseId=%s rejected: unusable photo quality", house_id)
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Photo is not usable for segmentation.",
                    "errors": quality["errors"],
                    "warnings": quality.get("warnings", []),
                },
            )

        # Upload while the temp dir still exists — source photo plus the raw
        # zones.json kept verbatim (alongside the normalized `zones` rows below) so
        # the exact SAM 3 output is preserved, not just its derived fields.
        logger.info("uploading source photo + zones.json to Supabase Storage")
        db.upload_file(f"houses/{house_id}/source.jpg", source_path, "image/jpeg")
        db.upload_file(f"houses/{house_id}/zones.json", zones_json_path, "application/json")
    # tmp_dir and everything in it is gone from this point on.

    logger.info("writing houses + zones rows to Supabase Postgres")
    db.insert_row(
        "houses",
        {
            "id": house_id,
            "content_hash": content_hash,
            "source_image_path": f"houses/{house_id}/source.jpg",
            "image_width": result["image_dimensions"]["width"],
            "image_height": result["image_dimensions"]["height"],
            "total_gross_wall_area_sqft": result["total_gross_wall_area_sqft"],
            "net_paintable_wall_area_sqft": result["net_paintable_wall_area_sqft"],
            "scale_factor_sqft_per_sq_pixel": result["scale_factor"]["sq_feet_per_sq_pixel"],
            "calibration_method": result["calibration_method"],
            "quality_warnings": quality.get("warnings", []),
        },
    )

    db.insert_rows(
        "zones",
        [
            {
                "house_id": house_id,
                "zone_key": z["id"],
                "label": z["label"],
                "display_name": z["display_name"],
                "category": z["category"],
                "is_protected": z["is_protected"],
                "confidence": z["confidence"],
                "polygon": z["polygon"],
                "bbox": list(z["bbox"]),
                "pixel_area": z["pixel_area"],
                "gross_area_sqft": z["gross_area_sqft"],
                "deductions_sqft": z["deductions_sqft"],
                "net_area_sqft": z["net_area_sqft"],
                "running_feet": z["running_feet"],
                "recommended_materials": z["recommended_materials"],
            }
            for z in result["zones"]
        ],
    )

    logger.info("segmentation complete for houseId=%s", house_id)
    return SegmentResponse(
        house_id=house_id,
        image_width=result["image_dimensions"]["width"],
        image_height=result["image_dimensions"]["height"],
        total_gross_wall_area_sqft=result["total_gross_wall_area_sqft"],
        net_paintable_wall_area_sqft=result["net_paintable_wall_area_sqft"],
        scale_factor_sqft_per_sq_pixel=result["scale_factor"]["sq_feet_per_sq_pixel"],
        calibration_method=result["calibration_method"],
        quality_warnings=quality.get("warnings", []),
        zones=_zone_responses(result["zones"]),
    )
