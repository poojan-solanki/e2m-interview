#!/usr/bin/env python3
"""CLI Demo for Phase 2: AI Segmentation & Facade Parsing.

Accepts an exterior residential house image, validates image quality, extracts EXIF,
runs FastSAM concept segmentation, calculates real-world metric surface areas,
and exports binary masks, composite overlay preview, and zones.json.

Examples:
    python backend/demo_segment.py --image house.jpg
    python backend/demo_segment.py --image house.jpg --output output/
    python backend/demo_segment.py --generate-sample
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import cv2
import numpy as np

from backend.segmentation.segmenter import FacadeSegmenter
from backend.segmentation.zone_exporter import export_segmentation_artifacts


def create_sample_facade_image(output_path: Path) -> Path:
    """Generates a synthetic residential house elevation image for testing when no photo is provided."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    w, h = 1200, 800
    img = np.zeros((h, w, 3), dtype=np.uint8)

    # 1. Sky background (gradient light blue)
    for y in range(h):
        val = int(220 + (y / h) * 35)
        img[y, :] = (val, int(val * 0.92), int(val * 0.82))

    # 2. Ground / driveway
    cv2.rectangle(img, (0, 680), (w, h), (120, 130, 135), -1)

    # 3. Main house facade wall (Warm stone color)
    wall_poly = np.array([[200, 200], [1000, 200], [1000, 680], [200, 680]], dtype=np.int32)
    cv2.fillPoly(img, [wall_poly], (200, 215, 225))
    cv2.polylines(img, [wall_poly], isClosed=True, color=(140, 150, 160), thickness=3)

    # 4. Roof / Parapet
    roof_poly = np.array([[180, 200], [600, 80], [1020, 200]], dtype=np.int32)
    cv2.fillPoly(img, [roof_poly], (70, 75, 85))
    cv2.polylines(img, [roof_poly], isClosed=True, color=(40, 45, 50), thickness=3)

    # 5. Accent Pillars / Columns (2 vertical columns at entrance)
    cv2.rectangle(img, (500, 380), (560, 680), (160, 175, 185), -1)
    cv2.rectangle(img, (660, 380), (720, 680), (160, 175, 185), -1)
    cv2.rectangle(img, (500, 380), (560, 680), (110, 120, 130), 2)
    cv2.rectangle(img, (660, 380), (720, 680), (110, 120, 130), 2)

    # 6. Entrance Door (Standard reference object: 2.1m height)
    door_rect = (575, 470, 645, 680)
    cv2.rectangle(img, (door_rect[0], door_rect[1]), (door_rect[2], door_rect[3]), (50, 60, 110), -1)
    cv2.rectangle(img, (door_rect[0], door_rect[1]), (door_rect[2], door_rect[3]), (30, 35, 70), 3)

    # 7. Ground floor windows (Left and Right)
    cv2.rectangle(img, (260, 450), (420, 580), (220, 180, 120), -1)
    cv2.rectangle(img, (260, 450), (420, 580), (80, 80, 80), 3)
    cv2.rectangle(img, (800, 450), (940, 580), (220, 180, 120), -1)
    cv2.rectangle(img, (800, 450), (940, 580), (80, 80, 80), 3)

    # 8. First floor balcony & railing
    cv2.rectangle(img, (320, 240), (880, 370), (180, 200, 210), -1)
    # Balcony Glass Railing
    cv2.rectangle(img, (320, 330), (880, 370), (240, 220, 180), -1)
    cv2.rectangle(img, (320, 330), (880, 370), (160, 140, 100), 2)

    # 9. First floor windows behind balcony
    cv2.rectangle(img, (400, 260), (520, 330), (220, 180, 120), -1)
    cv2.rectangle(img, (680, 260), (800, 330), (220, 180, 120), -1)

    cv2.imwrite(str(output_path), img)
    return output_path


