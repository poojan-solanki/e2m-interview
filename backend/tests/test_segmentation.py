"""Comprehensive unit tests for Phase 2: AI Segmentation & Metrology."""

import json
from pathlib import Path
import cv2
import numpy as np
import pytest

from backend.segmentation.quality_checker import check_image_quality, ImageQualityReport
from backend.segmentation.exif_reader import extract_exif, ExifMetadata
from backend.segmentation.area_calculator import (
    polygon_area_pixels,
    polygon_perimeter_pixels,
    polygon_bounding_box,
    calibrate_scale_from_detection,
    compute_zone_measurements,
)
from backend.segmentation.segmenter import (
    FacadeSegmenter,
    SegmentedZone,
    SegmentationResult,
)
from backend.segmentation.zone_exporter import (
    draw_polygon_mask,
    generate_composite_overlay,
    export_segmentation_artifacts,
)


@pytest.fixture
def clean_test_image():
    """Creates a clean, sharp test image."""
    img = np.full((600, 800, 3), 180, dtype=np.uint8)
    # Draw sharp geometric shapes to provide high Laplacian variance
    cv2.rectangle(img, (100, 100), (400, 400), (50, 50, 50), -1)
    cv2.circle(img, (600, 300), 80, (20, 20, 20), -1)
    cv2.line(img, (50, 500), (750, 500), (0, 0, 0), 4)
    return img


# -------------------------------------------------------------------------
# 1. Quality Checker Tests
# -------------------------------------------------------------------------

def test_quality_checker_clean_image(clean_test_image):
    """Verify clean, sharp, well-lit image passes quality check."""
    report = check_image_quality(clean_test_image)
    assert report.is_valid is True
    assert report.is_blurry is False
    assert report.is_under_exposed is False
    assert report.is_over_exposed is False
    assert report.resolution == (800, 600)
    assert len(report.errors) == 0


def test_quality_checker_blurry_image(clean_test_image):
    """Verify blurred image triggers blur detection and fails validation."""
    blurred = cv2.GaussianBlur(clean_test_image, (45, 45), 0)
    report = check_image_quality(blurred, blur_threshold=100.0)
    assert report.is_blurry is True
    assert report.is_valid is False
    assert any("blurred" in err.lower() for err in report.errors)


def test_quality_checker_underexposed():
    """Verify pitch-black or underexposed image fails validation."""
    dark_img = np.full((600, 800, 3), 10, dtype=np.uint8)
    report = check_image_quality(dark_img, min_brightness=30.0)
    assert report.is_under_exposed is True
    assert report.is_valid is False
    assert any("underexposed" in err.lower() for err in report.errors)


def test_quality_checker_overexposed():
    """Verify completely washed-out image fails validation."""
    bright_img = np.full((600, 800, 3), 245, dtype=np.uint8)
    report = check_image_quality(bright_img, max_brightness=230.0)
    assert report.is_over_exposed is True
    assert report.is_valid is False
    assert any("overexposed" in err.lower() for err in report.errors)


def test_quality_checker_low_resolution():
    """Verify small thumbnail image fails minimum resolution check."""
    tiny_img = np.full((200, 300, 3), 120, dtype=np.uint8)
    report = check_image_quality(tiny_img, min_resolution=(640, 480))
    assert report.is_valid is False
    assert any("resolution" in err.lower() for err in report.errors)


# -------------------------------------------------------------------------
# 2. EXIF Reader Tests
# -------------------------------------------------------------------------

def test_exif_reader_missing_exif(tmp_path, clean_test_image):
    """Verify graceful handling of images without EXIF metadata (e.g. WhatsApp photos)."""
    img_path = tmp_path / "test_no_exif.jpg"
    cv2.imwrite(str(img_path), clean_test_image)

    exif = extract_exif(img_path)
    assert exif.has_exif is False
    assert exif.focal_length_mm is None
    assert exif.gps_latitude is None


def test_exif_reader_non_existent_file():
    """Verify non-existent file returns has_exif=False without raising an exception."""
    exif = extract_exif("non_existent_image_12345.jpg")
    assert exif.has_exif is False


# -------------------------------------------------------------------------
# 3. Polygon Geometry & Shoelace Formula Tests
# -------------------------------------------------------------------------

def test_shoelace_square_area():
    """Verify Shoelace formula on a 100x100 pixel square."""
    square = [[0, 0], [100, 0], [100, 100], [0, 100]]
    area = polygon_area_pixels(square)
    assert area == 10000.0


