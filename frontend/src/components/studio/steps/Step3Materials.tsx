"use client";

import { useState } from "react";
import Image from "next/image";
import { Check, Layers } from "lucide-react";
import { MATERIALS } from "@/data/materials";
import { LABEL_PLURAL } from "@/lib/boq";
import type { SampleHouse } from "@/types";
import { cn } from "@/lib/utils";

export default function Step3Materials({
  house,
  selectedZoneId,
  assignments,
  onAssignMaterial,
  onNext,
}: {
  house: SampleHouse;
  selectedZoneId: string | null;
  assignments: Record<string, string>;
  onAssignMaterial: (zoneIds: string[], materialId: string) => void;
  onNext: () => void;
}) {
  const [applyToAll, setApplyToAll] = useState(true);

  const selectedZone = house.zones.find((z) => z.id === selectedZoneId) ?? house.zones[0];
  const selectedMaterialId = selectedZone ? assignments[selectedZone.id] : undefined;
  const previewSrc = selectedMaterialId ? house.renderPreviews[selectedMaterialId] : undefined;
  const previewMaterial = selectedMaterialId ? MATERIALS.find((m) => m.id === selectedMaterialId) : undefined;

  const sameTypeZoneIds = selectedZone
    ? house.zones.filter((z) => !z.isProtected && z.label === selectedZone.label).map((z) => z.id)
    : [];
  const canApplyToAll = sameTypeZoneIds.length > 1;
  const groupLabel = selectedZone ? LABEL_PLURAL[selectedZone.label] ?? selectedZone.label : "";

  const handleAssign = (materialId: string) => {
    if (!selectedZone) return;
    onAssignMaterial(applyToAll && canApplyToAll ? sameTypeZoneIds : [selectedZone.id], materialId);
  };

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute -top-60 -left-24 w-[700px] h-[700px] rounded-full bg-[radial-gradient(circle,rgba(200,168,130,0.14)_0%,rgba(200,168,130,0)_70%)]" />
      <div className="pointer-events-none absolute -bottom-72 -right-28 w-[760px] h-[760px] rounded-full bg-[radial-gradient(circle,rgba(107,114,128,0.14)_0%,rgba(107,114,128,0)_70%)]" />

      <div className="relative z-10 flex gap-6 p-8" style={{ minHeight: "calc(100vh - 76px)" }}>
        <div className="w-[472px] flex-none flex flex-col gap-4">
          <div>
            <div className="font-display text-[17px] font-semibold text-text">Choose a Material</div>
            <div className="text-[12px] text-[#64748b] mt-0.5">
              Applying to:{" "}
              {applyToAll && canApplyToAll
                ? `${sameTypeZoneIds.length} ${groupLabel}`
                : selectedZone &&
                  `${selectedZone.displayName} · ${
                    selectedZone.category === "railing"
                      ? `${selectedZone.runningFeet.toFixed(1)} Rft`
                      : `${selectedZone.netAreaSqft.toFixed(1)} sq ft`
                  }`}
            </div>
          </div>

          {canApplyToAll && (
            <button
              type="button"
              onClick={() => setApplyToAll((v) => !v)}
              className={cn(
                "flex items-center gap-2.5 py-2.75 px-3.5 rounded-[13px] text-left transition-colors",
                applyToAll
                  ? "bg-gradient-to-br from-accent/16 to-accent/5 border border-accent/38"
                  : "bg-white/3 border border-white/8"
              )}
            >
              <span
                className={cn(
                  "w-4.5 h-4.5 rounded-[5px] border flex items-center justify-center flex-none",
                  applyToAll ? "bg-accent border-accent" : "border-white/25"
                )}
              >
                {applyToAll && <Check size={11} strokeWidth={3} className="text-[#241a0c]" />}
              </span>
              <Layers size={14} strokeWidth={2} className="text-accent flex-none" />
              <span className="text-[12.5px] text-text">
                Apply to all {sameTypeZoneIds.length} {groupLabel} at once
              </span>
            </button>
          )}

          <div className="grid grid-cols-2 gap-3.5">
            {MATERIALS.map((m) => {
              const isSelected = selectedZone && assignments[selectedZone.id] === m.id;
              const totalRate = m.materialRateInr + m.laborRateInr;
              return (
                <button
                  key={m.id}
                  type="button"
                  disabled={!selectedZone}
                  onClick={() => handleAssign(m.id)}
                  className={cn(
                    "text-left rounded-[18px] p-4 backdrop-blur-xl transition-shadow",
                    isSelected
                      ? "bg-gradient-to-br from-accent/18 to-accent/5 border-[1.5px] border-accent shadow-[0_0_0_4px_rgba(200,168,130,0.10),0_14px_34px_rgba(200,168,130,0.20),inset_0_1px_0_rgba(255,255,255,0.15)]"
                      : "bg-gradient-to-br from-white/6 to-white/1.5 border border-white/11 shadow-[0_10px_28px_rgba(0,0,0,0.30),inset_0_1px_0_rgba(255,255,255,0.08)]"
                  )}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span
                      className="w-8.5 h-8.5 rounded-full border-2"
                      style={{
                        background: `radial-gradient(circle at 32% 28%, ${m.swatchColor}dd, ${m.swatchColor})`,
                        borderColor: isSelected ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.18)",
                        boxShadow: `0 4px 12px ${m.swatchColor}55`,
                      }}
                    />
                    {isSelected ? (
                      <span className="w-5 h-5 rounded-full bg-accent flex items-center justify-center">
                        <Check size={12} strokeWidth={3} className="text-[#241a0c]" />
                      </span>
                    ) : selectedZone?.recommendedMaterials.includes(m.id) ? (
                      <span className="text-[9px] font-semibold py-0.75 px-1.75 rounded-[6px] bg-accent/14 text-accent">
                        RECOMMENDED
                      </span>
                    ) : null}
                  </div>
                  <div className="text-[13px] font-semibold text-text mb-0.5">{m.shortName}</div>
                  <div className={cn("text-[12px]", isSelected ? "text-[#e8d5b7]" : "text-[#64748b]")}>
                    &#8377;{totalRate.toLocaleString("en-IN")} / {m.unit === "Rft" ? "Rft" : "sq ft"}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex-1 flex flex-col gap-3.5">
          <div className="relative flex-1 rounded-[24px] overflow-hidden border border-white/12 bg-[#05070a] shadow-[0_24px_60px_rgba(0,0,0,0.45),inset_0_0_0_1px_rgba(255,255,255,0.06)] min-h-[400px]">
            <Image
              src={previewSrc ?? house.imageSrc}
              alt="Live material preview"
              fill
              className="object-cover"
            />
            <div className="absolute top-4 left-4 py-2 px-3.5 rounded-[11px] bg-gradient-to-br from-[#161920]/88 to-[#0e1015]/78 backdrop-blur-md border border-white/16 shadow-[0_8px_20px_rgba(0,0,0,0.4)]">
              <span className="text-[12px] font-semibold text-text">Live Preview</span>
              {previewMaterial && selectedZone && (
                <span className="text-[12px] text-text-muted">
                  {" "}
                  &middot; {selectedZone.displayName} &rarr; {previewMaterial.shortName}
                </span>
              )}
              {!previewSrc && (
                <span className="text-[12px] text-text-muted"> &middot; pick a material to preview</span>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between py-4.5 px-5.5 rounded-[20px] bg-gradient-to-br from-white/[0.075] to-white/2 backdrop-blur-2xl backdrop-saturate-150 border border-white/12 shadow-[0_16px_40px_rgba(0,0,0,0.35),inset_0_1px_0_rgba(255,255,255,0.09)]">
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2 text-[12px] text-text-muted">
                <Check size={13} strokeWidth={2.4} className="text-accent" /> Instant procedural preview (CPU, &lt;50ms)
              </div>
              <div className="flex items-center gap-2 text-[12px] text-text font-medium">
                <Check size={13} strokeWidth={2.4} className="text-accent" /> Pixel lock verified on windows &amp; sky
              </div>
            </div>
            <button
              type="button"
              onClick={onNext}
              className="font-display py-3.5 px-7.5 rounded-[14px] border border-white/25 bg-gradient-to-br from-[#ddc4a1] via-accent to-[#b8956d] text-[#241a0c] text-[14px] font-semibold whitespace-nowrap shadow-[0_14px_32px_rgba(200,168,130,0.35),inset_0_1px_0_rgba(255,255,255,0.35)]"
            >
              View Comparison &rarr;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
