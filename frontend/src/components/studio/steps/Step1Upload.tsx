"use client";

import { useRef, useState } from "react";
import Image from "next/image";
import { UploadCloud } from "lucide-react";
import { HOUSE_1 } from "@/data/sampleHouse1";
import type { SampleHouse } from "@/types";

export default function Step1Upload({ onSelectHouse }: { onSelectHouse: (house: SampleHouse) => void }) {
  const [uploadPreview, setUploadPreview] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (!file || !file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = (e) => setUploadPreview(e.target?.result as string);
    reader.readAsDataURL(file);
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
              <div className="text-[13px] text-text-muted">
                Looks great. Continue with the sample house below to see the full detection &amp;
                costing flow &mdash; live segmentation on your own photo lands in Phase 5.
              </div>
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

        <div className="my-9 flex items-center gap-3.5 text-[12px] tracking-[0.08em] text-[#475569] uppercase">
          <div className="w-14 h-px bg-gradient-to-r from-transparent to-white/16" />
          or try a sample house
          <div className="w-14 h-px bg-gradient-to-l from-transparent to-white/16" />
        </div>

        <button
          type="button"
          onClick={() => onSelectHouse(HOUSE_1)}
          className="w-[420px] rounded-[20px] overflow-hidden bg-gradient-to-br from-white/7 to-white/2 backdrop-blur-xl border border-white/12 shadow-[0_16px_40px_rgba(0,0,0,0.35),inset_0_1px_0_rgba(255,255,255,0.08)] text-left"
        >
          <div className="relative w-full h-[210px]">
            <Image src={HOUSE_1.imageSrc} alt={HOUSE_1.name} fill className="object-cover" />
          </div>
          <div className="p-4.5">
            <div className="text-[14px] font-semibold text-text mb-1">
              Sample House &mdash; {HOUSE_1.name}
            </div>
            <div className="text-[12px] text-[#64748b]">
              {HOUSE_1.zones.length} zones detected &middot; ready to render
            </div>
          </div>
        </button>

        <div className="mt-14 text-[11px] tracking-[0.10em] text-[#3d4451] uppercase">
          SAM 3 structural detection &nbsp;&middot;&nbsp; ControlNet material rendering &nbsp;&middot;&nbsp; IS
          1200 costing
        </div>
      </div>
    </div>
  );
}
