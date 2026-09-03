// Client for the Phase 5 FastAPI backend (backend/api/). Replaces the client-side
// BoQ math port and the static precomputed preview JPEGs with real backend calls.
import { getMaterial } from "@/data/materials";
import type { BoQLineItem, BoQSummary, NeuralRenderJobStatus, RateOverride, SegmentResponse, Zone } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchBoQ(
  zones: Zone[],
  assignments: Record<string, string>,
  rateOverrides: Record<string, RateOverride>,
  contingencyPct = 5
): Promise<BoQSummary> {
  const assignedZones = zones.filter((z) => !z.isProtected && assignments[z.id]);

  const payload = {
    zones: assignedZones.map((z) => {
      const material = getMaterial(assignments[z.id]);
      return {
        zoneId: z.id,
        zoneName: z.displayName,
        materialId: material.id,
        unit: material.unit,
        grossAreaSqft: z.grossAreaSqft,
        deductionsSqft: z.deductionsSqft,
        runningFeet: z.runningFeet,
      };
    }),
    rateOverrides,
    contingencyPct,
  };

  const res = await fetch(`${API_BASE}/api/boq`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`BoQ request failed: ${res.status}`);
  }

  const data = await res.json();

  // The backend is authoritative for cost math; swap in the short display name
  // from the local catalog port since the backend returns the long catalog name.
  const items: BoQLineItem[] = data.items.map((item: BoQLineItem) => ({
    ...item,
    materialName: getMaterial(item.materialId).shortName,
  }));

  return { ...data, items };
}

export async function fetchRenderPreview(
  houseId: string,
  assignments: Record<string, string>
): Promise<{ imageDataUri: string; executionTimeMs: number }> {
  const res = await fetch(`${API_BASE}/api/render/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ houseId, assignments }),
  });

  if (!res.ok) {
    throw new Error(`Render preview request failed: ${res.status}`);
  }

  const data = await res.json();
  return { imageDataUri: data.imageDataUri, executionTimeMs: data.executionTimeMs };
}

export async function segmentUpload(file: File): Promise<SegmentResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/segment`, {
    method: "POST",
    body: formData,
  });

  if (res.status === 422) {
    const errorData = await res.json().catch(() => ({ detail: "Photo quality unusable" }));
    const msg = errorData.detail?.errors?.join(", ") || errorData.detail?.message || "Photo does not meet quality requirements.";
    throw new Error(msg);
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(typeof err.detail === "string" ? err.detail : `Segmentation failed (${res.status})`);
  }

  return res.json();
}

export async function startNeuralRenderJob(
  houseId: string,
  assignments: Record<string, string>
): Promise<{ jobId: string; status: string }> {
  const res = await fetch(`${API_BASE}/api/render/neural/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ houseId, assignments }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(typeof err.detail === "string" ? err.detail : `Neural render request failed: ${res.status}`);
  }

  return res.json();
}

export async function pollNeuralRenderJob(jobId: string): Promise<NeuralRenderJobStatus> {
  const res = await fetch(`${API_BASE}/api/render/neural/jobs/${jobId}`);

  if (!res.ok) {
    throw new Error(`Failed to check render status: ${res.status}`);
  }

  return res.json();
}
