"""POST /api/boq — wraps backend/engine/boq_calculator.py directly."""

from fastapi import APIRouter, HTTPException

from backend.api.schemas import BoQLineItemResponse, BoQRequest, BoQResponse
from backend.engine.boq_calculator import ZoneInput, calculate_boq

router = APIRouter()


def _build_zone_input(zone) -> ZoneInput:
    if zone.unit == "Rft":
        return ZoneInput(
            zone_id=zone.zone_id,
            zone_name=zone.zone_name,
            gross_area=zone.running_feet,
            material_id=zone.material_id,
            openings=0.0,
        )
    return ZoneInput(
        zone_id=zone.zone_id,
        zone_name=zone.zone_name,
        gross_area=zone.gross_area_sqft,
        material_id=zone.material_id,
        openings=zone.deductions_sqft,
    )


def _build_rate_overrides(request: BoQRequest) -> dict:
    """Translates per-zone overrides (keyed by zoneId, as the frontend sends them)
    into the engine's per-material overrides (keyed by materialId)."""
    overrides: dict = {}
    for zone in request.zones:
        override = request.rate_overrides.get(zone.zone_id)
        if override is None:
            continue
        entry = overrides.setdefault(zone.material_id, {})
        if override.material_rate_inr is not None:
            entry["material_rate"] = override.material_rate_inr
        if override.labor_rate_inr is not None:
            entry["labor_rate"] = override.labor_rate_inr
    return overrides


@router.post("/boq", response_model=BoQResponse, response_model_by_alias=True)
def compute_boq(request: BoQRequest) -> BoQResponse:
    zone_inputs = [_build_zone_input(z) for z in request.zones]
    rate_overrides = _build_rate_overrides(request)

    try:
        summary = calculate_boq(
            zone_inputs,
            rate_overrides=rate_overrides,
            contingency_percentage=request.contingency_pct / 100.0,
        )
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return BoQResponse(
        items=[
            BoQLineItemResponse(
                zone_id=item.zone_id,
                zone_name=item.zone_name,
                material_id=item.material_id,
                material_name=item.material_name,
                unit=item.unit,
                net_area=item.net_workable_area,
                wastage_pct=item.wastage_percentage,
                gross_material_area=item.gross_material_area,
                unit_material_rate_inr=item.unit_material_rate_inr,
                unit_labor_rate_inr=item.unit_labor_rate_inr,
                material_cost_inr=item.material_cost_inr,
                labor_cost_inr=item.labor_cost_inr,
                line_total_inr=item.line_total_inr,
            )
            for item in summary.items
        ],
        total_material_cost_inr=summary.total_material_cost_inr,
        total_labor_cost_inr=summary.total_labor_cost_inr,
        subtotal_inr=summary.subtotal_inr,
        contingency_pct=summary.contingency_percentage,
        contingency_amount_inr=summary.contingency_amount_inr,
        grand_total_inr=summary.grand_total_inr,
    )
