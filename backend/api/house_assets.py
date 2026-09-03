"""Resolves a houseId to its source image + zone/scale data — all sourced from
Supabase (Postgres for structured rows, Storage for the image bytes). Nothing about
a house is retained on local disk between requests; see backend/api/supabase_client.py.
"""

from pathlib import Path
from typing import Iterable, List, Optional

import cv2
import numpy as np

from backend.api import supabase_client as db

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def get_house(house_id: str) -> Optional[dict]:
    """Fetches a house's row (source_image_path, dimensions, scale factor, ...)."""
    return db.get_row("houses", "id", house_id)


def get_zones(house_id: str) -> List[dict]:
    """Fetches a house's zones, normalized to the id/label/polygon shape the rest
    of the backend (mask-building, API responses) already expects — DB rows use
    `zone_key` for what the rest of the codebase calls a zone's `id`.
    """
    rows = db.query("zones", {"house_id": house_id})
    return [{**row, "id": row["zone_key"]} for row in rows]


def download_source_image_bytes(house: dict) -> bytes:
    return db.download_bytes(house["source_image_path"])


def _draw_polygon_mask(dims: tuple[int, int], polygon: List[List[float]]) -> np.ndarray:
    """Draws a binary 8-bit mask (255 inside polygon, 0 outside). Mirrors
    backend/segmentation/zone_exporter.py's version — reimplemented locally so this
    module doesn't have to import the (torch/sam3-heavy) segmentation package just
    for a two-line cv2 utility.
    """
    w, h = dims
    mask = np.zeros((h, w), dtype=np.uint8)
    if len(polygon) < 3:
        return mask
    pts = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))
    cv2.fillPoly(mask, [pts], 255)
    return mask


def build_combined_mask(zones: List[dict], dims: tuple[int, int]) -> np.ndarray:
    """Builds the blanket "everything renovatable" mask straight from zone polygon
    data — replaces the old renovation_inpaint_mask.png file that used to be
    generated once and stored on disk. Used by /api/render/preview and as the
    /api/render/neural fallback when a request doesn't scope to specific zoneIds.
    """
    combined = np.zeros((dims[1], dims[0]), dtype=np.uint8)
    for zone in zones:
        if not zone["is_protected"]:
            combined = cv2.bitwise_or(combined, _draw_polygon_mask(dims, zone["polygon"]))

    kernel = np.ones((3, 3), np.uint8)
    for zone in zones:
        if zone["is_protected"]:
            dilated = cv2.dilate(_draw_polygon_mask(dims, zone["polygon"]), kernel, iterations=1)
            combined = cv2.bitwise_and(combined, cv2.bitwise_not(dilated))

    return combined


def build_scoped_mask(zones: List[dict], zone_ids: Iterable[str], dims: tuple[int, int]) -> np.ndarray:
    """Builds an inpaint mask covering only the given zone ids, still protecting all
    protected zones (windows/doors/foreground) regardless of which ids were requested.
    """
    zone_ids = set(zone_ids)
    combined = np.zeros((dims[1], dims[0]), dtype=np.uint8)

    for zone in zones:
        if zone["id"] in zone_ids and not zone["is_protected"]:
            combined = cv2.bitwise_or(combined, _draw_polygon_mask(dims, zone["polygon"]))

    kernel = np.ones((3, 3), np.uint8)
    for zone in zones:
        if zone["is_protected"]:
            dilated = cv2.dilate(_draw_polygon_mask(dims, zone["polygon"]), kernel, iterations=1)
            combined = cv2.bitwise_and(combined, cv2.bitwise_not(dilated))

    return combined
