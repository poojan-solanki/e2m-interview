"""Materials Catalog for Exterior Renovation Cost Estimation.

Provides pre-defined material specifications, civil consumption rates,
wastage factors, and market rates in INR (Ahmedabad / Gujarat region).
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional


class MaterialCategory(str, Enum):
    PAINT = "paint"
    TEXTURE = "texture"
    CLADDING = "cladding"
    TILES = "tiles"
    RAILING = "railing"
    PANELS = "panels"


@dataclass(frozen=True)
class Material:
    id: str
    name: str
    category: MaterialCategory
    unit: str  # "sq_ft" or "Rft" (running feet)
    consumption_unit: str  # e.g., "liters", "kg", "sq_ft", "Rft", "tiles"
    coverage_per_consumption_unit: float  # e.g., 65.0 sq ft per liter
    wastage_factor: float  # e.g., 0.10 for 10%
    material_rate_inr: float  # Material cost per unit in ₹
    labor_rate_inr: float  # Labor cost per unit in ₹
    description: str
    recommended_zones: List[str]

    @property
    def total_rate_inr(self) -> float:
        """Combined unit rate (material + labor)."""
        return round(self.material_rate_inr + self.labor_rate_inr, 2)

    def calculate_consumption(self, net_area: float) -> float:
        """Calculates quantity of material needed before wastage."""
        if self.coverage_per_consumption_unit <= 0:
            return net_area
        return round(net_area / self.coverage_per_consumption_unit, 2)

    def calculate_gross_consumption(self, net_area: float) -> float:
        """Calculates quantity of material needed including wastage."""
        base_qty = self.calculate_consumption(net_area)
        return round(base_qty * (1.0 + self.wastage_factor), 2)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["total_rate_inr"] = self.total_rate_inr
        data["category"] = self.category.value
        return data


# Pre-defined civil engineering catalog with Ahmedabad market standard rates (2026)
MATERIALS_CATALOG: Dict[str, Material] = {
    "weatherproof_paint": Material(
        id="weatherproof_paint",
        name="Exterior Weatherproof Acrylic Emulsion",
        category=MaterialCategory.PAINT,
        unit="sq_ft",
        consumption_unit="liters",
        coverage_per_consumption_unit=65.0,  # 65 sq ft per liter (2 coats + 1 primer coat)
        wastage_factor=0.10,  # 10% wastage
        material_rate_inr=25.0,
        labor_rate_inr=12.0,
        description="High-performance 100% acrylic emulsion with anti-fungal protection and UV resistance.",
        recommended_zones=["wall", "main_wall", "parapet", "accent_wall"],
    ),
    "textured_stucco": Material(
        id="textured_stucco",
        name="Textured Stucco Finish",
        category=MaterialCategory.TEXTURE,
        unit="sq_ft",
        consumption_unit="kg",
        coverage_per_consumption_unit=25.0,  # 25 sq ft per kg
        wastage_factor=0.10,  # 10% wastage
        material_rate_inr=45.0,
        labor_rate_inr=18.0,
        description="Premium weather-resistant exterior textured stucco with sand-grain aesthetic.",
        recommended_zones=["wall", "accent_wall", "pillar", "elevation_box"],
    ),
    "stone_cladding": Material(
        id="stone_cladding",
        name="Natural Granite / Slate Stone Cladding",
        category=MaterialCategory.CLADDING,
        unit="sq_ft",
        consumption_unit="sq_ft",
        coverage_per_consumption_unit=1.0,  # 1 sq ft per sq ft (+ 4.5kg adhesive mortar / m²)
        wastage_factor=0.15,  # 15% cutting & pattern matching wastage
        material_rate_inr=220.0,
        labor_rate_inr=65.0,
        description="Natural split-face granite or slate stone veneer with polymer-modified adhesive bonding.",
        recommended_zones=["pillar", "accent_wall", "portico", "boundary_pillars"],
    ),
    "vitrified_tiles": Material(
        id="vitrified_tiles",
        name="Exterior Vitrified Wall Tiles",
        category=MaterialCategory.TILES,
        unit="sq_ft",
        consumption_unit="sq_ft",
        coverage_per_consumption_unit=1.0,  # 1 sq ft per sq ft (+ epoxy grout)
        wastage_factor=0.10,  # 10% cutting wastage
        material_rate_inr=85.0,
        labor_rate_inr=35.0,
        description="Heavy-duty exterior grade vitrified wall tiles with water absorption < 0.05%.",
        recommended_zones=["wall", "accent_wall", "balcony_wall", "parking_wall"],
    ),
    "glass_railing": Material(
        id="glass_railing",
        name="Frameless Toughened Glass Railing (SS 304)",
        category=MaterialCategory.RAILING,
        unit="Rft",  # Running feet
        consumption_unit="Rft",
        coverage_per_consumption_unit=1.0,  # 1 Rft per Rft
        wastage_factor=0.05,  # 5% wastage
        material_rate_inr=1400.0,
        labor_rate_inr=300.0,
        description="12mm toughened safety glass with SS 304 grade heavy-duty base spigots and top handrail.",
        recommended_zones=["balcony", "balcony_railing", "terrace_parapet"],
    ),
    "metal_railing": Material(
        id="metal_railing",
        name="Powder-Coated MS / GI Metal Railing",
        category=MaterialCategory.RAILING,
        unit="Rft",  # Running feet
        consumption_unit="Rft",
        coverage_per_consumption_unit=1.0,  # 1 Rft per Rft
        wastage_factor=0.05,  # 5% wastage
        material_rate_inr=650.0,
        labor_rate_inr=180.0,
        description="Anti-rust zinc-chromate treated mild steel railing with matte polyester powder coating.",
        recommended_zones=["balcony", "balcony_railing", "staircase", "parapet"],
    ),
    "wpc_panels": Material(
        id="wpc_panels",
        name="WPC Exterior Louver Panels",
        category=MaterialCategory.PANELS,
        unit="sq_ft",
        consumption_unit="sq_ft",
        coverage_per_consumption_unit=1.0,  # 1 sq ft per sq ft
        wastage_factor=0.12,  # 12% cutting wastage
        material_rate_inr=180.0,
        labor_rate_inr=45.0,
        description="Wood-plastic composite interlocking fluted facade panels with aluminum substructure.",
        recommended_zones=["wall", "accent_wall", "facade_fins", "elevation_box"],
    ),
}


def get_material(material_id: str) -> Material:
    """Retrieves a material by ID. Raises KeyError if not found."""
    normalized_id = material_id.strip().lower()
    if normalized_id not in MATERIALS_CATALOG:
        valid_keys = ", ".join(MATERIALS_CATALOG.keys())
        raise KeyError(f"Material '{material_id}' not found. Available materials: {valid_keys}")
    return MATERIALS_CATALOG[normalized_id]


def list_materials(category: Optional[MaterialCategory] = None) -> List[Material]:
    """Returns list of all materials, optionally filtered by category."""
    materials = list(MATERIALS_CATALOG.values())
    if category is not None:
        materials = [m for m in materials if m.category == category]
    return materials
