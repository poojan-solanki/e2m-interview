"use client";

import Image from "next/image";
import { Printer, X } from "lucide-react";
import { formatINR } from "@/lib/boq";
import type { BoQGroup, BoQSummary, SampleHouse } from "@/types";

export default function ReportModal({
  house,
  summary,
  groups,
  onClose,
}: {
  house: SampleHouse;
  summary: BoQSummary;
  groups: BoQGroup[];
  onClose: () => void;
}) {
  const afterSrc =
    Object.values(house.renderPreviews).find(Boolean) ?? house.imageSrc;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/70 backdrop-blur-sm py-10 print:bg-white print:py-0">
      <div
        data-report-chrome
        className="fixed top-6 right-6 flex items-center gap-2 print:hidden"
      >
        <button
          type="button"
          onClick={() => window.print()}
          className="flex items-center gap-2 py-2.5 px-4.5 rounded-xl bg-gradient-to-br from-[#ddc4a1] via-accent to-[#b8956d] text-[#241a0c] text-[13px] font-semibold shadow-lg"
        >
          <Printer size={14} strokeWidth={2.2} />
          Print / Save PDF
        </button>
        <button
          type="button"
          onClick={onClose}
          className="w-9.5 h-9.5 rounded-xl bg-white/10 border border-white/20 flex items-center justify-center text-white"
        >
          <X size={16} strokeWidth={2} />
        </button>
      </div>

      <div
        className="w-[816px] max-w-[92vw] bg-[#f4f1ec] shadow-[0_30px_80px_rgba(15,23,42,0.35)] print:shadow-none print:w-full"
        style={{ fontFamily: "var(--font-body)" }}
      >
        <div className="p-14">
          <div className="flex items-center justify-between pb-5.5 border-b-2 border-[#0f172a]">
            <div className="flex items-center gap-2.5">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#b45309" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 21V9.5l9-6.2 9 6.2V21" />
                <path d="M9 21v-8h6v8" />
              </svg>
              <span className="font-display text-[15px] font-semibold tracking-[0.05em] text-[#0f172a]">
                AI ARCHITECTURE STUDIO
              </span>
            </div>
            <div className="text-right">
              <div className="font-display text-[12px] font-semibold text-[#0f172a]">Contractor Quotation</div>
              <div className="text-[11px] text-[#64748b] mt-0.5">
                Ref #AIS-{new Date().getFullYear()}-{String(house.zones.length).padStart(4, "0")} &middot;{" "}
                {new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
              </div>
            </div>
          </div>

          <div className="flex gap-10 my-6.5">
            <div className="flex-1">
              <div className="text-[10px] tracking-[0.08em] uppercase text-[#94836b] font-semibold mb-1.5">
                Prepared For
              </div>
              <div className="text-[13px] text-[#1e293b] leading-relaxed">
                [CLIENT NAME]
                <br />
                [SITE ADDRESS]
                <br />
                [CONTACT NUMBER]
              </div>
            </div>
            <div className="flex-1">
              <div className="text-[10px] tracking-[0.08em] uppercase text-[#94836b] font-semibold mb-1.5">
                Project
              </div>
              <div className="text-[13px] text-[#1e293b] leading-relaxed">
                Exterior facade renovation
                <br />
                {house.name}
                <br />
                Ahmedabad, Gujarat market rates
              </div>
            </div>
          </div>

          <div className="flex gap-3.5 mb-7.5">
            <div className="flex-1 rounded-[10px] overflow-hidden border border-[#0f172a]/10 shadow-[0_10px_26px_rgba(15,23,42,0.12)]">
              <div className="relative w-full h-[150px]">
                <Image src={house.imageSrc} alt="Before" fill className="object-cover" />
              </div>
              <div className="py-1.75 px-2.5 bg-white text-[10px] font-semibold tracking-[0.05em] text-[#64748b] uppercase">
                Before
              </div>
            </div>
            <div className="flex-1 rounded-[10px] overflow-hidden border border-[#0f172a]/10 shadow-[0_10px_26px_rgba(15,23,42,0.12)]">
              <div className="relative w-full h-[150px]">
                <Image src={afterSrc} alt="After" fill className="object-cover" />
              </div>
              <div className="py-1.75 px-2.5 bg-white text-[10px] font-semibold tracking-[0.05em] text-[#b45309] uppercase">
                After
              </div>
            </div>
          </div>

          <div className="text-[10px] tracking-[0.08em] uppercase text-[#94836b] font-semibold mb-2.5">
            Itemized Bill of Quantities
          </div>

          <table className="w-full border-collapse">
            <thead>
              <tr>
                {["Zone", "Material", "Net Qty", "Amount"].map((h, i) => (
                  <th
                    key={h}
                    className={`text-left text-[10px] tracking-[0.06em] uppercase text-[#94836b] font-semibold pb-2.5 border-b-[1.5px] border-[#0f172a] ${
                      i === 3 ? "text-right" : ""
                    }`}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => (
                <tr key={group.groupKey} className="border-b border-[#0f172a]/10">
                  <td className="py-2.75 text-[13px] text-[#1e293b]">{group.displayName}</td>
                  <td className="py-2.75 text-[13px] text-[#1e293b]">{group.materialName}</td>
                  <td className="py-2.75 text-[13px] text-[#1e293b]">
                    {group.netArea.toFixed(1)} {group.unit === "Rft" ? "Rft" : "sq ft"}
                  </td>
                  <td className="py-2.75 text-[13px] text-[#1e293b] text-right">{formatINR(group.lineTotalInr)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="flex justify-end mt-4.5">
            <div className="w-[260px]">
              <div className="flex justify-between py-1.25 text-[12px] text-[#475569]">
                <span>Subtotal</span>
                <span>{formatINR(summary.subtotalInr)}</span>
              </div>
              <div className="flex justify-between py-1.25 text-[12px] text-[#475569]">
                <span>Contingency ({summary.contingencyPct}%)</span>
                <span>{formatINR(summary.contingencyAmountInr)}</span>
              </div>
              <div className="flex justify-between pt-3 mt-1.5 border-t-[1.5px] border-[#0f172a]">
                <span className="font-display text-[14px] font-semibold text-[#0f172a]">Grand Total</span>
                <span className="font-display text-[18px] font-bold text-[#b45309]">
                  {formatINR(summary.grandTotalInr)}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-10 pt-4 border-t border-[#0f172a]/10">
            <div className="text-[10px] leading-relaxed text-[#94a3b8]">
              Estimates are advisory, generated from AI-detected surface areas and standard Ahmedabad
              market rates. Final costs are subject to on-site verification by a licensed contractor.
              Areas computed per IS 1200 civil deduction convention.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
