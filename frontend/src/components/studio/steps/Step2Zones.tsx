"use client";

import { useState } from "react";
import { ChevronLeft, Lock, Sparkles, Wand2 } from "lucide-react";
import { MATERIALS, getMaterial } from "@/data/materials";
import type { SampleHouse } from "@/types";
import { cn } from "@/lib/utils";
import ZoneCanvas from "../canvas/ZoneCanvas";

// UI-only preview of a feature not wired to the backend yet — a free-text style
// prompt sent straight to the ControlNet+SD render instead of a fixed catalog
// material. The backend already accepts a `custom_style` modifier
// (backend/renderer/material_prompter.py::get_material_prompt), it's just never
// threaded from the API through to there. To make this real:
//   1. backend/api/schemas.py — NeuralRenderJobRequest/RenderPreviewRequest's
//      `assignments: Dict[str, str]` (zoneId -> materialId) would need to become
//      `Dict[str, {materialId?: str, customPrompt?: str}]`, since a custom style
//      has no catalog id and no fixed BoQ rate.
//   2. backend/api/routes/neural_render.py — the per-material-pass loop groups
//      zones by materialId and calls demo_render.py --material <id>; a custom-prompt
//      group would instead need demo_render.py --style "<prompt>" (the CLI flag
//      already exists, just unused by this route).
//   3. backend/engine/boq_calculator.py — a custom-prompt zone has no catalog rate,
//      so the BoQ would need a fallback (e.g. a flagged "contractor to quote" line)
//      instead of crashing on an unknown materialId.
// Until that's done, this UI only demonstrates the interaction locally — activating
// a custom style here doesn't add it to `assignments`, so it never reaches the
// backend or the quote.
interface CustomStyle {
  id: string;
  text: string;
}

const ZONE_COLORS: Record<string, string> = {
  wall: "#f59e0b",
  pillar: "#10b981",
  balcony_railing: "#8b5cf6",
  roof_parapet: "#f43f5e",
  window: "#3b82f6",
};

