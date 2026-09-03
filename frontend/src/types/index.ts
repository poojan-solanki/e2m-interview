export type ZoneCategory = "opening" | "surface" | "railing";

export interface Zone {
  id: string;
  label: string;
  displayName: string;
  category: ZoneCategory;
  isProtected: boolean;
  confidence: number;
  /** [x, y][] in the coordinate space of the sample house's imageWidth/imageHeight */
  polygon: [number, number][];
  bbox: [number, number, number, number];
  pixelArea: number;
  grossAreaSqft: number;
  deductionsSqft: number;
  netAreaSqft: number;
  runningFeet: number;
  recommendedMaterials: string[];
}

export type MaterialUnit = "sq_ft" | "Rft";

export interface Material {
  id: string;
  name: string;
  shortName: string;
  category: string;
  unit: MaterialUnit;
  consumptionUnit: string;
  coveragePerConsumptionUnit: number;
  wastageFactor: number;
  materialRateInr: number;
  laborRateInr: number;
  description: string;
  swatchColor: string;
}

export interface BoQLineItem {
  zoneId: string;
  zoneName: string;
  materialId: string;
  materialName: string;
  unit: MaterialUnit;
  netArea: number;
  wastagePct: number;
  grossMaterialArea: number;
  unitMaterialRateInr: number;
  unitLaborRateInr: number;
  materialCostInr: number;
  laborCostInr: number;
  lineTotalInr: number;
}

export interface BoQSummary {
  items: BoQLineItem[];
  totalMaterialCostInr: number;
  totalLaborCostInr: number;
  subtotalInr: number;
  contingencyPct: number;
  contingencyAmountInr: number;
  grandTotalInr: number;
}

/** One or more zones sharing the same label + material, collapsed into a single BoQ row. */
export interface BoQGroup {
  groupKey: string;
  zoneIds: string[];
  zoneCount: number;
  displayName: string;
  materialId: string;
  materialName: string;
  unit: MaterialUnit;
  netArea: number;
  wastagePct: number;
  unitMaterialRateInr: number;
  unitLaborRateInr: number;
  materialCostInr: number;
  laborCostInr: number;
  lineTotalInr: number;
}

export interface SampleHouse {
  id: string;
  name: string;
  imageSrc: string;
  imageWidth: number;
  imageHeight: number;
  totalGrossWallAreaSqft: number;
  netPaintableWallAreaSqft: number;
  renderPreviews: Record<string, string>;
  zones: Zone[];
}

export type WizardStep = 1 | 2 | 3 | 4 | 5;

export interface RateOverride {
  materialRateInr?: number;
  laborRateInr?: number;
}

export interface StudioState {
  step: WizardStep;
  house: SampleHouse | null;
  selectedZoneId: string | null;
  /** zoneId -> materialId */
  assignments: Record<string, string>;
  /** zoneId -> rate override */
  rateOverrides: Record<string, RateOverride>;
  activeMaterialTab: "instant" | "ai";
}
