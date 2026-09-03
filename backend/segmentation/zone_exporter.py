"""Export and Serialization of Segmentation Masks and Zones JSON (Requirement 5.2).

Generates individual zone binary masks, combined renovation inpaint masks,
color-coded visualization overlays, and structured zones.json metadata.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import cv2
import numpy as np

from .segmenter import SegmentationResult, SegmentedZone


# Distinct aesthetic colors (BGR format for OpenCV) for each architectural category
ZONE_COLORS = {
    "wall": (235, 164, 52),            # Sky blue (renovatable wall)
    "pillar": (0, 215, 255),           # Gold / Yellow
    "balcony_railing": (39, 127, 255), # Amber / Orange (balcony)
    "window": (180, 105, 255),         # Hot Pink / Magenta (Protected opening)
    "door": (147, 20, 255),            # Deep Magenta (Protected opening)
    "roof_parapet": (30, 200, 100),    # Green (roof overhang / chhajja)
    "person": (0, 0, 255),             # Red (protected human)
    "car": (120, 120, 120),            # Grey (foreground)
    "surface": (200, 200, 200),        # Neutral grey
}


def draw_polygon_mask(
    dimensions: Tuple[int, int],  # (width, height)
    polygon: List[List[float]],
) -> np.ndarray:
    """Draws a binary 8-bit mask (255 inside polygon, 0 outside)."""
    w, h = dimensions
    mask = np.zeros((h, w), dtype=np.uint8)
    if len(polygon) < 3:
        return mask
    pts = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))
    cv2.fillPoly(mask, [pts], 255)
    return mask


def generate_composite_overlay(
    image: np.ndarray,
    zones: List[SegmentedZone],
    alpha: float = 0.45,
) -> np.ndarray:
    """Creates a semi-transparent color-coded visualization of all detected facade zones."""
    overlay = image.copy()
    h, w = image.shape[:2]

    for zone in zones:
        if len(zone.polygon) < 3:
            continue

        color = ZONE_COLORS.get(zone.label, (180, 180, 180))
        pts = np.array(zone.polygon, dtype=np.int32).reshape((-1, 1, 2))

        # Fill semi-transparent polygon
        cv2.fillPoly(overlay, [pts], color)

    # Blend overlay with original
    blended = cv2.addWeighted(overlay, alpha, image, 1.0 - alpha, 0)

    # Draw solid boundary contours and readable text labels on top of blended image
    for zone in zones:
        if len(zone.polygon) < 3:
            continue

        color = ZONE_COLORS.get(zone.label, (180, 180, 180))
        pts = np.array(zone.polygon, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(blended, [pts], isClosed=True, color=color, thickness=2)

        # Place label near centroid or top-left of bbox
        x_min, y_min, x_max, y_max = zone.bbox
        text_x = max(10, min(w - 180, x_min + 5))
        text_y = max(20, min(h - 10, y_min + 20))

        label_text = f"{zone.label.upper()} ({zone.net_area_sqft:.0f} sqft)"
        if zone.category == "railing":
            label_text = f"{zone.label.upper()} ({zone.running_feet:.1f} Rft)"

        # Text background badge for readability
        (text_w, text_h), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(blended, (text_x - 2, text_y - text_h - 4), (text_x + text_w + 4, text_y + baseline), (20, 20, 20), -1)
        cv2.putText(blended, label_text, (text_x, text_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    return blended


def export_segmentation_artifacts(
    result: SegmentationResult,
    output_dir: Union[str, Path],
    base_image: Optional[np.ndarray] = None,
) -> Dict[str, str]:
    """Saves zones.json, binary masks, inpaint mask, and composite overlay preview.
    
    Args:
        result: SegmentationResult object.
        output_dir: Destination directory path.
        base_image: Optional BGR numpy array of the original photo.
        
    Returns:
        Dict mapping artifact keys to their saved absolute file paths.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    w, h = result.image_dimensions

    # Load base image if not passed
    if base_image is None:
        if Path(result.image_path).exists():
            base_image = cv2.imread(result.image_path)
        else:
            base_image = np.zeros((h, w, 3), dtype=np.uint8)

    artifacts = {}

    # 1. Save individual binary masks and cache them in memory
    zone_masks = {}
    for zone in result.zones:
        mask = draw_polygon_mask((w, h), zone.polygon)
        mask_filename = zone.mask_filename or f"{zone.id}_mask.png"
        mask_file_path = out_path / mask_filename
        cv2.imwrite(str(mask_file_path), mask)
        artifacts[f"mask_{zone.id}"] = str(mask_file_path)
        zone_masks[zone.id] = mask

    # 2. Build combined renovation inpaint mask using a strict 2-pass hierarchy
    # Pass 1: Union all renovatable surfaces (walls, pillars, parapets)
    combined_renovation_mask = np.zeros((h, w), dtype=np.uint8)
    for zone in result.zones:
        if not zone.is_protected:
            combined_renovation_mask = cv2.bitwise_or(combined_renovation_mask, zone_masks[zone.id])

    # Pass 2: Strictly subtract all protected openings (windows, doors) so they CANNOT be overwritten by walls
    kernel = np.ones((3, 3), np.uint8)
    for zone in result.zones:
        if zone.is_protected:
            # Dilate opening mask slightly (2px) to protect external window frames & mullions
            dilated_opening = cv2.dilate(zone_masks[zone.id], kernel, iterations=1)
            combined_renovation_mask = cv2.bitwise_and(
                combined_renovation_mask,
                cv2.bitwise_not(dilated_opening),
            )

    # 3. Save combined renovation mask for Phase 3 inpainting
    inpaint_mask_path = out_path / "renovation_inpaint_mask.png"
    cv2.imwrite(str(inpaint_mask_path), combined_renovation_mask)
    artifacts["renovation_inpaint_mask"] = str(inpaint_mask_path)

    # 3. Save composite overlay preview
    overlay_img = generate_composite_overlay(base_image, result.zones)
    overlay_path = out_path / "overlay_preview.png"
    cv2.imwrite(str(overlay_path), overlay_img)
    artifacts["overlay_preview"] = str(overlay_path)

    # 4. Save zones.json
    zones_json_path = out_path / "zones.json"
    with open(zones_json_path, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2)
    artifacts["zones_json"] = str(zones_json_path)

    return artifacts
