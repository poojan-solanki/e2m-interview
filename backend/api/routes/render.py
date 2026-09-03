"""POST /api/render/preview — wraps backend/renderer/instant_preview.py (Tier-1, CPU-only)."""

import base64
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.api.schemas import RenderPreviewRequest, RenderPreviewResponse
from backend.engine.materials_catalog import get_material
from backend.renderer.instant_preview import render_instant_preview

router = APIRouter()

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"

# Maps a sample house id to its committed source photo + matching inpaint mask.
# See backend/assets/house1/ — regenerated once via demo_segment.py on a GPU
# machine and checked into git so this endpoint needs no GPU at request time.
HOUSE_ASSETS = {
    "house-1": {
        "image": ASSETS_DIR / "house1" / "source.jpg",
        "mask": ASSETS_DIR / "house1" / "inpaint_mask.png",
    },
}


@router.post("/render/preview", response_model=RenderPreviewResponse, response_model_by_alias=True)
def render_preview(request: RenderPreviewRequest) -> RenderPreviewResponse:
    house = HOUSE_ASSETS.get(request.house_id)
    if house is None:
        raise HTTPException(status_code=404, detail=f"Unknown houseId: {request.house_id}")

    try:
        get_material(request.material_id)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = render_instant_preview(
        image=house["image"],
        inpaint_mask=house["mask"],
        material_id=request.material_id,
    )

    buffer = BytesIO()
    result.preview_image.save(buffer, format="JPEG", quality=90)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

    return RenderPreviewResponse(
        material_id=request.material_id,
        image_data_uri=f"data:image/jpeg;base64,{encoded}",
        execution_time_ms=result.execution_time_ms,
        output_width=result.output_dimensions[0],
        output_height=result.output_dimensions[1],
    )
