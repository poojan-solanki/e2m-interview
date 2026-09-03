"""Pydantic request/response models for the Phase 5 REST API.

Field names use camelCase aliases so the JSON wire format matches
frontend/src/types/index.ts exactly (Zone, RateOverride, BoQLineItem, BoQSummary).
"""

from typing import Dict, List, Optional, Tuple

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
    assignments: Dict[str, str]  # zoneId -> materialId; different zones may use different materials


class RenderPreviewResponse(CamelModel):
    material_ids: List[str]  # distinct materials actually rendered, in no particular order
    image_data_uri: str
    execution_time_ms: float
    output_width: int
    output_height: int


# --- /api/segment -------------------------------------------------------------


class ZoneResponse(CamelModel):
    id: str
    label: str
    display_name: str
    category: str
    is_protected: bool
    confidence: float
    polygon: List[Tuple[float, float]]
    bbox: Tuple[int, int, int, int]
    pixel_area: float
    gross_area_sqft: float
    deductions_sqft: float
    net_area_sqft: float
    running_feet: float
    recommended_materials: List[str]


class SegmentResponse(CamelModel):
    house_id: str
    image_width: int
    image_height: int
    total_gross_wall_area_sqft: float
    net_paintable_wall_area_sqft: float
    scale_factor_sqft_per_sq_pixel: float
    calibration_method: str
    quality_warnings: List[str] = []
    zones: List[ZoneResponse]


# --- /api/render/neural -------------------------------------------------------


class NeuralRenderJobRequest(CamelModel):
    house_id: str
    assignments: Dict[str, str]  # zoneId -> materialId; one GPU pass runs per distinct material


class NeuralRenderJobCreated(CamelModel):
    job_id: str
    status: str


class NeuralRenderJobStatus(CamelModel):
    job_id: str
    status: str  # "pending" | "running" | "done" | "error"
    image_url: Optional[str] = None
    error_message: Optional[str] = None
    elapsed_sec: Optional[float] = None
    current_material_index: Optional[int] = None  # 1-based, e.g. 2 of 3
    total_materials: Optional[int] = None
    current_material_id: Optional[str] = None
