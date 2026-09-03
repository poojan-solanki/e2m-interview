"use client";

import { Moon } from "lucide-react";
import type { WizardStep } from "@/types";
import { cn } from "@/lib/utils";

const STEPS: { n: WizardStep; label: string }[] = [
  { n: 1, label: "Upload" },
  { n: 2, label: "Zones" },
  { n: 3, label: "Materials" },
  { n: 4, label: "Compare" },
  { n: 5, label: "Quote" },
];

export default function StudioHeader({ currentStep }: { currentStep: WizardStep }) {
  return (
    <div className="sticky top-0 z-20 flex items-center justify-between px-10 h-[76px] bg-gradient-to-b from-[#161920]/85 to-[#0e1015]/70 backdrop-blur-2xl backdrop-saturate-150 shadow-[inset_0_1px_0_rgba(255,255,255,0.08),0_12px_32px_rgba(0,0,0,0.28)]">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent/35 to-transparent" />
      <div className="absolute inset-x-0 bottom-0 h-px bg-white/8" />

      <div className="flex items-center gap-3">
        <div className="w-[34px] h-[34px] rounded-[10px] flex items-center justify-center bg-gradient-to-br from-accent/28 to-accent/8 border border-accent/35 shadow-[0_4px_14px_rgba(200,168,130,0.18),inset_0_1px_0_rgba(255,255,255,0.15)]">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#e8d5b7" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 21V9.5l9-6.2 9 6.2V21" />
            <path d="M9 21v-8h6v8" />
          </svg>
        </div>
        <span className="font-display text-[15px] tracking-[0.08em] text-text font-semibold">
          AI ARCHITECTURE STUDIO
        </span>
      </div>

      <div className="flex items-center gap-0 py-2 px-4.5 rounded-full bg-white/[0.035] border border-white/[0.07]">
        {STEPS.map((s, i) => {
          const active = s.n === currentStep;
          const done = s.n < currentStep;
          return (
            <div key={s.n} className="flex items-center">
              <div className="flex items-center gap-2">
                <div
                  className={cn(
                    "font-display w-[25px] h-[25px] rounded-full flex items-center justify-center text-[12px] font-semibold border transition-colors",
                    active || done
                      ? "bg-gradient-to-br from-accent-light to-accent border-accent text-[#1a1408]"
                      : "border-white/25 text-text-muted"
                  )}
                  style={
                    active
                      ? { boxShadow: "0 0 0 4px rgba(200,168,130,0.16), 0 2px 8px rgba(200,168,130,0.4)" }
                      : undefined
                  }
                >
                  {s.n}
                </div>
                <span
                  className={cn(
                    "text-[13px] font-semibold whitespace-nowrap",
                    active ? "text-text" : done ? "text-accent" : "text-[#64748b]"
                  )}
                >
                  {s.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={cn("w-7 h-px mx-2.5", done ? "bg-accent" : "bg-white/15")} />
              )}
            </div>
          );
        })}
      </div>

      <div className="w-9 h-9 rounded-[10px] flex items-center justify-center bg-gradient-to-br from-white/7 to-white/2 border border-white/12 shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]">
        <Moon size={16} strokeWidth={1.8} className="text-text-muted" />
      </div>
    </div>
  );
}
