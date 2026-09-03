"use client";

import { Lock } from "lucide-react";
import type { SampleHouse } from "@/types";
import { cn } from "@/lib/utils";
import ZoneCanvas from "../canvas/ZoneCanvas";

const ZONE_COLORS: Record<string, string> = {
  wall: "#f59e0b",
  pillar: "#10b981",
  balcony_railing: "#8b5cf6",
  roof_parapet: "#f43f5e",
  window: "#3b82f6",
  door: "#3b82f6",
};

const STAT_GROUPS: { key: string; label: string; labels: string[] }[] = [
  { key: "wall", label: "Walls", labels: ["wall"] },
  { key: "window", label: "Windows", labels: ["window", "door"] },
  { key: "railing", label: "Railings", labels: ["balcony_railing"] },
  { key: "roof", label: "Roof", labels: ["roof_parapet"] },
];

export default function Step2Zones({
  house,
  selectedZoneId,
  assignments,
  onSelectZone,
  onNext,
}: {
  house: SampleHouse;
  selectedZoneId: string | null;
  assignments: Record<string, string>;
  onSelectZone: (zoneId: string) => void;
  onNext: () => void;
}) {
  const assignableZones = house.zones.filter((z) => !z.isProtected);
  const protectedCount = house.zones.length - assignableZones.length;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute -top-64 -right-24 w-[760px] h-[760px] rounded-full bg-[radial-gradient(circle,rgba(139,92,246,0.10)_0%,rgba(139,92,246,0)_70%)]" />
      <div className="pointer-events-none absolute -bottom-72 -left-36 w-[640px] h-[640px] rounded-full bg-[radial-gradient(circle,rgba(200,168,130,0.10)_0%,rgba(200,168,130,0)_70%)]" />

      <div className="relative z-10 flex gap-6 p-8" style={{ height: "calc(100vh - 76px)" }}>
        <div className="w-[320px] flex-none rounded-[22px] bg-gradient-to-br from-white/[0.075] to-white/2 backdrop-blur-2xl backdrop-saturate-150 border border-white/12 shadow-[0_16px_44px_rgba(0,0,0,0.38),inset_0_1px_0_rgba(255,255,255,0.09)] p-5.5 flex flex-col gap-5">
          <div>
            <div className="font-display text-[17px] font-semibold text-text">Detected Zones</div>
            <div className="text-[12px] text-[#64748b] mt-0.5">
              {house.zones.length} architectural elements found
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            {STAT_GROUPS.map((g) => {
              const count = house.zones.filter((z) => g.labels.includes(z.label)).length;
              return (
                <div
                  key={g.key}
                  className="rounded-[14px] bg-gradient-to-br from-white/5 to-white/1 border border-white/9 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] p-3"
                >
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <span
                      className="w-1.75 h-1.75 rounded-full"
                      style={{
                        background: ZONE_COLORS[g.labels[0]],
                        boxShadow: `0 0 6px ${ZONE_COLORS[g.labels[0]]}b0`,
                      }}
                    />
                    <span className="text-[11px] text-[#64748b]">{g.label}</span>
                  </div>
                  <div className="font-display text-[20px] font-semibold text-text">{count}</div>
                </div>
              );
            })}
          </div>

          <div className="h-px bg-white/8" />

          <div className="flex flex-col gap-2 overflow-y-auto flex-1">
            {assignableZones.map((zone) => {
              const isSelected = zone.id === selectedZoneId;
              const materialId = assignments[zone.id];
              return (
                <button
                  key={zone.id}
                  type="button"
                  onClick={() => onSelectZone(zone.id)}
                  className={cn(
                    "flex items-center gap-2.5 py-2.75 px-3 rounded-[13px] text-left transition-colors",
                    isSelected
                      ? "bg-gradient-to-br from-accent/16 to-accent/5 border border-accent/38 shadow-[0_0_0_1px_rgba(200,168,130,0.15),0_8px_20px_rgba(200,168,130,0.14)]"
                      : "bg-white/3 border border-white/6 hover:bg-white/5"
                  )}
                >
                  <span
                    className="w-2.25 h-2.25 rounded-full flex-none"
                    style={{
                      background: ZONE_COLORS[zone.label],
                      boxShadow: `0 0 6px ${ZONE_COLORS[zone.label]}b0`,
                    }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-[13px] font-semibold text-text truncate">{zone.displayName}</div>
                    <div className="text-[11px] text-[#64748b]">
                      {zone.category === "railing"
                        ? `${zone.runningFeet.toFixed(1)} Rft`
                        : `${zone.netAreaSqft.toFixed(1)} sq ft`}
                    </div>
                  </div>
                  <span
                    className={cn(
                      "text-[10px] font-semibold py-1 px-2 rounded-[6px] whitespace-nowrap",
                      isSelected
                        ? "bg-accent/22 text-[#f2e4d3]"
                        : materialId
                          ? "bg-emerald-500/15 text-emerald-300"
                          : "bg-white/6 text-[#64748b]"
                    )}
                  >
                    {isSelected ? "Selected" : materialId ? "Assigned" : "Unassigned"}
                  </span>
                </button>
              );
            })}

            {house.zones
              .filter((z) => z.isProtected)
              .slice(0, 6)
              .map((zone) => (
                <div
                  key={zone.id}
                  className="flex items-center gap-2.5 py-2.75 px-3 rounded-[13px] bg-white/[0.018] border border-white/5 opacity-65"
                >
                  <span className="w-2.25 h-2.25 rounded-full flex-none" style={{ background: "#3b82f6" }} />
                  <div className="flex-1 min-w-0">
                    <div className="text-[13px] font-semibold text-text truncate">{zone.displayName}</div>
                    <div className="text-[11px] text-[#64748b]">{zone.netAreaSqft.toFixed(1)} sq ft</div>
                  </div>
                  <Lock size={13} strokeWidth={2} className="text-[#64748b]" />
                </div>
              ))}
            {protectedCount > 6 && (
              <div className="text-[11px] text-[#475569] text-center py-1.5">
                +{protectedCount - 6} more protected windows
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={onNext}
            className="font-display py-3.5 rounded-[13px] border border-white/25 bg-gradient-to-br from-[#ddc4a1] via-accent to-[#b8956d] text-[#241a0c] text-[14px] font-semibold shadow-[0_12px_28px_rgba(200,168,130,0.30),inset_0_1px_0_rgba(255,255,255,0.35)]"
          >
            Continue to Materials &rarr;
          </button>
        </div>

        <div className="flex-1 flex flex-col gap-3.5">
          <div className="flex items-center gap-4.5 py-3 px-4.5 rounded-full bg-gradient-to-br from-white/6 to-white/1.5 backdrop-blur-xl border border-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] w-fit">
            {[
              { label: "Wall", color: ZONE_COLORS.wall },
              { label: "Pillar", color: ZONE_COLORS.pillar },
              { label: "Railing", color: ZONE_COLORS.balcony_railing },
              { label: "Roof", color: ZONE_COLORS.roof_parapet },
              { label: "Window · locked", color: ZONE_COLORS.window },
            ].map((l) => (
              <div key={l.label} className="flex items-center gap-1.5">
                <span className="w-2.25 h-2.25 rounded-[2px]" style={{ background: l.color }} />
                <span className="text-[11px] text-[#94a3b8]">{l.label}</span>
              </div>
            ))}
          </div>

          <ZoneCanvas
            imageSrc={house.imageSrc}
            imageWidth={house.imageWidth}
            imageHeight={house.imageHeight}
            zones={house.zones}
            selectedZoneId={selectedZoneId}
            assignments={assignments}
            onZoneClick={onSelectZone}
          />
        </div>
      </div>
    </div>
  );
}
