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

export type WizardStep = 1 | 2 | 3 | 4;

export interface RateOverride {
  materialRateInr?: number;
  laborRateInr?: number;
}

export interface StudioState {
  step: WizardStep;
  /** Furthest step reached so far — lets the header show/allow jumping back to any
   * previously-visited step without losing its "completed" styling when you do. */
  maxStepReached: WizardStep;
  house: SampleHouse | null;
  /** Paint-bucket model: pick a material, then click zones to paint them with it —
   * any number of zones can end up on different materials this way. null = nothing
   * active, clicking a zone does nothing. See /api/render/preview and
   * /api/render/neural's multi-material compositing, which is what this feeds. */
  activeMaterialId: string | null;
  /** zoneId -> materialId */
  assignments: Record<string, string>;
  /** zoneId -> rate override */
  rateOverrides: Record<string, RateOverride>;
  activeMaterialTab: "instant" | "ai";
  /** The actual rendered "after" image shown in Step 4 (instant preview or AI neural
   * render, whichever the user last viewed) — carried into the Step 5 quote/report so
   * it reflects the real render instead of a disconnected static fallback. */
  renderedImageSrc: string | null;
}

export interface SegmentResponse {
  houseId: string;
  imageWidth: number;
  imageHeight: number;
  totalGrossWallAreaSqft: number;
  netPaintableWallAreaSqft: number;
  scaleFactorSqftPerSqPixel: number;
  calibrationMethod: string;
  qualityWarnings: string[];
  zones: Zone[];
}

export interface NeuralRenderJobStatus {
  jobId: string;
  status: "pending" | "running" | "done" | "error";
  imageUrl?: string | null;
  errorMessage?: string | null;
  elapsedSec?: number | null;
  currentMaterialIndex?: number | null;
  totalMaterials?: number | null;
  currentMaterialId?: string | null;
}
