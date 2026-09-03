"""Spatial Area & Geometry Calculator for Segmented Facade Polygons (Requirement 5.5).

Computes 2D polygon areas via Shoelace formula, linear railing perimeters,
scale calibration from detected reference objects, and net workable areas with opening deductions.
"""

import math
from typing import Dict, List, Optional, Tuple, Union
import numpy as np

from backend.engine.area_estimator import (
    STANDARD_DOOR_HEIGHT_M,
    STANDARD_DOOR_WIDTH_M,
    ScaleFactor,
    calculate_scale_factor_from_reference,
    compute_net_area,
)


def polygon_area_pixels(polygon: Union[List, np.ndarray]) -> float:
    """Computes the 2D surface area of a polygon in pixels using the Shoelace formula.
    
    Formula:
        A = 0.5 * |sum(x_i * y_{i+1} - x_{i+1} * y_i)|
    """
    pts = np.asarray(polygon, dtype=np.float64)
    if len(pts) < 3:
        return 0.0

    # Ensure shape is (N, 2)
    if pts.ndim > 2:
        pts = pts.reshape(-1, 2)

    x = pts[:, 0]
    y = pts[:, 1]
    # Vectorized shoelace formula using np.roll
    area = 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
    return float(area)


def polygon_perimeter_pixels(polygon: Union[List, np.ndarray]) -> float:
    """Computes perimeter length of a polygon in pixel space."""
    pts = np.asarray(polygon, dtype=np.float64)
    if len(pts) < 2:
        return 0.0
    if pts.ndim > 2:
        pts = pts.reshape(-1, 2)

    diffs = np.diff(pts, axis=0)
    segment_lengths = np.hypot(diffs[:, 0], diffs[:, 1])
    # Add closing segment
    closing_len = math.hypot(pts[-1, 0] - pts[0, 0], pts[-1, 1] - pts[0, 1])
    return float(np.sum(segment_lengths) + closing_len)


def polygon_bounding_box(polygon: Union[List, np.ndarray]) -> Tuple[int, int, int, int]:
    """Computes axis-aligned bounding box (x_min, y_min, x_max, y_max) in integer pixels."""
    pts = np.asarray(polygon, dtype=np.float64)
    if pts.ndim > 2:
        pts = pts.reshape(-1, 2)
    if len(pts) == 0:
        return (0, 0, 0, 0)
    x_min = int(np.floor(np.min(pts[:, 0])))
    y_min = int(np.floor(np.min(pts[:, 1])))
    x_max = int(np.ceil(np.max(pts[:, 0])))
    y_max = int(np.ceil(np.max(pts[:, 1])))
    return (x_min, y_min, x_max, y_max)


def calibrate_scale_from_detection(
    detected_zones: List[dict],
    image_shape: Tuple[int, int],  # (height, width)
    known_door_height_m: float = STANDARD_DOOR_HEIGHT_M,
    fallback_meters_per_pixel: Optional[float] = None,
) -> Tuple[ScaleFactor, str]:
    """Derives metric ScaleFactor by finding an entrance door reference, or using intelligent geometric prior.
    
    Returns:
        (scale_factor, calibration_method_description)
    """
    img_h, img_w = image_shape[:2]

    # 1. Search for a detected door object
    door_candidates = [z for z in detected_zones if z.get("label", "").lower() in ["door", "entrance", "entrance_door"]]
    if door_candidates:
        # Choose the candidate with highest confidence or most plausible aspect ratio
        best_door = max(door_candidates, key=lambda z: z.get("confidence", 0.0))
        bbox = best_door.get("bbox")
        if bbox:
            _, y_min, _, y_max = bbox
            door_height_px = float(y_max - y_min)
            if door_height_px > 30:  # Plausible pixel height
                scale = calculate_scale_factor_from_reference(known_door_height_m, door_height_px)
                method = f"Calibrated via detected door (h={door_height_px:.0f}px = {known_door_height_m:.2f}m)"
                return scale, method

    # 2. Check for manual fallback
    if fallback_meters_per_pixel and fallback_meters_per_pixel > 0:
        scale = ScaleFactor(
            meters_per_pixel=fallback_meters_per_pixel,
            feet_per_pixel=fallback_meters_per_pixel * 3.28084,
            sq_meters_per_sq_pixel=fallback_meters_per_pixel ** 2,
            sq_feet_per_sq_pixel=(fallback_meters_per_pixel * 3.28084) ** 2,
        )
        return scale, f"User-specified scale ({fallback_meters_per_pixel:.4f} m/px)"

    # 3. Architectural Prior Fallback:
    # In typical residential exterior photos taken from street/driveway:
    # A 2-story building (~6.5m facade) occupies ~60-75% of the vertical frame height.
    # Therefore, 1 vertical pixel ≈ (6.5m / (img_h * 0.70)).
    estimated_facade_height_m = 6.5
    estimated_facade_px = max(100.0, float(img_h) * 0.70)
    scale = calculate_scale_factor_from_reference(estimated_facade_height_m, estimated_facade_px)
    method = f"Architectural geometric prior (estimated 2-story facade height {estimated_facade_height_m:.1f}m = {estimated_facade_px:.0f}px)"
    return scale, method


def compute_zone_measurements(
    polygon: Union[List, np.ndarray],
    scale_factor: ScaleFactor,
    is_linear: bool = False,
) -> dict:
    """Computes physical area and perimeter metrics for a polygon."""
    px_area = polygon_area_pixels(polygon)
    px_perim = polygon_perimeter_pixels(polygon)
    bbox = polygon_bounding_box(polygon)

    area_sqft = scale_factor.pixel_area_to_sq_feet(px_area)
    area_sqm = scale_factor.pixel_area_to_sq_meters(px_area)
    perim_ft = scale_factor.pixel_length_to_feet(px_perim)
    perim_m = scale_factor.pixel_length_to_meters(px_perim)

    # For railings: linear running length is estimated as the horizontal top span or half perimeter
    bbox_w_px = max(0, bbox[2] - bbox[0])
    running_ft = scale_factor.pixel_length_to_feet(bbox_w_px)

    return {
        "pixel_area": round(px_area, 1),
        "pixel_perimeter": round(px_perim, 1),
        "bounding_box": list(bbox),
        "area_sqft": area_sqft,
        "area_sqm": area_sqm,
        "perimeter_ft": perim_ft,
        "perimeter_m": perim_m,
        "running_feet": running_ft if is_linear else 0.0,
    }