export default function Step2Zones({
  house,
  activeMaterialId,
  assignments,
  onSetActiveMaterial,
  onAssignMaterial,
  onUnassignZone,
  onBack,
  onNext,
}: {
  house: SampleHouse;
  activeMaterialId: string | null;
  assignments: Record<string, string>;
  onSetActiveMaterial: (materialId: string | null) => void;
  onAssignMaterial: (zoneIds: string[], materialId: string) => void;
  onUnassignZone: (zoneId: string) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const [customStyles, setCustomStyles] = useState<CustomStyle[]>([]);
  const [activeCustomId, setActiveCustomId] = useState<string | null>(null);
  const [customInputOpen, setCustomInputOpen] = useState(false);
  const [customInputValue, setCustomInputValue] = useState("");

  const assignableZones = house.zones.filter((z) => !z.isProtected);
  const protectedCount = house.zones.length - assignableZones.length;
  const activeMaterial = activeMaterialId ? getMaterial(activeMaterialId) : null;
  const activeCustom = activeCustomId ? customStyles.find((c) => c.id === activeCustomId) : null;

  function selectMaterial(id: string | null) {
    setActiveCustomId(null);
    onSetActiveMaterial(id);
  }

  function activateCustom(id: string | null) {
    onSetActiveMaterial(null);
    setActiveCustomId(id);
  }

  function submitCustomStyle() {
    const text = customInputValue.trim();
    if (!text) return;
    const id = `draft-${Date.now()}`;
    setCustomStyles((prev) => [...prev, { id, text }]);
    setCustomInputValue("");
    setCustomInputOpen(false);
    activateCustom(id);
  }

  const compatibleZones = activeMaterialId
    ? assignableZones.filter((z) => z.recommendedMaterials.includes(activeMaterialId))
    : [];
  const pendingZones = compatibleZones.filter((z) => assignments[z.id] !== activeMaterialId);

  function handleZoneClick(zoneId: string) {
    const zone = house.zones.find((z) => z.id === zoneId);
    if (!zone || zone.isProtected) return;

    if (!activeMaterialId) {
      if (assignments[zoneId]) onUnassignZone(zoneId);
      return;
    }
    if (!zone.recommendedMaterials.includes(activeMaterialId)) return;
    if (assignments[zoneId] === activeMaterialId) {
      onUnassignZone(zoneId);
    } else {
      onAssignMaterial([zoneId], activeMaterialId);
    }
  }

  // How many zones already carry each assigned material — the whole point of the
  // paint-bucket model is that different zones can end up on different materials,
  // so surfacing that breakdown makes the capability visible as you go.
  const materialCounts = new Map<string, number>();
  for (const materialId of Object.values(assignments)) {
    materialCounts.set(materialId, (materialCounts.get(materialId) ?? 0) + 1);
  }
  const assignedCount = Object.keys(assignments).length;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute -top-64 -right-24 w-[760px] h-[760px] rounded-full bg-[radial-gradient(circle,rgba(139,92,246,0.10)_0%,rgba(139,92,246,0)_70%)]" />
      <div className="pointer-events-none absolute -bottom-72 -left-36 w-[640px] h-[640px] rounded-full bg-[radial-gradient(circle,rgba(200,168,130,0.10)_0%,rgba(200,168,130,0)_70%)]" />

      <div className="relative z-10 flex gap-6 p-8" style={{ height: "calc(100vh - 76px)" }}>
        {/* MATERIAL PALETTE */}
        <div className="w-[280px] flex-none rounded-[22px] bg-gradient-to-br from-white/[0.075] to-white/2 backdrop-blur-2xl backdrop-saturate-150 border border-white/12 shadow-[0_16px_44px_rgba(0,0,0,0.38),inset_0_1px_0_rgba(255,255,255,0.09)] p-5.5 flex flex-col gap-3.5 overflow-y-auto">
          <div>
            <div className="font-display text-[17px] font-semibold text-text">Materials</div>
            <div className="text-[12px] text-[#64748b] mt-0.5">
              Pick one, then click zones on the photo to paint them.
            </div>
          </div>

          {MATERIALS.map((m) => {
            const isActive = activeMaterialId === m.id;
            const count = materialCounts.get(m.id) ?? 0;
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => selectMaterial(isActive ? null : m.id)}
                className={cn(
                  "flex items-center gap-2.5 py-2.5 px-3 rounded-[14px] text-left transition-colors",
                  isActive
                    ? "bg-gradient-to-br from-accent/20 to-accent/5 border border-accent shadow-[0_0_0_3px_rgba(200,168,130,0.12)]"
                    : "bg-white/3 border border-white/8 hover:bg-white/5"
                )}
              >
                <span
                  className="w-[22px] h-[22px] rounded-[7px] border border-white/20 flex-none"
                  style={{ background: m.swatchColor }}
                />
                <span className="flex-1 min-w-0">
                  <span className="block text-[12.5px] font-semibold text-text truncate">{m.shortName}</span>
                  <span className="block text-[11px] text-[#64748b] mono">
                    &#8377;{m.materialRateInr}/{m.unit === "Rft" ? "Rft" : "sq ft"}
                    {count > 0 ? ` · ${count} zone${count === 1 ? "" : "s"}` : ""}
                  </span>
                </span>
              </button>
            );
          })}

          <div className="flex items-center gap-2 mt-1 mb-[-6px]">
            <div className="flex-1 h-px bg-white/8" />
            <span className="text-[9.5px] tracking-[0.08em] uppercase text-[#64748b] font-semibold">
              Or write your own
            </span>
            <div className="flex-1 h-px bg-white/8" />
          </div>

          {customStyles.map((c) => {
            const isActive = activeCustomId === c.id;
            return (
              <button
                key={c.id}
                type="button"
                onClick={() => activateCustom(isActive ? null : c.id)}
                className={cn(
                  "flex items-center gap-2.5 py-2.5 px-3 rounded-[14px] text-left transition-colors",
                  isActive
                    ? "bg-gradient-to-br from-accent/20 to-accent/5 border border-accent shadow-[0_0_0_3px_rgba(200,168,130,0.12)]"
                    : "bg-white/3 border border-white/8 hover:bg-white/5"
                )}
              >
                <span className="w-[22px] h-[22px] rounded-[7px] border border-white/20 flex-none flex items-center justify-center bg-[conic-gradient(from_220deg,#d4ad7a,#7fa8bf,#a78bfa,#d4ad7a)]">
                  <Wand2 size={11} className="text-[#0b0c0f]" />
                </span>
                <span className="flex-1 min-w-0">
                  <span className="block text-[12px] font-semibold text-text truncate">{c.text}</span>
                  <span className="block text-[10.5px] text-[#64748b]">Draft prompt · preview only</span>
                </span>
              </button>
            );
          })}

          {customInputOpen ? (
            <div className="flex flex-col gap-2 p-2.5 rounded-[13px] bg-white/4 border border-white/16">
              <input
                autoFocus
                type="text"
                value={customInputValue}
                onChange={(e) => setCustomInputValue(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submitCustomStyle()}
                placeholder="e.g. reclaimed dark walnut siding, matte black trim"
                maxLength={140}
                className="bg-white/4 border border-white/10 rounded-[9px] py-2 px-2.5 text-[12px] text-text placeholder:text-[#5b6472] outline-none focus:border-accent"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setCustomInputOpen(false);
                    setCustomInputValue("");
                  }}
                  className="flex-1 py-1.75 rounded-[8px] border border-white/15 text-[11px] font-semibold text-text-muted"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={submitCustomStyle}
                  className="flex-1 py-1.75 rounded-[8px] bg-accent text-[#241a0c] text-[11px] font-semibold"
                >
                  Add &amp; activate
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setCustomInputOpen(true)}
              className="flex items-center gap-2.5 py-2.5 px-3 rounded-[14px] text-left bg-white/3 border border-dashed border-white/16 hover:bg-white/5 transition-colors"
            >
              <span className="w-[22px] h-[22px] rounded-[7px] border border-white/20 flex-none flex items-center justify-center bg-[conic-gradient(from_220deg,#d4ad7a,#7fa8bf,#a78bfa,#d4ad7a)]">
                <Wand2 size={11} className="text-[#0b0c0f]" />
              </span>
              <span className="flex-1 min-w-0">
                <span className="block text-[12px] font-semibold text-text">Custom Style&hellip;</span>
                <span className="block text-[10.5px] text-[#64748b]">Type a prompt for Stable Diffusion</span>
              </span>
            </button>
          )}

          {activeMaterial ? (
            <div className="mt-1 py-2.75 px-3 rounded-[13px] bg-accent/8 border border-dashed border-accent/35 text-[11.5px] text-[#e8d5b7] leading-relaxed">
              <b className="text-text">{activeMaterial.shortName}</b> is active &mdash; {compatibleZones.length} zone
              {compatibleZones.length === 1 ? "" : "s"} on this facade accept it. Click one on the photo, or:
              {pendingZones.length > 0 && (
                <button
                  type="button"
                  onClick={() => onAssignMaterial(pendingZones.map((z) => z.id), activeMaterialId!)}
                  className="mt-2 w-full flex items-center justify-center gap-1.5 py-2 rounded-[10px] bg-accent text-[#241a0c] font-semibold text-[11.5px]"
                >
                  <Sparkles size={12} /> Paint all {pendingZones.length} compatible zone
                  {pendingZones.length === 1 ? "" : "s"}
                </button>
              )}
            </div>
          ) : activeCustom ? (
            <div className="mt-1 py-2.75 px-3 rounded-[13px] bg-amber-500/8 border border-dashed border-amber-400/35 text-[11.5px] text-amber-200 leading-relaxed">
              <b className="text-text">&ldquo;{activeCustom.text}&rdquo;</b> is active as a preview only &mdash; custom
              prompts aren&apos;t wired to the render or quote yet. Clicking zones won&apos;t assign anything real
              until the backend supports it (see the TODO at the top of this file).
            </div>
          ) : (
            <div className="mt-1 py-2.75 px-3 rounded-[13px] bg-white/3 border border-white/8 text-[11.5px] text-[#64748b] leading-relaxed">
              Nothing active. Pick a material above, or click an already-painted zone to remove it.
            </div>
          )}
        </div>

        {/* CANVAS */}
        <div className="flex-1 flex flex-col gap-3.5 min-w-0">
          <div className="flex items-center justify-between">
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
            <div className="text-[12px] text-[#64748b]">
              {house.zones.length} zones &middot; {assignableZones.length} assignable &middot; {protectedCount}{" "}
              protected
            </div>
          </div>

          <ZoneCanvas
            imageSrc={house.imageSrc}
            imageWidth={house.imageWidth}
            imageHeight={house.imageHeight}
            zones={house.zones}
            activeMaterialId={activeMaterialId}
            assignments={assignments}
            onZoneClick={handleZoneClick}
          />

          <div className="flex items-center justify-between py-3.5 px-4.5 rounded-[18px] bg-gradient-to-br from-white/6 to-white/1.5 backdrop-blur-xl border border-white/10">
            <span className="text-[12px] text-[#94a3b8]">
              <b className="text-text">{assignedCount}</b> / {assignableZones.length} zones assigned &middot;{" "}
              <b className="text-text">{materialCounts.size}</b> distinct material{materialCounts.size === 1 ? "" : "s"}
            </span>
            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={onBack}
                className="py-3 px-4 rounded-[13px] border border-white/15 bg-white/4 text-text-muted hover:text-text hover:bg-white/7 transition-colors flex items-center justify-center"
              >
                <ChevronLeft size={16} strokeWidth={2.2} />
              </button>
              <button
                type="button"
                onClick={onNext}
                className="font-display py-3 px-6 rounded-[13px] border border-white/25 bg-gradient-to-br from-[#ddc4a1] via-accent to-[#b8956d] text-[#241a0c] text-[13.5px] font-semibold shadow-[0_12px_28px_rgba(200,168,130,0.30),inset_0_1px_0_rgba(255,255,255,0.35)]"
              >
                Continue to Compare &rarr;
              </button>
            </div>
          </div>
        </div>

        {/* ZONE LIST */}
        <div className="w-[280px] flex-none rounded-[22px] bg-gradient-to-br from-white/[0.075] to-white/2 backdrop-blur-2xl backdrop-saturate-150 border border-white/12 shadow-[0_16px_44px_rgba(0,0,0,0.38),inset_0_1px_0_rgba(255,255,255,0.09)] p-5.5 flex flex-col gap-3 overflow-y-auto">
          <div className="font-display text-[15px] font-semibold text-text">All Zones</div>
          <div className="flex flex-col gap-2">
            {assignableZones.map((zone) => {
              const materialId = assignments[zone.id];
              const compatible = !activeMaterialId || zone.recommendedMaterials.includes(activeMaterialId);
              return (
                <button
                  key={zone.id}
                  type="button"
                  onClick={() => handleZoneClick(zone.id)}
                  disabled={!!activeMaterialId && !compatible}
                  className={cn(
                    "flex items-center gap-2.5 py-2.25 px-2.75 rounded-[12px] text-left transition-colors",
                    !compatible && activeMaterialId
                      ? "bg-white/[0.015] border border-white/5 opacity-35 cursor-not-allowed"
                      : "bg-white/3 border border-white/6 hover:bg-white/5"
                  )}
                >
                  <span
                    className="w-2 h-2 rounded-full flex-none"
                    style={{ background: materialId ? getMaterial(materialId).swatchColor : ZONE_COLORS[zone.label] }}
                  />
                  <span className="flex-1 min-w-0 text-[12px] font-medium text-text truncate">
                    {zone.displayName}
                  </span>
                  {materialId && (
                    <span className="text-[9.5px] font-semibold py-0.5 px-1.5 rounded-[5px] bg-emerald-500/15 text-emerald-300 whitespace-nowrap">
                      {getMaterial(materialId).shortName}
                    </span>
                  )}
                </button>
              );
            })}
            {house.zones
              .filter((z) => z.isProtected)
              .slice(0, 4)
              .map((zone) => (
                <div
                  key={zone.id}
                  className="flex items-center gap-2.5 py-2.25 px-2.75 rounded-[12px] bg-white/[0.018] border border-white/5 opacity-65"
                >
                  <span className="w-2 h-2 rounded-full flex-none" style={{ background: "#3b82f6" }} />
                  <span className="flex-1 min-w-0 text-[12px] font-medium text-text truncate">
                    {zone.displayName}
                  </span>
                  <Lock size={11} strokeWidth={2} className="text-[#64748b] flex-none" />
                </div>
              ))}
            {protectedCount > 4 && (
              <div className="text-[11px] text-[#475569] text-center py-1">+{protectedCount - 4} more protected</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
