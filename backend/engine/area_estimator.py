"""Area & Metrology Estimator for Building Facades.

Implements optical pinhole projection, standard architectural reference calibration,
metric conversion, and civil engineering opening deduction rules (IS 1200).
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Union


# Standard Architectural Reference Constants (India / International Residential)
STANDARD_DOOR_HEIGHT_M: float = 2.10   # Standard entrance door height in meters (~6.89 ft)
STANDARD_DOOR_WIDTH_M: float = 0.90    # Standard entrance door width in meters (~2.95 ft)
STANDARD_FLOOR_HEIGHT_M: float = 3.00   # Single residential floor-to-floor height in meters (~9.84 ft)
STANDARD_WINDOW_HEIGHT_M: float = 1.20  # Typical residential window height in meters (~3.94 ft)

# Conversion factors
METERS_TO_FEET: float = 3.280839895
SQ_METERS_TO_SQ_FEET: float = 10.76391041671


def meters_to_feet(meters: float) -> float:
    """Converts linear meters to feet."""
    return meters * METERS_TO_FEET


def feet_to_meters(feet: float) -> float:
    """Converts linear feet to meters."""
    return feet / METERS_TO_FEET


def sq_meters_to_sq_feet(sq_meters: float) -> float:
    """Converts square meters to square feet."""
    return sq_meters * SQ_METERS_TO_SQ_FEET


def sq_feet_to_sq_meters(sq_feet: float) -> float:
    """Converts square feet to square meters."""
    return sq_feet / SQ_METERS_TO_SQ_FEET


# -------------------------------------------------------------------------
# 1. Reference Object Calibration (Tier 1 Primary Anchor)
# -------------------------------------------------------------------------

@dataclass(frozen=True)
class ScaleFactor:
    """Encapsulates spatial scale derived from reference calibration."""
    meters_per_pixel: float
    feet_per_pixel: float
    sq_meters_per_sq_pixel: float
    sq_feet_per_sq_pixel: float

    def pixel_length_to_feet(self, pixels: float) -> float:
        """Converts pixel distance to linear feet."""
        return round(pixels * self.feet_per_pixel, 2)

    def pixel_length_to_meters(self, pixels: float) -> float:
        """Converts pixel distance to linear meters."""
        return round(pixels * self.meters_per_pixel, 3)

    def pixel_area_to_sq_feet(self, pixel_area: float) -> float:
        """Converts pixel area to square feet."""
        return round(pixel_area * self.sq_feet_per_sq_pixel, 2)

    def pixel_area_to_sq_meters(self, pixel_area: float) -> float:
        """Converts pixel area to square meters."""
        return round(pixel_area * self.sq_meters_per_sq_pixel, 3)


def calculate_scale_factor_from_reference(
    reference_dimension_m: float,
    reference_pixels: float,
) -> ScaleFactor:
    """Computes spatial scale factor given a known physical dimension and its pixel span.
    
    Example:
        If a standard entrance door (2.10 m) spans 350 pixels vertically:
        scale = calculate_scale_factor_from_reference(2.10, 350.0)
    """
    if reference_pixels <= 0:
        raise ValueError("Reference pixel measurement must be greater than zero.")
    if reference_dimension_m <= 0:
        raise ValueError("Reference physical dimension must be greater than zero.")

    meters_per_px = reference_dimension_m / reference_pixels
    feet_per_px = meters_per_px * METERS_TO_FEET
    sq_m_per_px2 = meters_per_px ** 2
    sq_ft_per_px2 = feet_per_px ** 2

    return ScaleFactor(
        meters_per_pixel=meters_per_px,
        feet_per_pixel=feet_per_px,
        sq_meters_per_sq_pixel=sq_m_per_px2,
        sq_feet_per_sq_pixel=sq_ft_per_px2,
    )


# -------------------------------------------------------------------------
# 2. Pinhole Optical Projection (Tier 2 EXIF Secondary Cross-Check)
# -------------------------------------------------------------------------

def calculate_focal_length_pixels(
    focal_length_mm: float,
    sensor_width_mm: float,
    image_width_px: int,
) -> float:
    """Computes camera focal length in pixels using pinhole geometry.
    
    Formula:
        f_pixels = (focal_length_mm * image_width_px) / sensor_width_mm
    """
    if sensor_width_mm <= 0 or image_width_px <= 0 or focal_length_mm <= 0:
        raise ValueError("Focal length, sensor width, and image width must all be positive numbers.")
    return (focal_length_mm * image_width_px) / sensor_width_mm


def calculate_real_dimension_pinhole(
    pixel_dimension: float,
    distance_m: float,
    focal_length_pixels: float,
) -> float:
    """Calculates physical dimension in meters using pinhole projection.
    
    Formula:
        Real Dimension (m) = (pixel_dimension * distance_m) / focal_length_pixels
    """
    if focal_length_pixels <= 0:
        raise ValueError("Focal length in pixels must be greater than zero.")
    if distance_m <= 0:
        raise ValueError("Distance from camera must be greater than zero.")
    return (pixel_dimension * distance_m) / focal_length_pixels


def calculate_area_pinhole(
    pixel_width: float,
    pixel_height: float,
    distance_m: float,
    focal_length_pixels: float,
) -> Tuple[float, float]:
    """Calculates physical surface area in square meters and square feet using pinhole model.
    
    Returns:
        (area_sq_meters, area_sq_feet)
    """
    real_width_m = calculate_real_dimension_pinhole(pixel_width, distance_m, focal_length_pixels)
    real_height_m = calculate_real_dimension_pinhole(pixel_height, distance_m, focal_length_pixels)
    area_sq_m = real_width_m * real_height_m
    area_sq_ft = sq_meters_to_sq_feet(area_sq_m)
    return round(area_sq_m, 2), round(area_sq_ft, 2)


# -------------------------------------------------------------------------
# 3. Civil Engineering Opening Deduction Rule (IS 1200 Standard)
# -------------------------------------------------------------------------

@dataclass(frozen=True)
class AreaDeductionResult:
    """Summary of gross area, opening deductions, and net workable area."""
    gross_area_sqft: float
    total_deductions_sqft: float
    net_area_sqft: float
    deduction_percentage: float

    def to_dict(self) -> dict:
        return {
            "gross_area_sqft": self.gross_area_sqft,
            "total_deductions_sqft": self.total_deductions_sqft,
            "net_area_sqft": self.net_area_sqft,
            "deduction_percentage": self.deduction_percentage,
        }


def compute_net_area(
    gross_area_sqft: float,
    openings: Union[float, List[Union[float, dict, Tuple[float, float]]]] = 0.0,
) -> AreaDeductionResult:
    """Applies civil engineering opening deduction rule to compute net workable area.
    
    Contractors order paint/stone only for the net surface, deducting window and door openings.
    
    Args:
        gross_area_sqft: Total surface area of the wall including openings.
        openings: Can be:
            - A float representing total openings area in sq ft
            - A list of opening areas in sq ft [24.0, 36.0]
            - A list of (width_ft, height_ft) tuples [(4.0, 6.0), (3.0, 7.0)]
            - A list of dicts with 'area_sqft' or ('width_ft' and 'height_ft')
            
    Returns:
        AreaDeductionResult with gross, deductions, net area, and deduction %.
    """
    if gross_area_sqft < 0:
        raise ValueError("Gross area cannot be negative.")

    total_deductions = 0.0

    if isinstance(openings, (int, float)):
        total_deductions = float(openings)
    elif isinstance(openings, list):
        for item in openings:
            if isinstance(item, (int, float)):
                total_deductions += float(item)
            elif isinstance(item, tuple) and len(item) == 2:
                w, h = item
                total_deductions += float(w) * float(h)
            elif isinstance(item, dict):
                if "area_sqft" in item:
                    total_deductions += float(item["area_sqft"])
                elif "width_ft" in item and "height_ft" in item:
                    total_deductions += float(item["width_ft"]) * float(item["height_ft"])

    # Civil safeguard: net area cannot be negative
    total_deductions = min(total_deductions, gross_area_sqft)
    net_area = max(0.0, gross_area_sqft - total_deductions)

    pct = round((total_deductions / gross_area_sqft * 100.0), 2) if gross_area_sqft > 0 else 0.0

    return AreaDeductionResult(
        gross_area_sqft=round(gross_area_sqft, 2),
        total_deductions_sqft=round(total_deductions, 2),
        net_area_sqft=round(net_area, 2),
        deduction_percentage=pct,
    )
