"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ReactCompareSlider, ReactCompareSliderImage } from "react-compare-slider";
import { AlertCircle, ChevronLeft, ChevronRight, Loader2, Maximize2, Sparkles } from "lucide-react";
import { getMaterial } from "@/data/materials";
import { fetchRenderPreview, pollNeuralRenderJob, startNeuralRenderJob } from "@/lib/api";
import type { SampleHouse } from "@/types";
import { cn } from "@/lib/utils";

// Stable cache key for the current zone->material assignment set — order-independent,
// so returning to an identical set of assignments hits the cache instead of
// re-rendering. The composite result depends on the *whole* assignment map, not a
// single material, so caching per-material (like the old single-material design did)
// isn't meaningful anymore.
function assignmentsKey(assignments: Record<string, string>): string {
  return JSON.stringify(Object.entries(assignments).sort(([a], [b]) => a.localeCompare(b)));
}

export default function Step4Comparison({
  house,
  assignments,
  activeTab,
  onTabChange,
  onRenderedImageChange,
  onBack,
  onNext,
}: {
  house: SampleHouse;
  assignments: Record<string, string>;
  activeTab: "instant" | "ai";
  onTabChange: (tab: "instant" | "ai") => void;
  onRenderedImageChange: (src: string | null) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const key = useMemo(() => assignmentsKey(assignments), [assignments]);
  const distinctMaterialIds = useMemo(() => Array.from(new Set(Object.values(assignments))), [assignments]);
  const assignedZoneCount = Object.keys(assignments).length;
  const materialNames = distinctMaterialIds.map((id) => getMaterial(id).shortName).join(", ");

  // Live-rendered previews from POST /api/render/preview, cached per assignment set
  const [previewCache, setPreviewCache] = useState<Record<string, string>>({});
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(false);
  const requestId = useRef(0);

  // Neural render state from POST /api/render/neural/jobs
  const [neuralCache, setNeuralCache] = useState<Record<string, string>>({});
  const [neuralJobId, setNeuralJobId] = useState<string | null>(null);
  const [neuralStatus, setNeuralStatus] = useState<"idle" | "pending" | "running" | "done" | "error">("idle");
  const [neuralError, setNeuralError] = useState<string | null>(null);
  const [neuralElapsed, setNeuralElapsed] = useState(0);
  const [neuralProgress, setNeuralProgress] = useState<{ index: number; total: number; materialId: string } | null>(
    null
  );

  useEffect(() => {
    if (assignedZoneCount === 0 || previewCache[key]) return;
    const thisRequest = ++requestId.current;
    Promise.resolve()
      .then(() => {
        if (requestId.current !== thisRequest) return;
        setPreviewLoading(true);
        setPreviewError(false);
      })
      .then(() => fetchRenderPreview(house.id, assignments))
      .then(({ imageDataUri }) => {
        if (requestId.current !== thisRequest) return;
        setPreviewCache((cache) => ({ ...cache, [key]: imageDataUri }));
      })
      .catch(() => {
        if (requestId.current === thisRequest) setPreviewError(true);
      })
      .finally(() => {
        if (requestId.current === thisRequest) setPreviewLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [house.id, key]);

  // Poll neural render job
  useEffect(() => {
    if (!neuralJobId || (neuralStatus !== "pending" && neuralStatus !== "running")) return;

    const interval = setInterval(async () => {
      try {
        const res = await pollNeuralRenderJob(neuralJobId);
        setNeuralStatus(res.status);
        if (res.elapsedSec) setNeuralElapsed(res.elapsedSec);
        if (res.totalMaterials && res.currentMaterialIndex && res.currentMaterialId) {
          setNeuralProgress({
            index: res.currentMaterialIndex,
            total: res.totalMaterials,
            materialId: res.currentMaterialId,
          });
        }

        if (res.status === "done" && res.imageUrl) {
          setNeuralCache((c) => ({ ...c, [key]: res.imageUrl! }));
          setNeuralJobId(null);
        } else if (res.status === "error") {
          setNeuralError(res.errorMessage || "Neural render failed.");
          setNeuralJobId(null);
        }
      } catch (e) {
        console.error("Neural poll error:", e);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [neuralJobId, neuralStatus, key]);

  // Surface whichever real render is currently the best available (neural > instant
  // preview > nothing) to the parent so Step 5's quote/report can show it, instead of
  // that state dying with this component when the wizard navigates away from Step 4.
  useEffect(() => {
    const best = neuralCache[key] ?? previewCache[key] ?? null;
    onRenderedImageChange(best);
  }, [neuralCache, previewCache, key, onRenderedImageChange]);

  const handleStartNeuralRender = async () => {
    setNeuralStatus("pending");
    setNeuralError(null);
    setNeuralElapsed(0);
    setNeuralProgress(null);

    try {
      const { jobId } = await startNeuralRenderJob(house.id, assignments);
      setNeuralJobId(jobId);
      setNeuralStatus("running");
    } catch (err: unknown) {
      setNeuralStatus("error");
      setNeuralError(err instanceof Error ? err.message : "Failed to start AI render");
    }
  };

  const afterSrc =
    activeTab === "ai" ? neuralCache[key] ?? previewCache[key] ?? house.imageSrc : previewCache[key] ?? house.imageSrc;

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
          AI Neural Render
        </button>
      </div>

      <div className="relative z-10 w-[1180px] max-w-[92vw] rounded-[26px] overflow-hidden border border-white/14 shadow-[0_36px_90px_rgba(0,0,0,0.5),inset_0_0_0_1px_rgba(255,255,255,0.06)]">
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

        {activeTab === "ai" && !neuralCache[key] && (
          <div className="z-30 absolute inset-0 flex items-center justify-center bg-[#05070a]/75 backdrop-blur-[4px]">
            {neuralStatus === "running" || neuralStatus === "pending" ? (
              <div className="py-6 px-8 rounded-2xl bg-gradient-to-br from-[#161920]/95 to-[#0e1015]/90 backdrop-blur-md border border-white/20 flex flex-col items-center gap-3 max-w-[440px] text-center shadow-2xl">
                <Loader2 size={28} className="animate-spin text-accent" />
                <div className="text-[16px] font-semibold text-text">Neural Inpainting in Progress</div>
                <div className="text-[12px] text-text-muted leading-relaxed">
                  {neuralProgress
                    ? `Rendering material ${neuralProgress.index} of ${neuralProgress.total}: ${getMaterial(neuralProgress.materialId).shortName}...`
                    : "Running ControlNet Canny edge guidance & SD 1.5 inpainting on RTX 3050 GPU..."}
                </div>
                <div className="text-[13px] font-mono text-accent font-medium mt-1">
                  {neuralElapsed > 0
                    ? `${Math.round(neuralElapsed)}s elapsed (~${(neuralProgress?.total ?? 1) * 4}-${(neuralProgress?.total ?? 1) * 5} min total)`
                    : "Initializing diffusion pipeline..."}
                </div>
              </div>
            ) : neuralStatus === "error" ? (
              <div className="py-6 px-8 rounded-2xl bg-gradient-to-br from-red-950/90 to-[#0e1015]/90 backdrop-blur-md border border-red-500/30 flex flex-col items-center gap-3 max-w-[440px] text-center shadow-2xl">
                <AlertCircle size={28} className="text-red-400" />
                <div className="text-[15px] font-semibold text-white">Neural Render Failed</div>
                <div className="text-[12px] text-red-300 leading-relaxed">{neuralError}</div>
                <button
                  type="button"
                  onClick={handleStartNeuralRender}
                  className="font-display mt-2 py-2 px-5 rounded-xl bg-accent text-[#241a0c] text-[13px] font-semibold hover:brightness-105 transition"
                >
                  Retry AI Render
                </button>
              </div>
            ) : (
              <div className="py-6 px-8 rounded-2xl bg-gradient-to-br from-[#161920]/95 to-[#0e1015]/90 backdrop-blur-md border border-white/20 flex flex-col items-center gap-3.5 max-w-[480px] text-center shadow-2xl">
                <div className="w-11 h-11 rounded-2xl bg-accent/20 border border-accent/40 flex items-center justify-center text-accent shadow-[0_4px_16px_rgba(200,168,130,0.25)]">
                  <Sparkles size={22} />
                </div>
                <div>
                  <div className="text-[16px] font-semibold text-text mb-1">Generate AI Neural Render</div>
                  <div className="text-[12px] text-text-muted leading-relaxed">
                    Runs ControlNet architectural edge guidance with SD 1.5 inpainting for{" "}
                    <span className="text-white font-medium">{materialNames || "your assigned materials"}</span>{" "}
                    with 100% pixel-lock on protected windows.
                    {distinctMaterialIds.length > 1 && (
                      <>
                        {" "}
                        {distinctMaterialIds.length} materials means {distinctMaterialIds.length} sequential GPU
                        passes — expect ~{distinctMaterialIds.length * 4}-{distinctMaterialIds.length * 5} min total.
                      </>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleStartNeuralRender}
                  disabled={assignedZoneCount === 0}
                  className="font-display mt-1 py-3 px-6 rounded-xl border border-white/25 bg-gradient-to-br from-[#ddc4a1] via-accent to-[#b8956d] text-[#241a0c] text-[13px] font-semibold shadow-[0_8px_20px_rgba(200,168,130,0.35)] flex items-center gap-2 hover:brightness-105 transition disabled:opacity-40"
                >
                  <Sparkles size={16} />
                  Start Neural Generation
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === "instant" && previewLoading && !previewCache[key] && (
          <div className="z-30 absolute inset-0 flex items-center justify-center bg-[#05070a]/45 backdrop-blur-[2px]">
            <div className="py-2.5 px-5 rounded-full bg-gradient-to-br from-[#161920]/90 to-[#0e1015]/85 backdrop-blur-md border border-white/20 text-[12px] text-text-muted">
              Rendering {materialNames.toLowerCase() || "preview"}&hellip;
            </div>
          </div>
        )}

        {activeTab === "instant" && assignedZoneCount === 0 && (
          <div className="z-30 absolute inset-0 flex items-center justify-center bg-[#05070a]/45 backdrop-blur-[2px]">
            <div className="py-2.5 px-5 rounded-full bg-gradient-to-br from-[#161920]/90 to-[#0e1015]/85 backdrop-blur-md border border-white/20 text-[12px] text-text-muted">
              No zones have a material assigned yet.
            </div>
          </div>
        )}

        {activeTab === "instant" && previewError && (
          <div className="z-30 absolute inset-0 flex items-center justify-center bg-[#05070a]/45 backdrop-blur-[2px]">
            <div className="py-2.5 px-5 rounded-full bg-gradient-to-br from-red-500/20 to-red-500/10 backdrop-blur-md border border-red-500/30 text-[12px] text-red-300">
              Couldn&apos;t reach the render backend &mdash; showing the original photo.
            </div>
          </div>
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
        <div className="flex items-center gap-2.25 py-2.5 px-4 rounded-full bg-gradient-to-br from-white/6 to-white/1.5 backdrop-blur-xl border border-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] max-w-[620px]">
          <div className="flex -space-x-1.5 flex-none">
            {distinctMaterialIds.slice(0, 4).map((id) => {
              const m = getMaterial(id);
              return (
                <span
                  key={id}
                  className="w-4 h-4 rounded-full border border-[#0e1015]"
                  style={{
                    background: `radial-gradient(circle at 32% 28%, ${m.swatchColor}dd, ${m.swatchColor})`,
                    boxShadow: `0 2px 6px ${m.swatchColor}66`,
                  }}
                />
              );
            })}
          </div>
          <span className="text-[12px] text-[#cbd5e1] truncate">
            {distinctMaterialIds.length === 0
              ? "No materials assigned"
              : `${materialNames} applied to ${assignedZoneCount} zone${assignedZoneCount === 1 ? "" : "s"}`}
          </span>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={onBack}
            className="py-3.5 px-4.5 rounded-[14px] border border-white/15 bg-white/4 text-text-muted hover:text-text hover:bg-white/7 transition-colors flex items-center justify-center"
          >
            <ChevronLeft size={17} strokeWidth={2.2} />
          </button>
          <button
            type="button"
            onClick={onNext}
            className="font-display py-3.5 px-7 rounded-[14px] border border-white/25 bg-gradient-to-br from-[#ddc4a1] via-accent to-[#b8956d] text-[#241a0c] text-[14px] font-semibold shadow-[0_14px_32px_rgba(200,168,130,0.35),inset_0_1px_0_rgba(255,255,255,0.35)]"
          >
            Continue to Quote &rarr;
          </button>
        </div>
      </div>
    </div>
  );
}