def run_segmentation(
    image_path: Path,
    output_dir: Path,
    door_height_m: float = 2.10,
    device: str = None,
    conf_threshold: float = 0.25,
):
    """Executes the full segmentation and metrology pipeline."""
    print("=" * 88)
    print("  AI EXTERIOR HOUSE FACADE SEGMENTATION & METROLOGY")
    print("=" * 88)
    print(f"Input Image : {image_path}")
    print(f"Output Dir  : {output_dir}")
    print(f"Reference H : {door_height_m}m (Standard Entrance Door)")
    print("-" * 88)

    # 1. Initialize Segmenter
    segmenter = FacadeSegmenter(device=device, conf_threshold=conf_threshold)
    print(f"Loaded FastSAM Engine [Device: {segmenter.device.upper()}]")

    # 2. Run Segmentation Pipeline
    print("Running architectural zone detection & spatial calibration...")
    result = segmenter.segment_image(
        image_input=image_path,
        known_door_height_m=door_height_m,
    )

    # 3. Print Quality & Calibration Summary
    q = result.quality_report
    exif = result.exif_metadata
    scale = result.scale_factor

    print("\n--- [1] MEDIA QUALITY & CAMERA CALIBRATION ---")
    status_str = "PASSED ✓" if q.is_valid else "FAILED ✗"
    print(f"• Image Usability : {status_str} (Resolution: {q.resolution[0]}x{q.resolution[1]}, Sharpness: {q.blur_score:.1f}, Brightness: {q.brightness:.1f})")
    if q.warnings:
        for w in q.warnings:
            print(f"  [Warning] {w}")

    if exif.has_exif:
        cam = f"{exif.camera_make or ''} {exif.camera_model or ''}".strip() or "Standard Digital Camera"
        fl_str = f"{exif.focal_length_mm:.1f}mm" if exif.focal_length_mm else "N/A"
        print(f"• Camera Metadata : {cam} (Focal Length: {fl_str})")
        if exif.gps_latitude and exif.gps_longitude:
            print(f"• GPS Location    : {exif.gps_latitude:.5f}, {exif.gps_longitude:.5f}")
    else:
        print("• Camera Metadata : EXIF stripped or unavailable (Standard web/mobile pipeline)")

    print(f"• Spatial Scale   : 1 pixel = {scale.meters_per_pixel:.4f}m ({scale.feet_per_pixel:.4f} ft)")
    print(f"• Method Used     : {result.calibration_method}")

    # 4. Print Detected Zones Table
    print("\n--- [2] DETECTED ARCHITECTURAL ZONES ---")
    header = f"{'Zone ID':<18} | {'Category':<10} | {'Status':<11} | {'Gross Area':<12} | {'Openings':<10} | {'Net Workable':<14}"
    print(header)
    print("-" * 88)

    if not result.zones:
        print("  No architectural zones detected at current confidence threshold.")
    else:
        for z in result.zones:
            status = "LOCKED [P]" if z.is_protected else "RENOVATABLE"
            gross_str = f"{z.gross_area_sqft:.1f} sqft"
            ded_str = f"-{z.deductions_sqft:.1f}" if z.deductions_sqft > 0 else "0.0"
            if z.category == "railing":
                net_str = f"{z.running_feet:.1f} Rft"
            else:
                net_str = f"{z.net_area_sqft:.1f} sqft"

            print(f"{z.id:<18} | {z.category[:10]:<10} | {status:<11} | {gross_str:<12} | {ded_str:<10} | {net_str:<14}")

    print("-" * 88)
    print(f"Total Gross Wall Surface Area : {result.total_gross_wall_area_sqft:.1f} sq ft")
    print(f"Total Protected Window Area   : {result.total_window_area_sqft:.1f} sq ft")
    print(f"Net Paintable/Claddable Area  : {result.net_paintable_wall_area_sqft:.1f} sq ft")

    # 5. Export Masks and Zones Metadata
    print("\n--- [3] EXPORTING ARTIFACTS ---")
    artifacts = export_segmentation_artifacts(result, output_dir)
    for key, path in artifacts.items():
        print(f"✓ Saved: {path}")

    print("\n" + "=" * 88)
    print(f"  PHASE 2 SEGMENTATION COMPLETE: {len(result.zones)} zones exported to {output_dir}/")
    print("=" * 88 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Phase 2: AI Segmentation & Facade Parsing (CLI Demo)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--image", type=str, default=None, help="Path to input residential building photo (JPG/PNG)")
    parser.add_argument("--output", type=str, default="output", help="Directory where masks and zones.json will be saved (default: output/)")
    parser.add_argument("--door-height", type=float, default=2.10, help="Physical height of entrance door in meters for Tier 1 calibration (default: 2.10m)")
    parser.add_argument("--device", type=str, default=None, help="Computation device ('cuda' or 'cpu', auto-detected by default)")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold for FastSAM (default: 0.25)")
    parser.add_argument("--generate-sample", action="store_true", help="Generate a synthetic house elevation image in samples/sample_house.jpg")

    args = parser.parse_args()

    sample_img_path = Path("samples/sample_house.jpg")

    if args.generate_sample:
        create_sample_facade_image(sample_img_path)
        print(f"✓ Synthetic sample house image generated at: {sample_img_path}")
        return

    # If image is specified, run on it
    if args.image:
        img_path = Path(args.image)
        if not img_path.exists():
            print(f"Error: Specified image does not exist: {img_path}", file=sys.stderr)
            sys.exit(1)
    else:
        # If no image specified, check if sample exists or create it
        if not sample_img_path.exists():
            print("No image specified. Creating synthetic residential sample at samples/sample_house.jpg...")
            create_sample_facade_image(sample_img_path)
        img_path = sample_img_path

    out_dir = Path(args.output)
    run_segmentation(
        image_path=img_path,
        output_dir=out_dir,
        door_height_m=args.door_height,
        device=args.device,
        conf_threshold=args.conf,
    )


if __name__ == "__main__":
    main()
