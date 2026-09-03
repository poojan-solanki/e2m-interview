"""Tests for the Phase 5 FastAPI backend (backend/api/).

All cases here are pure CPU / fast-fail validation, no GPU required. Real
SAM 3 segmentation and ControlNet+SD rendering are verified manually against
a live `uvicorn` process instead — see the notes in the /api/segment and
/api/render/neural/jobs sections below for why.
"""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.api import supabase_client as db
from backend.api.main import app

client = TestClient(app)

FIXTURE_HOUSE_ID = "test-fixture-house"


@pytest.fixture(scope="module")
def fixture_house_id():
    """A small, deterministic house in Supabase for tests that need *some* valid
    house to point at (e.g. exercising the material-validation path) without
    running real SAM 3 segmentation. Self-contained (generates its own image, no
    dependency on external sample files) and upserted idempotently, safe to leave.
    """
    if not db.is_configured():
        pytest.skip("Supabase not configured (SUPABASE_SERVICE_ROLE_KEY missing)")

    buf = BytesIO()
    Image.new("RGB", (1200, 800), color=(180, 180, 180)).save(buf, format="JPEG")
    db.upload_bytes(f"houses/{FIXTURE_HOUSE_ID}/source.jpg", buf.getvalue(), "image/jpeg")
    db.upsert_row(
        "houses",
        {
            "id": FIXTURE_HOUSE_ID,
            "source_image_path": f"houses/{FIXTURE_HOUSE_ID}/source.jpg",
            "image_width": 1200,
            "image_height": 800,
            "total_gross_wall_area_sqft": 100.0,
            "net_paintable_wall_area_sqft": 90.0,
            "scale_factor_sqft_per_sq_pixel": 0.001,
            "calibration_method": "test fixture",
            "quality_warnings": [],
        },
        on_conflict="id",
    )
    # Two non-overlapping halves so a multi-material composite is actually
    # exercised (different region, different material, verifiably distinct).
    for zone_key, x0, x1 in [("zone_01_wall", 0, 600), ("zone_02_wall", 600, 1200)]:
        db.upsert_row(
            "zones",
            {
                "house_id": FIXTURE_HOUSE_ID,
                "zone_key": zone_key,
                "label": "wall",
                "display_name": zone_key,
                "category": "surface",
                "is_protected": False,
                "confidence": 0.9,
                "polygon": [[x0, 0], [x1, 0], [x1, 800], [x0, 800]],
                "bbox": [x0, 0, x1, 800],
                "pixel_area": (x1 - x0) * 800,
                "gross_area_sqft": 45.0,
                "deductions_sqft": 0.0,
                "net_area_sqft": 45.0,
                "running_feet": 0.0,
                "recommended_materials": ["weatherproof_paint", "stone_cladding", "wpc_panels"],
            },
            on_conflict="house_id,zone_key",
        )
    return FIXTURE_HOUSE_ID


# -------------------------------------------------------------------------
# POST /api/boq
# -------------------------------------------------------------------------

