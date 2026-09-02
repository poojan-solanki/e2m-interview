"""Unit tests for BoQ calculation engine."""

import pytest
from backend.engine.boq_calculator import (
    ZoneInput,
    BoQLineItem,
    BoQSummary,
    calculate_boq,
)


def test_single_zone_paint_calculation():
    """Verify single zone paint calculation with standard rates."""
    zone = ZoneInput(
        zone_id="wall_01",
        zone_name="Front Wall",
        gross_area=1200.0,
        material_id="weatherproof_paint",
        openings=0.0,
    )

    summary = calculate_boq([zone], contingency_percentage=0.05)

    assert len(summary.items) == 1
    item = summary.items[0]

    # Net area = 1200 sq ft
    assert item.net_workable_area == 1200.0
    # Wastage 10% -> 120.0 sq ft allowance -> gross 1320.0 sq ft
    assert item.wastage_area_allowance == 120.0
    assert item.gross_material_area == 1320.0

    # Material cost: 1320 * 25 = ₹33,000
    assert item.material_cost_inr == 33000.0
    # Labor cost: 1200 * 12 = ₹14,400
    assert item.labor_cost_inr == 14400.0
    # Line total = ₹47,400
    assert item.line_total_inr == 47400.0

    # Subtotal and grand total
    assert summary.subtotal_inr == 47400.0
    # Contingency 5% of 47400 = 2370.0
    assert summary.contingency_amount_inr == 2370.0
    # Grand total = 47400 + 2370 = 49770.0
    assert summary.grand_total_inr == 49770.0


def test_single_zone_with_openings_deductions():
    """Verify stone cladding calculation with window deductions."""
    # 800 sq ft wall with 120 sq ft openings -> net 680 sq ft
    zone = ZoneInput(
        zone_id="accent_wall",
        zone_name="Portico Accent Wall",
        gross_area=800.0,
        material_id="stone_cladding",
        openings=120.0,
    )

    summary = calculate_boq([zone], contingency_percentage=0.05)
    item = summary.items[0]

    assert item.gross_surface_area == 800.0
    assert item.deductions_area == 120.0
    assert item.net_workable_area == 680.0

    # Stone cladding wastage = 15% -> 680 * 0.15 = 102 sq ft allowance -> gross 782 sq ft
    assert item.wastage_percentage == 15.0
    assert item.wastage_area_allowance == 102.0
    assert item.gross_material_area == 782.0

    # Material: 782 * ₹220 = ₹172,040
    assert item.material_cost_inr == 172040.0
    # Labor: 680 * ₹65 = ₹44,200
    assert item.labor_cost_inr == 44200.0
    assert item.line_total_inr == 216240.0


def test_linear_railing_calculation():
    """Verify linear railing calculation (Rft unit)."""
    # 24 Rft glass railing
    zone = ZoneInput(
        zone_id="railing_01",
        zone_name="Balcony Railing",
        gross_area=24.0,  # 24 running feet
        material_id="glass_railing",
        openings=0.0,
    )

    summary = calculate_boq([zone], contingency_percentage=0.05)
    item = summary.items[0]

    assert item.unit == "Rft"
    assert item.net_workable_area == 24.0
    # Wastage 5% -> 24 * 0.05 = 1.2 Rft -> 25.2 Rft gross
    assert item.wastage_area_allowance == 1.2
    assert item.gross_material_area == 25.2

    # Material: 25.2 * ₹1400 = ₹35,280
    assert item.material_cost_inr == 35280.0
    # Labor: 24 * ₹300 = ₹7,200
    assert item.labor_cost_inr == 7200.0
    assert item.line_total_inr == 42480.0


def test_rate_overrides():
    """Verify user ability to override material and labor rates dynamically."""
    zone = ZoneInput(
        zone_id="wall_01",
        zone_name="Front Wall",
        gross_area=100.0,
        material_id="weatherproof_paint",
        openings=0.0,
    )

    # Standard rates: mat=25, lab=12
    # Override: mat=20, lab=10
    overrides = {
        "weatherproof_paint": {
            "material_rate": 20.0,
            "labor_rate": 10.0,
        }
    }

    summary = calculate_boq([zone], rate_overrides=overrides, contingency_percentage=0.0)
    item = summary.items[0]

    # Gross area 100 + 10% = 110 sq ft
    # Mat cost: 110 * 20 = 2200
    # Lab cost: 100 * 10 = 1000
    # Total = 3200
    assert item.unit_material_rate_inr == 20.0
    assert item.unit_labor_rate_inr == 10.0
    assert item.material_cost_inr == 2200.0
    assert item.labor_cost_inr == 1000.0
    assert item.line_total_inr == 3200.0
    assert summary.grand_total_inr == 3200.0


def test_multi_zone_category_breakdown():
    """Verify multi-zone aggregation and category breakdowns."""
    zones = [
        ZoneInput(zone_id="z1", zone_name="Wall 1", gross_area=500.0, material_id="weatherproof_paint"),
        ZoneInput(zone_id="z2", zone_name="Pillars", gross_area=100.0, material_id="stone_cladding"),
        ZoneInput(zone_id="z3", zone_name="Balcony", gross_area=20.0, material_id="glass_railing"),
    ]

    summary = calculate_boq(zones, contingency_percentage=0.10)

    assert len(summary.items) == 3
    # Check category totals exist
    assert "paint" in summary.category_totals_inr
    assert "cladding" in summary.category_totals_inr
    assert "railing" in summary.category_totals_inr

    # Category totals sum to subtotal
    cat_sum = sum(summary.category_totals_inr.values())
    assert pytest.approx(summary.subtotal_inr, rel=1e-3) == cat_sum
    assert summary.contingency_percentage == 10.0
    assert summary.contingency_amount_inr == round(summary.subtotal_inr * 0.10, 2)
    assert summary.grand_total_inr == round(summary.subtotal_inr + summary.contingency_amount_inr, 2)


def test_empty_zones_returns_zero_summary():
    """Verify empty zones input returns valid zero summary without errors."""
    summary = calculate_boq([])
    assert summary.items == []
    assert summary.grand_total_inr == 0.0
    assert summary.subtotal_inr == 0.0
