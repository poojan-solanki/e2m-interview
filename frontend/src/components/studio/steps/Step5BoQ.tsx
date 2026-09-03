"use client";

import { useEffect, useMemo, useState } from "react";
import { Download, Lock } from "lucide-react";
import { fetchBoQ } from "@/lib/api";
import { formatINR, groupBoQItems } from "@/lib/boq";
import type { BoQSummary, RateOverride, SampleHouse } from "@/types";
import ReportModal from "../report/ReportModal";

const ZONE_COLORS: Record<string, string> = {
  wall: "#f59e0b",
  pillar: "#10b981",
  balcony_railing: "#8b5cf6",
  roof_parapet: "#f43f5e",
  window: "#3b82f6",
};

const EMPTY_SUMMARY: BoQSummary = {
  items: [],
  totalMaterialCostInr: 0,
  totalLaborCostInr: 0,
  subtotalInr: 0,
  contingencyPct: 5,
  contingencyAmountInr: 0,
  grandTotalInr: 0,
};

export default function Step5BoQ({
  house,
  assignments,
  rateOverrides,
  onRateOverride,
}: {
  house: SampleHouse;
  assignments: Record<string, string>;
  rateOverrides: Record<string, RateOverride>;
  onRateOverride: (zoneIds: string[], override: RateOverride) => void;
}) {
  const [reportOpen, setReportOpen] = useState(false);
  const [summary, setSummary] = useState<BoQSummary>(EMPTY_SUMMARY);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(false);

  const assignedZoneCount = useMemo(
    () => house.zones.filter((z) => !z.isProtected && assignments[z.id]).length,
    [house.zones, assignments]
  );

  // Debounced: rate override inputs fire on every keystroke, and the BoQ math
  // now lives server-side (backend/engine/boq_calculator.py is the source of truth).
  // No zones assigned is handled as derived state below rather than reset here,
  // so this effect never needs to setState synchronously on its own body.
  useEffect(() => {
    if (assignedZoneCount === 0) {
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      setLoading(true);
      fetchBoQ(house.zones, assignments, rateOverrides)
        .then((result) => {
          if (cancelled) return;
          setSummary(result);
          setLoadError(false);
        })
        .catch(() => {
          if (!cancelled) setLoadError(true);
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [house.zones, assignments, rateOverrides, assignedZoneCount]);

  const displaySummary = assignedZoneCount === 0 ? EMPTY_SUMMARY : summary;
  const displayLoadError = assignedZoneCount > 0 && loadError;

  const groups = useMemo(
    () => groupBoQItems(displaySummary.items, house.zones),
    [displaySummary.items, house.zones]
  );

  const protectedWindowCount = house.zones.filter((z) => z.isProtected).length;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute -top-64 -right-24 w-[760px] h-[760px] rounded-full bg-[radial-gradient(circle,rgba(200,168,130,0.13)_0%,rgba(200,168,130,0)_70%)]" />
      <div className="pointer-events-none absolute -bottom-72 -left-36 w-[640px] h-[640px] rounded-full bg-[radial-gradient(circle,rgba(59,130,246,0.09)_0%,rgba(59,130,246,0)_70%)]" />

      <div className="relative z-10 flex gap-6 p-8">
        <div className="flex-1 flex flex-col gap-5">
          <div>
            <div className="font-display text-[20px] font-semibold text-text">Bill of Quantities</div>
            <div className="text-[12px] text-[#64748b] mt-1">Ahmedabad market rates &middot; editable below</div>
          </div>

          {displayLoadError && (
            <div className="rounded-2xl bg-gradient-to-br from-red-500/10 to-red-500/3 backdrop-blur-md border border-red-500/24 p-4 text-[12px] text-red-300">
              Couldn&apos;t reach the pricing backend. Make sure the API server is running (
              <code className="text-red-200">uv run uvicorn backend.api.main:app --reload --port 8000</code>).
            </div>
          )}

          {displaySummary.items.length === 0 ? (
            <div className="rounded-[22px] bg-gradient-to-br from-white/[0.075] to-white/2 backdrop-blur-2xl border border-white/12 p-10 text-center text-[13px] text-text-muted">
              No zones have a material assigned yet. Go back to Materials and assign at least one zone to
              see costs here.
            </div>
          ) : (
            <div
              className={`rounded-[22px] bg-gradient-to-br from-white/[0.075] to-white/2 backdrop-blur-2xl backdrop-saturate-150 border border-white/12 shadow-[0_18px_48px_rgba(0,0,0,0.38),inset_0_1px_0_rgba(255,255,255,0.09)] p-6.5 transition-opacity ${
                loading ? "opacity-60" : "opacity-100"
              }`}
            >
              <table className="w-full border-collapse">
                <thead>
                  <tr className="text-left">
                    {["Zone", "Material", "Net Qty", "Material Rate", "Labor Rate", ""].map((h, i) => (
                      <th
                        key={h}
                        className={`text-[11px] tracking-[0.06em] uppercase text-[#64748b] font-semibold pb-3.5 px-2 ${
                          i === 5 ? "text-right" : ""
                        }`}
                      >
                        {h || "Line Total"}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {groups.map((group) => {
                    const zone = house.zones.find((z) => z.id === group.zoneIds[0])!;
                    return (
                      <tr key={group.groupKey} className="border-t border-white/7">
                        <td className="py-4 px-2">
                          <div className="flex items-center gap-2">
                            <span
                              className="w-2 h-2 rounded-full"
                              style={{
                                background: ZONE_COLORS[zone.label] ?? "#94a3b8",
                                boxShadow: `0 0 6px ${ZONE_COLORS[zone.label] ?? "#94a3b8"}b0`,
                              }}
                            />
                            <span className="font-semibold text-text text-[13px]">{group.displayName}</span>
                          </div>
                        </td>
                        <td className="py-4 px-2 text-[13px] text-[#e2e8f0]">{group.materialName}</td>
                        <td className="py-4 px-2 text-[13px] text-[#e2e8f0]">
                          {group.netArea.toFixed(1)} {group.unit === "Rft" ? "Rft" : "sq ft"}
                        </td>
                        <td className="py-4 px-2 text-[13px]">
                          <input
                            type="number"
                            value={group.unitMaterialRateInr}
                            onChange={(e) =>
                              onRateOverride(group.zoneIds, { materialRateInr: Number(e.target.value) })
                            }
                            className="w-20 bg-transparent border-b border-dashed border-accent/45 text-[#e2e8f0] focus:outline-none focus:border-accent"
                          />
                        </td>
                        <td className="py-4 px-2 text-[13px]">
                          <input
                            type="number"
                            value={group.unitLaborRateInr}
                            onChange={(e) =>
                              onRateOverride(group.zoneIds, { laborRateInr: Number(e.target.value) })
                            }
                            className="w-20 bg-transparent border-b border-dashed border-accent/45 text-[#e2e8f0] focus:outline-none focus:border-accent"
                          />
                        </td>
                        <td className="py-4 px-2 text-right font-semibold text-text text-[13px]">
                          {formatINR(group.lineTotalInr)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex items-center gap-2.5 py-3.5 px-4.5 rounded-2xl bg-gradient-to-br from-blue-500/10 to-blue-500/3 backdrop-blur-md border border-blue-500/24 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
            <Lock size={15} strokeWidth={2} className="text-blue-300" />
            <span className="text-[12px] text-blue-300">
              {protectedWindowCount} windows excluded from renovation cost &mdash; structurally protected,
              no material applied
            </span>
          </div>
        </div>

        <div className="w-[340px] flex-none flex flex-col gap-4">
          <div className="rounded-[22px] bg-gradient-to-br from-white/8 to-white/2 backdrop-blur-2xl backdrop-saturate-150 border border-white/13 shadow-[0_20px_50px_rgba(0,0,0,0.42),inset_0_1px_0_rgba(255,255,255,0.10)] p-6.5">
            <div className="font-display text-[15px] font-semibold text-text mb-4.5">Cost Summary</div>

            <div className="flex justify-between mb-3 text-[13px]">
              <span className="text-text-muted">Material subtotal</span>
              <span className="text-[#e2e8f0]">{formatINR(displaySummary.totalMaterialCostInr)}</span>
            </div>
            <div className="flex justify-between mb-3 text-[13px]">
              <span className="text-text-muted">Labor subtotal</span>
              <span className="text-[#e2e8f0]">{formatINR(displaySummary.totalLaborCostInr)}</span>
            </div>
            <div className="flex justify-between mb-4.5 text-[13px]">
              <span className="text-text-muted">Contingency ({displaySummary.contingencyPct}%)</span>
              <span className="text-[#e2e8f0]">{formatINR(displaySummary.contingencyAmountInr)}</span>
            </div>

            <div className="h-px bg-white/10 mb-4.5" />

            <div className="mb-1.5">
              <span className="text-[12px] tracking-[0.06em] uppercase text-accent font-semibold">
                Grand Total
              </span>
            </div>
            <div className="font-display text-[32px] font-bold mb-5.5 bg-gradient-to-br from-white to-[#e8d5b7] bg-clip-text text-transparent">
              {formatINR(displaySummary.grandTotalInr)}
            </div>

            <button
              type="button"
              disabled={displaySummary.items.length === 0}
              onClick={() => setReportOpen(true)}
              className="w-full py-3.75 rounded-[14px] border border-white/25 bg-gradient-to-br from-[#ddc4a1] via-accent to-[#b8956d] text-[#241a0c] text-[14px] font-semibold shadow-[0_14px_32px_rgba(200,168,130,0.35),inset_0_1px_0_rgba(255,255,255,0.35)] flex items-center justify-center gap-2 disabled:opacity-40"
            >
              <Download size={15} strokeWidth={2.2} />
              Download Contractor Report
            </button>
          </div>

          <div className="text-[11px] leading-relaxed text-[#475569] px-1">
            Estimates are advisory and generated from AI-detected surface areas. Final costs are subject
            to on-site verification.
          </div>
        </div>
      </div>

      {reportOpen && (
        <ReportModal house={house} summary={displaySummary} groups={groups} onClose={() => setReportOpen(false)} />
      )}
    </div>
  );
}
