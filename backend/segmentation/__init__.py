"""Segmentation and Facade Parsing Package."""

from .quality_checker import check_image_quality, ImageQualityReport
from .exif_reader import extract_exif, ExifMetadata
from .area_calculator import (
    polygon_area_pixels,
    polygon_perimeter_pixels,
    polygon_bounding_box,
    calibrate_scale_from_detection,
    compute_zone_measurements,
)
from .segmenter import (
    ARCHITECTURAL_CONCEPTS,
    CONCEPT_MAPPING,
    SegmentedZone,
    SegmentationResult,
    FacadeSegmenter,
)
from .zone_exporter import (
    export_segmentation_artifacts,
    generate_composite_overlay,
    draw_polygon_mask,
)

__all__ = [
    "check_image_quality",
    "ImageQualityReport",
    "extract_exif",
    "ExifMetadata",
    "polygon_area_pixels",
    "polygon_perimeter_pixels",
    "polygon_bounding_box",
    "calibrate_scale_from_detection",
    "compute_zone_measurements",
    "ARCHITECTURAL_CONCEPTS",
    "CONCEPT_MAPPING",
    "SegmentedZone",
    "SegmentationResult",
    "FacadeSegmenter",
    "export_segmentation_artifacts",
    "generate_composite_overlay",
    "draw_polygon_mask",
]
