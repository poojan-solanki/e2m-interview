// Exact port of backend/engine/materials_catalog.py — keep in sync with that file.
import type { Material } from "@/types";

export const MATERIALS: Material[] = [
  {
    id: "weatherproof_paint",
    name: "Exterior Weatherproof Acrylic Emulsion",
    shortName: "Weatherproof Paint",
    category: "paint",
    unit: "sq_ft",
    consumptionUnit: "liters",
    coveragePerConsumptionUnit: 65.0,
    wastageFactor: 0.1,
    materialRateInr: 25.0,
    laborRateInr: 12.0,
    description:
      "High-performance 100% acrylic emulsion with anti-fungal protection and UV resistance.",
    swatchColor: "#d97706",
  },
  {
    id: "textured_stucco",
    name: "Textured Stucco Finish",
    shortName: "Textured Stucco",
    category: "texture",
    unit: "sq_ft",
    consumptionUnit: "kg",
    coveragePerConsumptionUnit: 25.0,
    wastageFactor: 0.1,
    materialRateInr: 45.0,
    laborRateInr: 18.0,
    description:
      "Premium weather-resistant exterior textured stucco with sand-grain aesthetic.",
    swatchColor: "#c4a97d",
  },
  {
    id: "stone_cladding",
    name: "Natural Granite / Slate Stone Cladding",
    shortName: "Stone Cladding",
    category: "cladding",
    unit: "sq_ft",
    consumptionUnit: "sq_ft",
    coveragePerConsumptionUnit: 1.0,
    wastageFactor: 0.15,
    materialRateInr: 220.0,
    laborRateInr: 65.0,
    description:
      "Natural split-face granite or slate stone veneer with polymer-modified adhesive bonding.",
    swatchColor: "#6b7280",
  },
  {
    id: "vitrified_tiles",
    name: "Exterior Vitrified Wall Tiles",
    shortName: "Vitrified Tiles",
    category: "tiles",
    unit: "sq_ft",
    consumptionUnit: "sq_ft",
    coveragePerConsumptionUnit: 1.0,
    wastageFactor: 0.1,
    materialRateInr: 85.0,
    laborRateInr: 35.0,
    description: "Heavy-duty exterior grade vitrified wall tiles with water absorption < 0.05%.",
    swatchColor: "#475569",
  },
  {
    id: "wpc_panels",
    name: "WPC Exterior Louver Panels",
    shortName: "WPC Louver Panels",
    category: "panels",
    unit: "sq_ft",
    consumptionUnit: "sq_ft",
    coveragePerConsumptionUnit: 1.0,
    wastageFactor: 0.12,
    materialRateInr: 180.0,
    laborRateInr: 45.0,
    description:
      "Wood-plastic composite interlocking fluted facade panels with aluminum substructure.",
    swatchColor: "#4a3728",
  },
  {
    id: "glass_railing",
    name: "Frameless Toughened Glass Railing (SS 304)",
    shortName: "Glass Railing",
    category: "railing",
    unit: "Rft",
    consumptionUnit: "Rft",
    coveragePerConsumptionUnit: 1.0,
    wastageFactor: 0.05,
    materialRateInr: 1400.0,
    laborRateInr: 300.0,
    description:
      "12mm toughened safety glass with SS 304 grade heavy-duty base spigots and top handrail.",
    swatchColor: "#bfdbfe",
  },
  {
    id: "metal_railing",
    name: "Powder-Coated MS / GI Metal Railing",
    shortName: "Metal Railing",
    category: "railing",
    unit: "Rft",
    consumptionUnit: "Rft",
    coveragePerConsumptionUnit: 1.0,
    wastageFactor: 0.05,
    materialRateInr: 650.0,
    laborRateInr: 180.0,
    description:
      "Anti-rust zinc-chromate treated mild steel railing with matte polyester powder coating.",
    swatchColor: "#1e293b",
  },
];

export function getMaterial(id: string): Material {
  const material = MATERIALS.find((m) => m.id === id);
  if (!material) throw new Error(`Unknown material id: ${id}`);
  return material;
}
