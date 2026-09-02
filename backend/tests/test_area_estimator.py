"""Unit tests for area estimator and metrology calculations."""

import pytest
from backend.engine.area_estimator import (
    STANDARD_DOOR_HEIGHT_M,
    STANDARD_DOOR_WIDTH_M,
    STANDARD_FLOOR_HEIGHT_M,
    calculate_scale_factor_from_reference,
    calculate_focal_length_pixels,
    calculate_real_dimension_pinhole,
    calculate_area_pinhole,
    compute_net_area,
    meters_to_feet,
    feet_to_meters,
    sq_meters_to_sq_feet,
    sq_feet_to_sq_meters,
)


def test_unit_conversions():
    """Verify basic length and area conversions."""
    assert round(meters_to_feet(1.0), 4) == 3.2808
    assert round(feet_to_meters(3.280839895), 4) == 1.0
    assert round(sq_meters_to_sq_feet(1.0), 4) == 10.7639
    assert round(sq_feet_to_sq_meters(10.76391041671), 4) == 1.0


def test_reference_calibration_standard_door():
    """Verify calibration using standard 2.1m entrance door."""
    # Suppose standard door (2.10m) spans 350 pixels vertically
    scale = calculate_scale_factor_from_reference(
        reference_dimension_m=STANDARD_DOOR_HEIGHT_M,
        reference_pixels=350.0,
    )
    assert scale.meters_per_pixel == pytest.approx(0.006, rel=1e-3)
    
    # A wall spanning 1050 pixels should be 6.30 meters (approx 20.67 ft)
    real_m = scale.pixel_length_to_meters(1050.0)
    real_ft = scale.pixel_length_to_feet(1050.0)
    assert real_m == pytest.approx(6.30, abs=0.01)
    assert real_ft == pytest.approx(20.67, abs=0.05)


def test_reference_calibration_invalid_inputs():
    """Verify ValueError on zero or negative reference values."""
    with pytest.raises(ValueError):
        calculate_scale_factor_from_reference(0.0, 300.0)
    with pytest.raises(ValueError):
        calculate_scale_factor_from_reference(2.1, 0.0)
    with pytest.raises(ValueError):
        calculate_scale_factor_from_reference(2.1, -100.0)


def test_pinhole_optical_projection():
    """Verify pinhole camera focal length and real-dimension math."""
    # Typical phone: 26mm equivalent on 1/1.7" sensor (~7.6mm width), 4000px image
    f_px = calculate_focal_length_pixels(
        focal_length_mm=26.0,
        sensor_width_mm=7.6,
        image_width_px=4000,
    )
    assert f_px > 0
    # Expected f_px ≈ 13684.21
    assert round(f_px, 1) == 13684.2

    # At distance D = 10 meters, an object of 1368.42 pixels should be approx 1.0 meter
    real_dim = calculate_real_dimension_pinhole(
        pixel_dimension=1368.421,
        distance_m=10.0,
        focal_length_pixels=f_px,
    )
    assert real_dim == pytest.approx(1.0, abs=0.01)


def test_pinhole_area_calculation():
    """Verify area calculation from pixel dimensions and distance."""
    # 2000 x 1000 pixels at D = 10m with f_px = 10000 -> width = 2m, height = 1m -> 2 sq m
    area_sqm, area_sqft = calculate_area_pinhole(
        pixel_width=2000.0,
        pixel_height=1000.0,
        distance_m=10.0,
        focal_length_pixels=10000.0,
    )
    assert area_sqm == pytest.approx(2.0, abs=0.01)
    assert area_sqft == pytest.approx(21.53, abs=0.05)


def test_compute_net_area_no_openings():
    """Verify net area when no openings exist."""
    res = compute_net_area(gross_area_sqft=1200.0, openings=0.0)
    assert res.gross_area_sqft == 1200.0
    assert res.total_deductions_sqft == 0.0
    assert res.net_area_sqft == 1200.0
    assert res.deduction_percentage == 0.0


def test_compute_net_area_scalar_openings():
    """Verify net area with float opening value."""
    res = compute_net_area(gross_area_sqft=1000.0, openings=150.0)
    assert res.gross_area_sqft == 1000.0
    assert res.total_deductions_sqft == 150.0
    assert res.net_area_sqft == 850.0
    assert res.deduction_percentage == 15.0


def test_compute_net_area_tuple_list_openings():
    """Verify net area when openings are given as (width, height) tuples."""
    # Two windows: 4x5 = 20 sq ft, 3x6 = 18 sq ft -> total 38 sq ft
    openings = [(4.0, 5.0), (3.0, 6.0)]
    res = compute_net_area(gross_area_sqft=500.0, openings=openings)
    assert res.total_deductions_sqft == 38.0
    assert res.net_area_sqft == 462.0
    assert res.deduction_percentage == 7.6


def test_compute_net_area_dict_list_openings():
    """Verify net area when openings are given as dicts."""
    openings = [
        {"area_sqft": 40.0},
        {"width_ft": 5.0, "height_ft": 4.0},  # 20 sq ft
    ]
    res = compute_net_area(gross_area_sqft=400.0, openings=openings)
    assert res.total_deductions_sqft == 60.0
    assert res.net_area_sqft == 340.0


def test_compute_net_area_safeguard_overdeduction():
    """Verify safeguard: deductions cannot exceed gross area (net area cannot be negative)."""
    res = compute_net_area(gross_area_sqft=200.0, openings=250.0)
    assert res.gross_area_sqft == 200.0
    assert res.total_deductions_sqft == 200.0
    assert res.net_area_sqft == 0.0
    assert res.deduction_percentage == 100.0


def test_compute_net_area_negative_gross_raises():
    """Verify negative gross area raises ValueError."""
    with pytest.raises(ValueError):
        compute_net_area(-100.0)
