"use client";

import { ReactCompareSlider, ReactCompareSliderImage } from "react-compare-slider";
import { ChevronLeft, ChevronRight, Maximize2 } from "lucide-react";
import { getMaterial } from "@/data/materials";
import type { SampleHouse } from "@/types";
import { cn } from "@/lib/utils";

export default function Step4Comparison({
  house,
  assignments,
  activeTab,
  onTabChange,
  onNext,
}: {
  house: SampleHouse;
  assignments: Record<string, string>;
  activeTab: "instant" | "ai";
  onTabChange: (tab: "instant" | "ai") => void;
  onNext: () => void;
}) {
  const assignedMaterialIds = Array.from(new Set(Object.values(assignments)));
  const renderedMaterialId =
    assignedMaterialIds.find((id) => house.renderPreviews[id]) ?? "stone_cladding";
  const afterSrc = house.renderPreviews[renderedMaterialId] ?? house.imageSrc;
  const material = getMaterial(renderedMaterialId);

  const assignedZoneCount = Object.values(assignments).filter((id) => id === renderedMaterialId).length;

  return (
    <div className="relative overflow-hidden flex flex-col items-center pb-14">
      <div className="pointer-events-none absolute -top-64 -left-36 w-[700px] h-[700px] rounded-full bg-[radial-gradient(circle,rgba(200,168,130,0.12)_0%,rgba(200,168,130,0)_70%)]" />
      <div className="pointer-events-none absolute -bottom-72 -right-36 w-[760px] h-[760px] rounded-full bg-[radial-gradient(circle,rgba(99,102,241,0.10)_0%,rgba(99,102,241,0)_70%)]" />

      <div className="relative z-10 pt-9 pb-2 text-center">
        <div className="font-display text-[24px] font-semibold text-text">Before &amp; After</div>
        <div className="text-[13px] text-[#64748b] mt-1">
          Drag the divider to compare &middot; structure is pixel-locked, only materials change
        </div>
      </div>

      <div className="relative z-10 flex gap-2.5 my-5.5 p-1.25 rounded-full bg-gradient-to-br from-white/6 to-white/1.5 backdrop-blur-xl border border-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
        <button
          type="button"
          onClick={() => onTabChange("instant")}
          className={cn(
            "font-display py-2.25 px-5.5 rounded-full text-[13px] font-semibold",
            activeTab === "instant"
              ? "bg-gradient-to-br from-[#ddc4a1] to-accent text-[#241a0c] shadow-[0_6px_18px_rgba(200,168,130,0.35)]"
              : "text-text-muted"
          )}
        >
          Instant Preview
        </button>
        <button
          type="button"
          onClick={() => onTabChange("ai")}
          className={cn(
            "font-display py-2.25 px-5.5 rounded-full text-[13px] font-semibold",
            activeTab === "ai"
              ? "bg-gradient-to-br from-[#ddc4a1] to-accent text-[#241a0c] shadow-[0_6px_18px_rgba(200,168,130,0.35)]"
              : "text-text-muted"
          )}
        >
          AI Render
        </button>
      </div>

      <div className="relative z-10 w-[1180px] max-w-[92vw] rounded-[26px] overflow-hidden border border-white/14 shadow-[0_36px_90px_rgba(0,0,0,0.5),inset_0_0_0_1px_rgba(255,255,255,0.06)]">
        {activeTab === "ai" ? (
          <div className="relative aspect-[2/1] flex items-center justify-center bg-[#05070a]">
            <ReactCompareSliderImage src={house.imageSrc} alt="Original" style={{ position: "absolute", inset: 0, objectFit: "cover", opacity: 0.25 }} />
            <div className="relative z-10 max-w-[420px] text-center py-6 px-8 rounded-2xl bg-gradient-to-br from-[#161920]/90 to-[#0e1015]/80 backdrop-blur-md border border-white/14">
              <div className="text-[14px] font-semibold text-text mb-1.5">Neural render needs a GPU backend</div>
              <div className="text-[12px] text-text-muted leading-relaxed">
                This machine has no CUDA device to run ControlNet + SD inpainting. Showing the CPU instant
                preview instead &mdash; wired to the real render pipeline in Phase 5.
              </div>
            </div>
          </div>
        ) : (
          <ReactCompareSlider
            style={{ aspectRatio: "2 / 1" }}
            itemOne={<ReactCompareSliderImage src={house.imageSrc} alt="Before" />}
            itemTwo={<ReactCompareSliderImage src={afterSrc} alt="After" />}
            handle={
              <div className="flex items-center gap-1">
                <div className="bg-gradient-to-br from-[#282c36]/85 to-[#0e1015]/75 backdrop-blur-md border border-white/40 rounded-full p-1.5 shadow-[0_12px_30px_rgba(0,0,0,0.5)]">
                  <ChevronLeft className="w-3 h-3 text-white" />
                </div>
                <div className="w-0.75 h-screen max-h-[590px] bg-gradient-to-b from-transparent via-white/80 to-transparent shadow-[0_0_16px_rgba(255,255,255,0.4)]" />
                <div className="bg-gradient-to-br from-[#282c36]/85 to-[#0e1015]/75 backdrop-blur-md border border-white/40 rounded-full p-1.5 shadow-[0_12px_30px_rgba(0,0,0,0.5)]">
                  <ChevronRight className="w-3 h-3 text-white" />
                </div>
              </div>
            }
          />
        )}

        <div className="z-20 font-display absolute top-5 left-5 py-2 px-4 rounded-[11px] bg-gradient-to-br from-[#161920]/85 to-[#0e1015]/72 backdrop-blur-md border border-white/20 text-[11px] font-semibold tracking-[0.06em] text-text shadow-[0_8px_20px_rgba(0,0,0,0.35)] pointer-events-none">
          BEFORE &middot; ORIGINAL
        </div>
        <div className="z-20 font-display absolute top-5 right-5 py-2 px-4 rounded-[11px] bg-gradient-to-br from-[#4a3a24]/92 to-[#241a0c]/88 backdrop-blur-md border border-accent/55 text-[11px] font-semibold tracking-[0.06em] text-[#f8ecdb] shadow-[0_8px_20px_rgba(0,0,0,0.35)] pointer-events-none">
          AFTER &middot; AI RENOVATION
        </div>
        <div className="z-20 absolute bottom-5 right-5 w-9.5 h-9.5 rounded-[11px] bg-gradient-to-br from-[#161920]/85 to-[#0e1015]/72 backdrop-blur-md border border-white/20 flex items-center justify-center shadow-[0_8px_20px_rgba(0,0,0,0.35)]">
          <Maximize2 size={15} strokeWidth={1.8} className="text-text" />
        </div>
      </div>

      <div className="relative z-10 flex items-center justify-between w-[1180px] max-w-[92vw] mt-5.5">
        <div className="flex items-center gap-2.25 py-2.5 px-4 rounded-full bg-gradient-to-br from-white/6 to-white/1.5 backdrop-blur-xl border border-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
          <span
            className="w-4 h-4 rounded-full"
            style={{
              background: `radial-gradient(circle at 32% 28%, ${material.swatchColor}dd, ${material.swatchColor})`,
              boxShadow: `0 2px 6px ${material.swatchColor}66`,
            }}
          />
          <span className="text-[12px] text-[#cbd5e1]">
            {material.shortName} applied to {Math.max(assignedZoneCount, 1)} zone
            {assignedZoneCount === 1 ? "" : "s"}
          </span>
        </div>
        <button
          type="button"
          onClick={onNext}
          className="font-display py-3.5 px-7 rounded-[14px] border border-white/25 bg-gradient-to-br from-[#ddc4a1] via-accent to-[#b8956d] text-[#241a0c] text-[14px] font-semibold shadow-[0_14px_32px_rgba(200,168,130,0.35),inset_0_1px_0_rgba(255,255,255,0.35)]"
        >
          Continue to Quote &rarr;
        </button>
      </div>
    </div>
  );
}
