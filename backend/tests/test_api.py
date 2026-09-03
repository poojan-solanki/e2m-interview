"""Tests for the Phase 5 FastAPI backend (backend/api/). Pure CPU, no GPU required."""

from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)


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

def test_render_preview_house1_returns_image():
    response = client.post(
        "/api/render/preview",
        json={"houseId": "house-1", "materialId": "stone_cladding"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["imageDataUri"].startswith("data:image/jpeg;base64,")
    assert data["outputWidth"] == 1600
    assert data["outputHeight"] == 1200
    assert data["materialId"] == "stone_cladding"


def test_render_preview_unknown_house_returns_404():
    response = client.post(
        "/api/render/preview",
        json={"houseId": "not_a_real_house", "materialId": "stone_cladding"},
    )
    assert response.status_code == 404


def test_render_preview_unknown_material_returns_400():
    response = client.post(
        "/api/render/preview",
        json={"houseId": "house-1", "materialId": "not_a_real_material"},
    )
    assert response.status_code == 400
