"""Pydantic request/response models for the Phase 5 REST API.

Field names use camelCase aliases so the JSON wire format matches
frontend/src/types/index.ts exactly (Zone, RateOverride, BoQLineItem, BoQSummary).
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# --- /api/boq ---------------------------------------------------------------


class ZoneCalcInput(CamelModel):
    zone_id: str
    zone_name: str
    material_id: str
    unit: str  # "sq_ft" or "Rft"
    gross_area_sqft: float = 0.0
    deductions_sqft: float = 0.0
    running_feet: float = 0.0


class RateOverrideModel(CamelModel):
    material_rate_inr: Optional[float] = None
    labor_rate_inr: Optional[float] = None


class BoQRequest(CamelModel):
    zones: List[ZoneCalcInput]
    rate_overrides: Dict[str, RateOverrideModel] = {}
    contingency_pct: float = 5.0


class BoQLineItemResponse(CamelModel):
    zone_id: str
    zone_name: str
    material_id: str
    material_name: str
    unit: str
    net_area: float
    wastage_pct: float
    gross_material_area: float
    unit_material_rate_inr: float
    unit_labor_rate_inr: float
    material_cost_inr: float
    labor_cost_inr: float
    line_total_inr: float


class BoQResponse(CamelModel):
    items: List[BoQLineItemResponse]
    total_material_cost_inr: float
    total_labor_cost_inr: float
    subtotal_inr: float
    contingency_pct: float
    contingency_amount_inr: float
    grand_total_inr: float


# --- /api/render/preview -----------------------------------------------------


class RenderPreviewRequest(CamelModel):
    house_id: str
    material_id: str


class RenderPreviewResponse(CamelModel):
    material_id: str
    image_data_uri: str
    execution_time_ms: float
    output_width: int
    output_height: int