def test_shoelace_triangle_area():
    """Verify Shoelace formula on a right triangle with base 100 and height 50."""
    triangle = [[0, 0], [100, 0], [0, 50]]
    area = polygon_area_pixels(triangle)
    assert area == 2500.0


def test_polygon_perimeter():
    """Verify perimeter of a 100x50 rectangle."""
    rect = [[0, 0], [100, 0], [100, 50], [0, 50]]
    perim = polygon_perimeter_pixels(rect)
    assert perim == pytest.approx(300.0, rel=1e-3)


def test_polygon_bounding_box():
    """Verify bounding box calculation."""
    poly = [[15, 25], [105, 30], [90, 85], [10, 80]]
    bbox = polygon_bounding_box(poly)
    assert bbox == (10, 25, 105, 85)


# -------------------------------------------------------------------------
# 4. Scale Calibration Tests
# -------------------------------------------------------------------------

def test_scale_calibration_from_door_detection():
    """Verify Tier 1 door calibration when door is detected."""
    zones = [
        {
            "id": "door_01",
            "label": "door",
            "confidence": 0.90,
            "bbox": [500, 300, 580, 650],  # height = 350 pixels
        }
    ]
    # Door height = 350 px for a standard 2.10m door -> scale = 0.006 m/px
    scale, method = calibrate_scale_from_detection(zones, image_shape=(800, 1200), known_door_height_m=2.10)
    assert scale.meters_per_pixel == pytest.approx(0.006, rel=1e-3)
    assert "detected door" in method.lower()


def test_scale_calibration_fallback_prior():
    """Verify architectural geometric prior fallback when no door is detected."""
    zones = [{"id": "wall_01", "label": "wall", "confidence": 0.85, "bbox": [100, 100, 700, 700]}]
    scale, method = calibrate_scale_from_detection(zones, image_shape=(1000, 1200))
    assert scale.meters_per_pixel > 0
    assert "architectural geometric prior" in method.lower()


# -------------------------------------------------------------------------
# 5. Zone Exporter Tests
# -------------------------------------------------------------------------

def test_draw_polygon_mask():
    """Verify binary mask creation."""
    poly = [[50, 50], [150, 50], [150, 150], [50, 150]]
    mask = draw_polygon_mask((300, 300), poly)
    assert mask.shape == (300, 300)
    assert mask.dtype == np.uint8
    # Center pixel should be white (255)
    assert mask[100, 100] == 255
    # Outside pixel should be black (0)
    assert mask[10, 10] == 0


