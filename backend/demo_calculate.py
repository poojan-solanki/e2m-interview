#!/usr/bin/env python3
"""CLI Demo for Phase 1: Core Calculation Engine.

Allows testing BoQ and takeoff formulas via command line.
Examples:
    python backend/demo_calculate.py --area 1200 --material weatherproof_paint
    python backend/demo_calculate.py --area 800 --material stone_cladding --openings 120
    python backend/demo_calculate.py --sample-house --export-html report.html
    python backend/demo_calculate.py --list-materials
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path so imports work cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from backend.engine.materials_catalog import MATERIALS_CATALOG, list_materials, get_material
from backend.engine.boq_calculator import ZoneInput, calculate_boq
from backend.engine.report_generator import generate_ascii_report, generate_html_report, generate_json_report


def run_single_zone(
    area: float,
    material_id: str,
    openings: float = 0.0,
    mat_rate_override: float = None,
    lab_rate_override: float = None,
    contingency: float = 0.05,
    export_html: str = None,
    export_json: str = None,
):
    """Executes BoQ calculation for a single facade zone."""
    zone = ZoneInput(
        zone_id="zone_01",
        zone_name="Main Facade Wall",
        gross_area=area,
        material_id=material_id,
        openings=openings,
    )

    rate_overrides = None
    if mat_rate_override is not None or lab_rate_override is not None:
        rate_overrides = {material_id: {}}
        if mat_rate_override is not None:
            rate_overrides[material_id]["material_rate"] = mat_rate_override
        if lab_rate_override is not None:
            rate_overrides[material_id]["labor_rate"] = lab_rate_override

    summary = calculate_boq([zone], rate_overrides=rate_overrides, contingency_percentage=contingency)

    # Print ASCII table
    print(generate_ascii_report(summary, project_title="Single Zone Estimate"))

    # Optional exports
    if export_html:
        html_content = generate_html_report(summary, project_title="Single Zone Renovation Estimate")
        with open(export_html, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"✓ HTML report exported to: {export_html}")

    if export_json:
        json_content = generate_json_report(summary)
        with open(export_json, "w", encoding="utf-8") as f:
            f.write(json_content)
        print(f"✓ JSON data exported to: {export_json}")


def run_sample_house(export_html: str = None, export_json: str = None):
    """Executes a realistic multi-zone residential elevation takeoff."""
    zones = [
        ZoneInput(
            zone_id="zone_wall_main",
            zone_name="Main Front Wall (Ground + 1st)",
            gross_area=1200.0,
            material_id="weatherproof_paint",
            openings=180.0,  # Windows and entrance door deductions
        ),
        ZoneInput(
            zone_id="zone_accent_pillar",
            zone_name="Entrance Portico Columns",
            gross_area=160.0,
            material_id="stone_cladding",
            openings=0.0,
        ),
        ZoneInput(
            zone_id="zone_elevation_box",
            zone_name="Cantilever Elevation Feature",
            gross_area=240.0,
            material_id="textured_stucco",
            openings=24.0,  # Small highlight window
        ),
        ZoneInput(
            zone_id="zone_balcony_railing",
            zone_name="First Floor Balcony Railing",
            gross_area=28.0,  # 28 Running Feet
            material_id="glass_railing",
            openings=0.0,
        ),
        ZoneInput(
            zone_id="zone_terrace_parapet",
            zone_name="Terrace Parapet Outer Face",
            gross_area=320.0,
            material_id="weatherproof_paint",
            openings=0.0,
        ),
    ]

    summary = calculate_boq(zones, contingency_percentage=0.05)
    print(generate_ascii_report(summary, project_title="Sample Villa Elevation Renovation"))

    if export_html:
        html_content = generate_html_report(summary, project_title="Villa Elevation Renovation Takeoff")
        with open(export_html, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"✓ HTML report exported to: {export_html}")

    if export_json:
        json_content = generate_json_report(summary)
        with open(export_json, "w", encoding="utf-8") as f:
            f.write(json_content)
        print(f"✓ JSON data exported to: {export_json}")


def main():
    parser = argparse.ArgumentParser(
        description="Phase 1: Core Calculation & BoQ Engine (CLI Demo)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--area", type=float, default=None, help="Surface area in sq ft (or Rft for railings)")
    parser.add_argument("--material", type=str, default=None, help="Material ID from catalog")
    parser.add_argument("--openings", type=float, default=0.0, help="Deduction area for window/door openings in sq ft")
    parser.add_argument("--mat-rate", type=float, default=None, help="Override material rate per unit in INR (₹)")
    parser.add_argument("--lab-rate", type=float, default=None, help="Override labor rate per unit in INR (₹)")
    parser.add_argument("--contingency", type=float, default=0.05, help="Contingency percentage as decimal (default 0.05 = 5%%)")
    parser.add_argument("--sample-house", action="store_true", help="Run comprehensive multi-zone sample residential house estimate")
    parser.add_argument("--list-materials", action="store_true", help="List all available materials with rates and coverage")
    parser.add_argument("--export-html", type=str, default=None, help="File path to export professional HTML contractor report")
    parser.add_argument("--export-json", type=str, default=None, help="File path to export JSON summary")

    args = parser.parse_args()

    if args.list_materials:
        print("\n" + "=" * 80)
        print(f"  AVAILABLE MATERIALS IN CIVIL CATALOG (Ahmedabad / Gujarat Market)")
        print("=" * 80)
        for m in list_materials():
            print(f"ID       : {m.id}")
            print(f"Name     : {m.name} [{m.category.value.upper()}]")
            print(f"Unit     : {m.unit} | Coverage: {m.coverage_per_consumption_unit} {m.unit} per {m.consumption_unit}")
            print(f"Wastage  : {m.wastage_factor * 100:.0f}% allowance")
            print(f"Rates    : ₹{m.material_rate_inr}/unit (Mat) + ₹{m.labor_rate_inr}/unit (Lab) = ₹{m.total_rate_inr}/unit Total")
            print(f"Zones    : {', '.join(m.recommended_zones)}")
            print("-" * 80)
        return

    if args.sample_house:
        run_sample_house(export_html=args.export_html, export_json=args.export_json)
        return

    if args.area is not None:
        mat_id = args.material or "weatherproof_paint"
        try:
            get_material(mat_id)
        except KeyError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        run_single_zone(
            area=args.area,
            material_id=mat_id,
            openings=args.openings,
            mat_rate_override=args.mat_rate,
            lab_rate_override=args.lab_rate,
            contingency=args.contingency,
            export_html=args.export_html,
            export_json=args.export_json,
        )
        return

    # If no arguments given, run default demo
    print("Running default calculation demo (use --help for all options):\n")
    run_single_zone(area=1200.0, material_id="weatherproof_paint")


if __name__ == "__main__":
    main()
