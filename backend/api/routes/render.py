"""POST /api/render/preview — wraps backend/renderer/instant_preview.py (Tier-1, CPU-only).

Multi-material: different zones can be assigned different materials. One
render_instant_preview call runs per distinct material (each scoped to only its own
zones via build_scoped_mask), and the results are composited into a single image —
render_instant_preview's pixel-lock guarantees each call only touches its own mask's
pixels, so compositing is a simple masked overwrite, no blending needed between passes.

Fully in-memory: the source image and inpaint masks come from Supabase (Storage +
Postgres zone polygons), and render_instant_preview accepts PIL Images directly, so
nothing ever touches local disk for this endpoint.
"""

import base64
from io import BytesIO

import numpy as np
from fastapi import APIRouter, HTTPException
from PIL import Image

from backend.api.house_assets import build_scoped_mask, download_source_image_bytes, get_house, get_zones
from backend.api.schemas import RenderPreviewRequest, RenderPreviewResponse
from backend.engine.materials_catalog import get_material
from backend.renderer.instant_preview import render_instant_preview

router = APIRouter()


@router.post("/render/preview", response_model=RenderPreviewResponse, response_model_by_alias=True)
def render_preview(request: RenderPreviewRequest) -> RenderPreviewResponse:
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

    image = Image.open(BytesIO(download_source_image_bytes(house))).convert("RGB")
    dims = (house["image_width"], house["image_height"])
    zones = get_zones(request.house_id)

    composite = np.array(image)
    total_ms = 0.0
    for material_id in distinct_materials:
        zone_ids = [zid for zid, mid in request.assignments.items() if mid == material_id]
        mask_array = build_scoped_mask(zones, zone_ids, dims)

        result = render_instant_preview(
            image=image,
            inpaint_mask=Image.fromarray(mask_array),
            material_id=material_id,
        )
        total_ms += result.execution_time_ms

        mask_bool = mask_array > 128
        composite = np.where(mask_bool[:, :, None], np.array(result.preview_image), composite)

    final_image = Image.fromarray(composite)
    buffer = BytesIO()
    final_image.save(buffer, format="JPEG", quality=90)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

    return RenderPreviewResponse(
        material_ids=distinct_materials,
        image_data_uri=f"data:image/jpeg;base64,{encoded}",
        execution_time_ms=round(total_ms, 2),
        output_width=dims[0],
        output_height=dims[1],
    )
