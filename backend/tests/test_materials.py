"""Unit tests for materials catalog."""

import pytest
from backend.engine.materials_catalog import (
    Material,
    MaterialCategory,
    MATERIALS_CATALOG,
    get_material,
    list_materials,
)


def test_materials_catalog_completeness():
    """Verify that all core architectural material types are present."""
    expected_ids = {
        "weatherproof_paint",
        "textured_stucco",
        "stone_cladding",
        "vitrified_tiles",
        "glass_railing",
        "metal_railing",
        "wpc_panels",
    }
    assert expected_ids.issubset(set(MATERIALS_CATALOG.keys()))


def test_material_rates_and_coverage_positive():
    """Verify that all materials have non-zero positive rates, coverages, and wastage margins."""
    for mat_id, mat in MATERIALS_CATALOG.items():
        assert mat.material_rate_inr > 0, f"{mat_id} has non-positive material rate"
        assert mat.labor_rate_inr > 0, f"{mat_id} has non-positive labor rate"
        assert mat.total_rate_inr == mat.material_rate_inr + mat.labor_rate_inr
        assert mat.coverage_per_consumption_unit > 0, f"{mat_id} has non-positive coverage"
        assert 0.0 < mat.wastage_factor < 0.50, f"{mat_id} has unrealistic wastage factor: {mat.wastage_factor}"
        assert len(mat.recommended_zones) > 0, f"{mat_id} has no recommended zones"


def test_get_material_success_and_normalization():
    """Verify case-insensitive lookup with leading/trailing whitespace."""
    mat1 = get_material("weatherproof_paint")
    mat2 = get_material("  WEATHERPROOF_PAINT  ")
    assert mat1.id == "weatherproof_paint"
    assert mat2.id == "weatherproof_paint"
    assert mat1 == mat2


def test_get_material_unknown_raises_key_error():
    """Verify informative KeyError when requesting invalid material."""
    with pytest.raises(KeyError) as excinfo:
        get_material("non_existent_material_123")
    assert "not found" in str(excinfo.value)
    assert "weatherproof_paint" in str(excinfo.value)


def test_list_materials_filtering():
    """Verify category filtering for catalog listings."""
    all_materials = list_materials()
    assert len(all_materials) == len(MATERIALS_CATALOG)

    railings = list_materials(category=MaterialCategory.RAILING)
    assert len(railings) >= 2
    assert all(r.category == MaterialCategory.RAILING for r in railings)

    paints = list_materials(category=MaterialCategory.PAINT)
    assert any(p.id == "weatherproof_paint" for p in paints)


def test_material_consumption_math():
    """Verify exact calculation of base and gross material consumption."""
    paint = get_material("weatherproof_paint")
    # 65 sq ft / liter
    # For 130 sq ft: 130 / 65 = 2.0 liters net
    # With 10% wastage: 2.0 * 1.10 = 2.20 liters gross
    assert paint.calculate_consumption(130.0) == 2.0
    assert paint.calculate_gross_consumption(130.0) == 2.20


def test_material_to_dict():
    """Verify dict serialization."""
    stone = get_material("stone_cladding")
    data = stone.to_dict()
    assert data["id"] == "stone_cladding"
    assert data["material_rate_inr"] == 220.0
    assert data["labor_rate_inr"] == 65.0
    assert data["total_rate_inr"] == 285.0
    assert data["category"] == "cladding"