def test_boq_single_sqft_zone_matches_hand_computed_values():
    """Mirrors backend/tests/test_boq.py's documented 1200 sqft / weatherproof_paint case."""
    response = client.post(
        "/api/boq",
        json={
            "zones": [
                {
                    "zoneId": "wall_01",
                    "zoneName": "Front Wall",
                    "materialId": "weatherproof_paint",
                    "unit": "sq_ft",
                    "grossAreaSqft": 1200.0,
                    "deductionsSqft": 0.0,
                    "runningFeet": 0.0,
                }
            ],
            "rateOverrides": {},
            "contingencyPct": 5.0,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    item = data["items"][0]

    assert item["netArea"] == 1200.0
    assert item["grossMaterialArea"] == 1320.0
    assert item["materialCostInr"] == 33000.0
    assert item["laborCostInr"] == 14400.0
    assert item["lineTotalInr"] == 47400.0


def test_boq_linear_railing_zone_uses_running_feet():
    response = client.post(
        "/api/boq",
        json={
            "zones": [
                {
                    "zoneId": "rail_01",
                    "zoneName": "Balcony Railing",
                    "materialId": "glass_railing",
                    "unit": "Rft",
                    "grossAreaSqft": 0.0,
                    "deductionsSqft": 0.0,
                    "runningFeet": 28.0,
                }
            ],
        },
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["netArea"] == 28.0
    assert item["unit"] == "Rft"


def test_boq_zone_rate_override_applies_to_material():
    response = client.post(
        "/api/boq",
        json={
            "zones": [
                {
                    "zoneId": "wall_01",
                    "zoneName": "Front Wall",
                    "materialId": "weatherproof_paint",
                    "unit": "sq_ft",
                    "grossAreaSqft": 1000.0,
                    "deductionsSqft": 0.0,
                    "runningFeet": 0.0,
                }
            ],
            "rateOverrides": {"wall_01": {"materialRateInr": 30.0}},
        },
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["unitMaterialRateInr"] == 30.0


def test_boq_unknown_material_returns_400():
    response = client.post(
        "/api/boq",
        json={
            "zones": [
                {
                    "zoneId": "wall_01",
                    "zoneName": "Front Wall",
                    "materialId": "not_a_real_material",
                    "unit": "sq_ft",
                    "grossAreaSqft": 100.0,
                    "deductionsSqft": 0.0,
                    "runningFeet": 0.0,
                }
            ],
        },
    )

    assert response.status_code == 400


# -------------------------------------------------------------------------
# POST /api/render/preview
# -------------------------------------------------------------------------

def test_render_preview_fixture_house_returns_image(fixture_house_id):
    response = client.post(
        "/api/render/preview",
        json={"houseId": fixture_house_id, "assignments": {"zone_01_wall": "stone_cladding"}},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["imageDataUri"].startswith("data:image/jpeg;base64,")
    assert data["outputWidth"] == 1200
    assert data["outputHeight"] == 800
    assert data["materialIds"] == ["stone_cladding"]


def test_render_preview_multi_material_composites_both(fixture_house_id):
    response = client.post(
        "/api/render/preview",
        json={
            "houseId": fixture_house_id,
            "assignments": {"zone_01_wall": "stone_cladding", "zone_02_wall": "wpc_panels"},
        },
    )
    assert response.status_code == 200
    assert response.json()["materialIds"] == ["stone_cladding", "wpc_panels"]


def test_render_preview_unknown_house_returns_404():
    response = client.post(
        "/api/render/preview",
        json={"houseId": "not_a_real_house", "assignments": {"zone_01_wall": "stone_cladding"}},
    )
    assert response.status_code == 404


def test_render_preview_unknown_material_returns_400(fixture_house_id):
    response = client.post(
        "/api/render/preview",
        json={"houseId": fixture_house_id, "assignments": {"zone_01_wall": "not_a_real_material"}},
    )
    assert response.status_code == 400


# -------------------------------------------------------------------------
# POST /api/segment (GPU required for a real run — see note below)
# -------------------------------------------------------------------------
# NOTE: a test that actually invokes FacadeSegmenter here (loading the SAM 3
# checkpoint via torch.load) reliably segfaults the whole pytest process on
# this Windows machine — the crash is inside Starlette TestClient's threaded
# anyio portal, not this endpoint's code. Real segmentation is verified
# manually against a live `uvicorn` process instead (a normal asyncio
# context, not TestClient's thread portal) — see SESSION_HANDOVER.md.


def test_segment_rejects_non_image_upload():
    response = client.post(
        "/api/segment",
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


# -------------------------------------------------------------------------
# POST /api/render/neural/jobs (GPU required for a real render — only the
# fast-fail validation paths are exercised here; a full render takes ~4-5
# minutes and is verified manually, not on every test run)
# -------------------------------------------------------------------------

def test_neural_render_job_unknown_house_returns_404():
    response = client.post(
        "/api/render/neural/jobs",
        json={"houseId": "not_a_real_house", "assignments": {"zone_01_wall": "stone_cladding"}},
    )
    assert response.status_code == 404


def test_neural_render_job_unknown_material_returns_400(fixture_house_id):
    response = client.post(
        "/api/render/neural/jobs",
        json={"houseId": fixture_house_id, "assignments": {"zone_01_wall": "not_a_real_material"}},
    )
    assert response.status_code == 400


def test_neural_render_job_status_unknown_id_returns_404():
    response = client.get("/api/render/neural/jobs/not-a-real-job-id")
    assert response.status_code == 404
