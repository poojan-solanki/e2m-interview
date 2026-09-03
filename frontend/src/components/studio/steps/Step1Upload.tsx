"use client";

import { useRef, useState } from "react";
import { AlertCircle, Loader2, Sparkles, UploadCloud } from "lucide-react";
import { segmentUpload } from "@/lib/api";
import type { SampleHouse, ZoneCategory } from "@/types";

export default function Step1Upload({ onSelectHouse }: { onSelectHouse: (house: SampleHouse) => void }) {
  const [uploadPreview, setUploadPreview] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (!file || !file.type.startsWith("image/")) return;
    setUploadFile(file);
    setErrorMsg(null);
    const reader = new FileReader();
    reader.onload = (e) => setUploadPreview(e.target?.result as string);
    reader.readAsDataURL(file);
  };

  const handleAnalyze = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!uploadFile || !uploadPreview) return;
    setAnalyzing(true);
    setErrorMsg(null);

    try {
      const res = await segmentUpload(uploadFile);
      const uploadedHouse: SampleHouse = {
        id: res.houseId,
        name: uploadFile.name.replace(/\.[^/.]+$/, "") || "Uploaded Facade",
        imageSrc: uploadPreview,
        imageWidth: res.imageWidth,
        imageHeight: res.imageHeight,
        totalGrossWallAreaSqft: res.totalGrossWallAreaSqft,
        netPaintableWallAreaSqft: res.netPaintableWallAreaSqft,
        renderPreviews: {},
        zones: res.zones.map((z) => ({
          id: z.id,
          label: z.label,
          displayName: z.displayName,
          category: z.category as ZoneCategory,
          isProtected: z.isProtected,
          confidence: z.confidence,
          polygon: z.polygon,
          bbox: z.bbox,
          pixelArea: z.pixelArea,
          grossAreaSqft: z.grossAreaSqft,
          deductionsSqft: z.deductionsSqft,
          netAreaSqft: z.netAreaSqft,
          runningFeet: z.runningFeet,
          recommendedMaterials: z.recommendedMaterials,
        })),
      };
      onSelectHouse(uploadedHouse);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to analyze photo. Please try again.";
      setErrorMsg(msg);
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="relative overflow-hidden pb-20">
      <div className="pointer-events-none absolute -top-64 left-28 w-[900px] h-[900px] rounded-full bg-[radial-gradient(circle,rgba(200,168,130,0.20)_0%,rgba(200,168,130,0)_68%)]" />
      <div className="pointer-events-none absolute -bottom-80 -right-36 w-[760px] h-[760px] rounded-full bg-[radial-gradient(circle,rgba(99,102,241,0.12)_0%,rgba(99,102,241,0)_70%)]" />

      <div className="relative z-10 flex flex-col items-center px-10 pt-24 text-center">
        <div className="flex items-center gap-2 py-1.5 px-4 rounded-full bg-gradient-to-br from-accent/14 to-accent/4 border border-accent/30 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] text-[12px] font-semibold tracking-[0.10em] text-[#e8d5b7] uppercase mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-accent shadow-[0_0_8px_rgba(200,168,130,0.8)]" />
          Exterior Renovation Studio
        </div>

        <h1 className="font-display text-[54px] leading-[1.12] font-semibold mb-5 max-w-[780px] tracking-[-0.01em] bg-gradient-to-b from-white to-[#c7ccd6] bg-clip-text text-transparent">
          See your renovation
          <br />
          before you build it
        </h1>

        <p className="text-[17px] leading-relaxed text-text-muted max-w-[560px] mb-11">
          Upload a photo of your house exterior. Our AI detects walls, windows and balconies, then
          shows the redesign with a contractor-ready cost estimate.
        </p>

        <div
          className="w-[640px] p-11 rounded-[26px] bg-gradient-to-br from-white/9 to-white/3 backdrop-blur-2xl backdrop-saturate-150 border-[1.5px] border-dashed border-white/22 shadow-[0_20px_60px_rgba(0,0,0,0.40),inset_0_1px_0_rgba(255,255,255,0.10)] flex flex-col items-center gap-4.5 cursor-pointer"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            handleFiles(e.dataTransfer.files);
          }}
        >
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />

          {uploadPreview ? (
            <>
              <div className="relative w-full h-[220px] rounded-2xl overflow-hidden border border-white/12">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={uploadPreview} alt="Your upload" className="w-full h-full object-cover" />
              </div>

              {errorMsg && (
                <div className="w-full flex items-center gap-2.5 p-3 rounded-xl bg-red-500/10 border border-red-500/25 text-red-300 text-[13px] text-left">
                  <AlertCircle size={18} className="shrink-0 text-red-400" />
                  <span>{errorMsg}</span>
                </div>
              )}

              {analyzing ? (
                <div className="flex flex-col items-center gap-2.5 py-3">
                  <div className="flex items-center gap-2 text-accent text-[14px] font-medium">
                    <Loader2 size={18} className="animate-spin text-accent" />
                    Analyzing architecture with Meta SAM 3...
                  </div>
                  <div className="text-[12px] text-text-muted">
                    Detecting walls, windows, balconies, roof overhangs &amp; spatial scale...
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2.5 w-full mt-1">
                  <button
                    type="button"
                    onClick={handleAnalyze}
                    className="font-display w-full py-3.5 px-7 rounded-[13px] border border-white/25 bg-gradient-to-br from-[#ddc4a1] via-accent to-[#b8956d] text-[#241a0c] text-[15px] font-semibold shadow-[0_12px_28px_rgba(200,168,130,0.35),inset_0_1px_0_rgba(255,255,255,0.35)] flex items-center justify-center gap-2 hover:brightness-105 transition"
                  >
                    <Sparkles size={18} />
                    Analyze &amp; Renovate This House
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      inputRef.current?.click();
                    }}
                    className="text-[12px] text-text-muted hover:text-white transition"
                  >
                    Choose a different photo
                  </button>
                </div>
              )}
            </>
          ) : (
            <>
              <div className="w-[58px] h-[58px] rounded-2xl bg-gradient-to-br from-accent/22 to-accent/6 border border-accent/32 shadow-[0_8px_20px_rgba(200,168,130,0.18),inset_0_1px_0_rgba(255,255,255,0.15)] flex items-center justify-center">
                <UploadCloud size={24} strokeWidth={1.7} className="text-[#e8d5b7]" />
              </div>
              <div>
                <div className="text-[15px] font-semibold text-text mb-1">Drop your house photo here</div>
                <div className="text-[13px] text-[#64748b]">
                  JPG or PNG &middot; min. 1024&times;768 &middot; well-lit exterior shot
                </div>
              </div>
              <button
                type="button"
                className="font-display mt-1.5 py-3 px-7 rounded-[13px] border border-white/25 bg-gradient-to-br from-[#ddc4a1] via-accent to-[#b8956d] text-[#241a0c] text-[14px] font-semibold shadow-[0_12px_28px_rgba(200,168,130,0.35),inset_0_1px_0_rgba(255,255,255,0.35)]"
              >
                Browse Files
              </button>
            </>
          )}
        </div>

        <div className="mt-14 text-[11px] tracking-[0.10em] text-[#3d4451] uppercase">
          SAM 3 structural detection &nbsp;&middot;&nbsp; ControlNet material rendering &nbsp;&middot;&nbsp; IS
          1200 costing
        </div>
      </div>
    </div>
  );
}