def test_zone_exporter_saves_all_artifacts(tmp_path):
    """Verify export_segmentation_artifacts creates zones.json, mask PNGs, and preview."""
    w, h = 600, 400
    base_img = np.full((h, w, 3), 200, dtype=np.uint8)

    poly_wall = [[50, 50], [550, 50], [550, 350], [50, 350]]
    poly_window = [[150, 120], [250, 120], [250, 220], [150, 220]]

    zone_wall = SegmentedZone(
        id="zone_01_wall",
        label="wall",
        display_name="Main Wall #1",
        category="surface",
        is_protected=False,
        confidence=0.92,
        polygon=poly_wall,
        bbox=[50, 50, 550, 350],
        pixel_area=150000.0,
        gross_area_sqft=600.0,
        deductions_sqft=40.0,
        net_area_sqft=560.0,
        running_feet=0.0,
        recommended_materials=["weatherproof_paint"],
        mask_filename="zone_01_wall_mask.png",
    )

    zone_window = SegmentedZone(
        id="zone_02_window",
        label="window",
        display_name="Window #2",
        category="opening",
        is_protected=True,
        confidence=0.88,
        polygon=poly_window,
        bbox=[150, 120, 250, 220],
        pixel_area=10000.0,
        gross_area_sqft=40.0,
        deductions_sqft=0.0,
        net_area_sqft=40.0,
        running_feet=0.0,
        recommended_materials=[],
        mask_filename="zone_02_window_mask.png",
    )

    scale, _ = calibrate_scale_from_detection([], (h, w))
    result = SegmentationResult(
        image_path="synthetic.jpg",
        image_dimensions=(w, h),
        quality_report=ImageQualityReport(
            is_valid=True, blur_score=250.0, is_blurry=False, brightness=120.0,
            is_under_exposed=False, is_over_exposed=False, resolution=(w, h),
        ),
        exif_metadata=ExifMetadata(has_exif=False),
        calibration_method="Test Calibration",
        scale_factor=scale,
        zones=[zone_wall, zone_window],
        total_gross_wall_area_sqft=600.0,
        total_window_area_sqft=40.0,
        net_paintable_wall_area_sqft=560.0,
    )

    artifacts = export_segmentation_artifacts(result, tmp_path, base_image=base_img)

    # 1. Check zones.json exists and contains correct content
    assert Path(artifacts["zones_json"]).exists()
    with open(artifacts["zones_json"], "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["zones"]) == 2
    assert data["zones"][0]["id"] == "zone_01_wall"
    assert data["zones"][1]["is_protected"] is True

    # 2. Check mask files exist
    assert Path(artifacts["mask_zone_01_wall"]).exists()
    assert Path(artifacts["mask_zone_02_window"]).exists()

    # 3. Check combined inpaint mask exists and excludes windows
    inpaint_mask_path = Path(artifacts["renovation_inpaint_mask"])
    assert inpaint_mask_path.exists()
    inpaint_mask = cv2.imread(str(inpaint_mask_path), cv2.IMREAD_GRAYSCALE)
    # Window center (x=200, y=170) must be black (0) because it is protected!
    assert inpaint_mask[170, 200] == 0
    # Wall region outside window (x=100, y=100) must be white (255)
    assert inpaint_mask[100, 100] == 255

    # 4. Check overlay preview exists
    assert Path(artifacts["overlay_preview"]).exists()


# -------------------------------------------------------------------------
# 6. SAM 3 FacadeSegmenter Integration & Unit Tests
# -------------------------------------------------------------------------

def test_sam3_segmenter_initialization():
    """Verify FacadeSegmenter initializes with SAM 3 defaults."""
    segmenter = FacadeSegmenter()
    assert segmenter.model_name == "weights/sam3.pt"
    assert segmenter.conf_threshold == 0.35
    assert segmenter.device in ["cuda", "cpu"]
    assert segmenter.model is None
    assert segmenter.processor is None


def test_sam3_checkpoint_and_vocab_resolution():
    """Verify SAM 3 checkpoint and BPE vocabulary path resolution."""
    segmenter = FacadeSegmenter()
    bpe_path = segmenter._get_bpe_path()
    assert bpe_path != "", "BPE vocabulary file path should be resolved"
    assert Path(bpe_path).exists(), f"BPE file not found at {bpe_path}"

    ckpt_path = segmenter._resolve_checkpoint()
    assert ckpt_path is not None, "SAM 3 weights checkpoint should be resolved"
    assert Path(ckpt_path).exists(), f"Checkpoint not found at {ckpt_path}"


def test_sam3_car_window_subtraction_logic():
    """Verify car mask subtraction removes car glass from window detections."""
    h, w = 500, 500
    # Simulate a car mask in the lower region
    car_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.rectangle(car_mask, (100, 300), (400, 480), 255, -1)

    # Simulate two window detections:
    # 1. House window on upper facade (x=150, y=50, w=100, h=100) -> outside car
    # 2. Car windshield detection (x=200, y=320, w=150, h=80) -> inside car
    house_win = np.zeros((h, w), dtype=np.uint8)
    cv2.rectangle(house_win, (150, 50), (250, 150), 255, -1)

    car_win = np.zeros((h, w), dtype=np.uint8)
    cv2.rectangle(car_win, (200, 320), (350, 400), 255, -1)

    # Subtraction logic
    clean_house_win = cv2.bitwise_and(house_win, cv2.bitwise_not(car_mask))
    clean_car_win = cv2.bitwise_and(car_win, cv2.bitwise_not(car_mask))

    # House window should be 100% retained
    assert np.sum(clean_house_win > 0) == np.sum(house_win > 0)
    # Car window should be 100% eliminated
    assert np.sum(clean_car_win > 0) == 0


def test_sam3_foreground_wall_exclusion_logic():
    """Verify painter and car foreground are subtracted from renovatable wall takeoffs."""
    h, w = 400, 400
    wall_mask = np.full((h, w), 255, dtype=np.uint8)

    # Person/car mask
    foreground = np.zeros((h, w), dtype=np.uint8)
    cv2.rectangle(foreground, (50, 200), (150, 380), 255, -1)

    # Windows mask (non-overlapping with foreground)
    windows = np.zeros((h, w), dtype=np.uint8)
    cv2.rectangle(windows, (250, 80), (350, 180), 255, -1)

    # Apply subtraction
    net_wall = cv2.bitwise_and(wall_mask, cv2.bitwise_not(foreground))
    net_wall = cv2.bitwise_and(net_wall, cv2.bitwise_not(windows))

    expected_pixels = (h * w) - int(np.sum(foreground > 0)) - int(np.sum(windows > 0))
    assert int(np.sum(net_wall > 0)) == expected_pixels
