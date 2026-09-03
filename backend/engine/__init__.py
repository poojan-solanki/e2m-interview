"""Calculation and takeoff engine package."""
from .materials_catalog import (
    Material,
    MaterialCategory,
    MATERIALS_CATALOG,
    get_material,
    list_materials,
)
from .area_estimator import (
    STANDARD_DOOR_HEIGHT_M,
    STANDARD_DOOR_WIDTH_M,
    STANDARD_FLOOR_HEIGHT_M,
    calculate_scale_factor_from_reference,
    calculate_focal_length_pixels,
    calculate_real_dimension_pinhole,
    calculate_area_pinhole,
    compute_net_area,
)
from .boq_calculator import (
    BoQLineItem,
    BoQSummary,
    ZoneInput,
    calculate_boq,
)
from .report_generator import (
    generate_ascii_report,
    generate_html_report,
    generate_json_report,
)

__all__ = [
    "Material",
    "MaterialCategory",
    "MATERIALS_CATALOG",
    "get_material",
    "list_materials",
    "STANDARD_DOOR_HEIGHT_M",
    "STANDARD_DOOR_WIDTH_M",
    "STANDARD_FLOOR_HEIGHT_M",
    "calculate_scale_factor_from_reference",
    "calculate_focal_length_pixels",
    "calculate_real_dimension_pinhole",
    "calculate_area_pinhole",
    "compute_net_area",
    "BoQLineItem",
    "BoQSummary",
    "ZoneInput",
    "calculate_boq",
    "generate_ascii_report",
    "generate_html_report",
    "generate_json_report",
]
