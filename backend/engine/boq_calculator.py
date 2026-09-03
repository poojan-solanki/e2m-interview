"""Bill of Quantities (BoQ) & Takeoff Cost Calculator.

Computes exact material quantities, civil wastage allowances, labor expenses,
and itemized project cost totals in INR (₹) with support for dynamic rate overrides.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Union
from .materials_catalog import Material, get_material
from .area_estimator import compute_net_area, AreaDeductionResult


@dataclass
class ZoneInput:
    """Input definition for an individual architectural facade zone."""
    zone_id: str
    zone_name: str
    gross_area: float  # sq ft for walls/slabs, or linear Rft for railings
    material_id: str
    openings: Union[float, List[Union[float, dict]]] = 0.0
    notes: Optional[str] = None


@dataclass
class BoQLineItem:
    """Detailed itemized takeoff calculation for a specific facade zone."""
    zone_id: str
    zone_name: str
    material_id: str
    material_name: str
    category: str
    unit: str  # "sq_ft" or "Rft"
    consumption_unit: str  # "liters", "kg", "sq_ft", "Rft"
    gross_surface_area: float
    deductions_area: float
    net_workable_area: float
    wastage_percentage: float
    wastage_area_allowance: float
    gross_material_area: float
    net_consumption_qty: float
    gross_consumption_qty: float
    unit_material_rate_inr: float
    unit_labor_rate_inr: float
    material_cost_inr: float
    labor_cost_inr: float
    line_total_inr: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BoQSummary:
    """Complete project Bill of Quantities with category breakdowns and grand total."""
    items: List[BoQLineItem]
    total_gross_area_sqft: float
    total_net_area_sqft: float
    total_material_cost_inr: float
    total_labor_cost_inr: float
    category_totals_inr: Dict[str, float]
    subtotal_inr: float
    contingency_percentage: float
    contingency_amount_inr: float
    grand_total_inr: float
    currency: str = "INR"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["items"] = [item.to_dict() for item in self.items]
        return data


def calculate_line_item(
    zone: ZoneInput,
    material: Material,
    material_rate_override: Optional[float] = None,
    labor_rate_override: Optional[float] = None,
) -> BoQLineItem:
    """Calculates quantity and cost for a single architectural zone."""
    # Railings are linear running feet, not subject to window openings
    is_linear = material.unit == "Rft"
    
    if is_linear:
        deduction_res = AreaDeductionResult(
            gross_area_sqft=zone.gross_area,
            total_deductions_sqft=0.0,
            net_area_sqft=zone.gross_area,
            deduction_percentage=0.0,
        )
    else:
        deduction_res = compute_net_area(zone.gross_area, zone.openings)

    net_area = deduction_res.net_area_sqft
    wastage_pct = material.wastage_factor
    wastage_allowance = round(net_area * wastage_pct, 2)
    gross_mat_area = round(net_area + wastage_allowance, 2)

    # Material consumption calculations
    net_consumption = material.calculate_consumption(net_area)
    gross_consumption = material.calculate_gross_consumption(net_area)

    # Active rates (with user overrides if provided)
    mat_rate = material_rate_override if material_rate_override is not None else material.material_rate_inr
    lab_rate = labor_rate_override if labor_rate_override is not None else material.labor_rate_inr

    # Civil cost principle:
    # Material is purchased for gross area (including cutting/spill wastage)
    # Labor is paid for net finished work installed
    material_cost = round(gross_mat_area * mat_rate, 2)
    labor_cost = round(net_area * lab_rate, 2)
    line_total = round(material_cost + labor_cost, 2)

    return BoQLineItem(
        zone_id=zone.zone_id,
        zone_name=zone.zone_name,
        material_id=material.id,
        material_name=material.name,
        category=material.category.value,
        unit=material.unit,
        consumption_unit=material.consumption_unit,
        gross_surface_area=deduction_res.gross_area_sqft,
        deductions_area=deduction_res.total_deductions_sqft,
        net_workable_area=net_area,
        wastage_percentage=round(wastage_pct * 100.0, 1),
        wastage_area_allowance=wastage_allowance,
        gross_material_area=gross_mat_area,
        net_consumption_qty=net_consumption,
        gross_consumption_qty=gross_consumption,
        unit_material_rate_inr=mat_rate,
        unit_labor_rate_inr=lab_rate,
        material_cost_inr=material_cost,
        labor_cost_inr=labor_cost,
        line_total_inr=line_total,
    )


def calculate_boq(
    zones: List[ZoneInput],
    rate_overrides: Optional[Dict[str, Dict[str, float]]] = None,
    contingency_percentage: float = 0.05,
) -> BoQSummary:
    """Calculates complete project Bill of Quantities across all facade zones.
    
    Args:
        zones: List of ZoneInput specifications.
        rate_overrides: Optional dictionary of rate modifications by material_id:
            e.g., {"weatherproof_paint": {"material_rate": 28.0, "labor_rate": 14.0}}
        contingency_percentage: Contingency allowance (default 0.05 for 5%).
        
    Returns:
        BoQSummary containing itemized calculations, category breakdowns, and grand total.
    """
    if not zones:
        return BoQSummary(
            items=[],
            total_gross_area_sqft=0.0,
            total_net_area_sqft=0.0,
            total_material_cost_inr=0.0,
            total_labor_cost_inr=0.0,
            category_totals_inr={},
            subtotal_inr=0.0,
            contingency_percentage=contingency_percentage * 100.0,
            contingency_amount_inr=0.0,
            grand_total_inr=0.0,
        )

    rate_overrides = rate_overrides or {}
    items: List[BoQLineItem] = []
    category_totals: Dict[str, float] = {}

    total_gross_area = 0.0
    total_net_area = 0.0
    total_material_cost = 0.0
    total_labor_cost = 0.0

    for zone in zones:
        material = get_material(zone.material_id)
        
        # Check for overrides
        mat_override = None
        lab_override = None
        if zone.material_id in rate_overrides:
            mat_override = rate_overrides[zone.material_id].get("material_rate")
            lab_override = rate_overrides[zone.material_id].get("labor_rate")

        line_item = calculate_line_item(zone, material, mat_override, lab_override)
        items.append(line_item)

        # Track area (only for surface areas in sq ft)
        if line_item.unit == "sq_ft":
            total_gross_area += line_item.gross_surface_area
            total_net_area += line_item.net_workable_area

        total_material_cost += line_item.material_cost_inr
        total_labor_cost += line_item.labor_cost_inr

        cat = line_item.category
        category_totals[cat] = round(category_totals.get(cat, 0.0) + line_item.line_total_inr, 2)

    subtotal = round(total_material_cost + total_labor_cost, 2)
    contingency_amount = round(subtotal * contingency_percentage, 2)
    grand_total = round(subtotal + contingency_amount, 2)

    return BoQSummary(
        items=items,
        total_gross_area_sqft=round(total_gross_area, 2),
        total_net_area_sqft=round(total_net_area, 2),
        total_material_cost_inr=round(total_material_cost, 2),
        total_labor_cost_inr=round(total_labor_cost, 2),
        category_totals_inr=category_totals,
        subtotal_inr=subtotal,
        contingency_percentage=round(contingency_percentage * 100.0, 1),
        contingency_amount_inr=contingency_amount,
        grand_total_inr=grand_total,
    )
