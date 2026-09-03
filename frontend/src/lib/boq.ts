// Port of backend/engine/boq_calculator.py's calculate_line_item / calculate_boq.
// Key rule (verified against the Python source): material cost is charged on the
// wastage-inflated GROSS area, labor cost is charged on the NET (as-installed) area.
import type { BoQGroup, BoQLineItem, BoQSummary, Material, Zone } from "@/types";

export const LABEL_PLURAL: Record<string, string> = {
  wall: "Walls",
  pillar: "Pillars",
  balcony_railing: "Balcony Railings",
  roof_parapet: "Roof Parapets",
  window: "Windows",
  door: "Doors",
};

const round2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100;

export function calculateLineItem(
  zone: Zone,
  material: Material,
  rateOverride?: { materialRateInr?: number; laborRateInr?: number }
): BoQLineItem {
  const isLinear = material.unit === "Rft";
  const netArea = isLinear ? zone.runningFeet : zone.netAreaSqft;

  const wastageAllowance = round2(netArea * material.wastageFactor);
  const grossMaterialArea = round2(netArea + wastageAllowance);

  const matRate = rateOverride?.materialRateInr ?? material.materialRateInr;
  const labRate = rateOverride?.laborRateInr ?? material.laborRateInr;

  const materialCostInr = round2(grossMaterialArea * matRate);
  const laborCostInr = round2(netArea * labRate);
  const lineTotalInr = round2(materialCostInr + laborCostInr);

  return {
    zoneId: zone.id,
    zoneName: zone.displayName,
    materialId: material.id,
    materialName: material.shortName,
    unit: material.unit,
    netArea,
    wastagePct: round2(material.wastageFactor * 100),
    grossMaterialArea,
    unitMaterialRateInr: matRate,
    unitLaborRateInr: labRate,
    materialCostInr,
    laborCostInr,
    lineTotalInr,
  };
}

export function calculateBoQ(
  items: BoQLineItem[],
  contingencyPct = 0.05
): BoQSummary {
  const totalMaterialCostInr = round2(items.reduce((s, i) => s + i.materialCostInr, 0));
  const totalLaborCostInr = round2(items.reduce((s, i) => s + i.laborCostInr, 0));
  const subtotalInr = round2(totalMaterialCostInr + totalLaborCostInr);
  const contingencyAmountInr = round2(subtotalInr * contingencyPct);
  const grandTotalInr = round2(subtotalInr + contingencyAmountInr);

  return {
    items,
    totalMaterialCostInr,
    totalLaborCostInr,
    subtotalInr,
    contingencyPct: round2(contingencyPct * 100),
    contingencyAmountInr,
    grandTotalInr,
  };
}

/** Collapses line items that share the same zone label + material into one display row. */
export function groupBoQItems(items: BoQLineItem[], zones: Zone[]): BoQGroup[] {
  const zoneById = new Map(zones.map((z) => [z.id, z]));
  const groups = new Map<string, BoQGroup>();

  for (const item of items) {
    const zone = zoneById.get(item.zoneId);
    const label = zone?.label ?? "zone";
    const key = `${label}::${item.materialId}`;
    const existing = groups.get(key);

    if (existing) {
      existing.zoneIds.push(item.zoneId);
      existing.zoneCount += 1;
      existing.netArea = round2(existing.netArea + item.netArea);
      existing.materialCostInr = round2(existing.materialCostInr + item.materialCostInr);
      existing.laborCostInr = round2(existing.laborCostInr + item.laborCostInr);
      existing.lineTotalInr = round2(existing.lineTotalInr + item.lineTotalInr);
      existing.displayName = `${LABEL_PLURAL[label] ?? label} ×${existing.zoneCount}`;
    } else {
      groups.set(key, {
        groupKey: key,
        zoneIds: [item.zoneId],
        zoneCount: 1,
        displayName: item.zoneName,
        materialId: item.materialId,
        materialName: item.materialName,
        unit: item.unit,
        netArea: item.netArea,
        wastagePct: item.wastagePct,
        unitMaterialRateInr: item.unitMaterialRateInr,
        unitLaborRateInr: item.unitLaborRateInr,
        materialCostInr: item.materialCostInr,
        laborCostInr: item.laborCostInr,
        lineTotalInr: item.lineTotalInr,
      });
    }
  }

  return Array.from(groups.values()).sort((a, b) => b.lineTotalInr - a.lineTotalInr);
}

export function formatINR(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}
