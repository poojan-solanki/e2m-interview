"use client";

import { useEffect, useRef, useState } from "react";
import type { Zone } from "@/types";
import { getMaterial } from "@/data/materials";

const ZONE_COLORS: Record<string, string> = {
  wall: "#f59e0b",
  pillar: "#10b981",
  balcony_railing: "#8b5cf6",
  roof_parapet: "#f43f5e",
  window: "#3b82f6",
  door: "#3b82f6",
};

function isPointInPolygon(px: number, py: number, polygon: [number, number][]): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];
    const intersect = yi > py !== yj > py && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

export default function ZoneCanvas({
  imageSrc,
  imageWidth,
  imageHeight,
  zones,
  selectedZoneId,
  assignments,
  onZoneClick,
}: {
  imageSrc: string;
  imageWidth: number;
  imageHeight: number;
  zones: Zone[];
  selectedZoneId: string | null;
  assignments: Record<string, string>;
  onZoneClick: (zoneId: string) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const [hoveredZoneId, setHoveredZoneId] = useState<string | null>(null);
  const [canvasSize, setCanvasSize] = useState({ w: 900, h: 675 });
  const [mousePos, setMousePos] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    const img = new window.Image();
    img.src = imageSrc;
    img.onload = () => {
      imgRef.current = img;
      draw();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageSrc]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0].contentRect.width;
      setCanvasSize({ w, h: (w * imageHeight) / imageWidth });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [imageWidth, imageHeight]);

  const scale = canvasSize.w / imageWidth;

  function draw() {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = canvasSize.w;
    canvas.height = canvasSize.h;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    for (const zone of zones) {
      const isSelected = zone.id === selectedZoneId;
      const isHovered = zone.id === hoveredZoneId;
      const assignedMaterialId = assignments[zone.id];
      const color = assignedMaterialId
        ? getMaterial(assignedMaterialId).swatchColor
        : ZONE_COLORS[zone.label] ?? "#94a3b8";

      ctx.beginPath();
      zone.polygon.forEach(([x, y], i) => {
        const px = x * scale;
        const py = y * scale;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.closePath();

      if (zone.isProtected) {
        ctx.strokeStyle = "rgba(59,130,246,0.55)";
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 2]);
        ctx.stroke();
        ctx.setLineDash([]);
        continue;
      }

      const fillAlpha = isSelected ? 0.45 : isHovered ? 0.3 : assignedMaterialId ? 0.32 : 0.16;
      ctx.fillStyle = hexToRgba(color, fillAlpha);
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = isSelected ? 2.5 : isHovered ? 2 : 1.25;
      ctx.stroke();
    }
  }

  useEffect(draw);

  function zoneAtPoint(clientX: number, clientY: number): Zone | null {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const x = ((clientX - rect.left) / rect.width) * imageWidth;
    const y = ((clientY - rect.top) / rect.height) * imageHeight;
    for (let i = zones.length - 1; i >= 0; i--) {
      const z = zones[i];
      if (z.isProtected) continue;
      if (isPointInPolygon(x, y, z.polygon)) return z;
    }
    return null;
  }

  const hoveredZone = zones.find((z) => z.id === hoveredZoneId);

  return (
    <div
      ref={containerRef}
      className="relative flex-1 rounded-[24px] overflow-hidden border border-white/12 bg-[#05070a] shadow-[0_24px_60px_rgba(0,0,0,0.45),inset_0_0_0_1px_rgba(255,255,255,0.06)]"
    >
      <canvas
        ref={canvasRef}
        className="block w-full h-full cursor-pointer"
        onMouseMove={(e) => {
          const z = zoneAtPoint(e.clientX, e.clientY);
          setHoveredZoneId(z?.id ?? null);
          setMousePos({ x: e.clientX, y: e.clientY });
        }}
        onMouseLeave={() => setHoveredZoneId(null)}
        onClick={(e) => {
          const z = zoneAtPoint(e.clientX, e.clientY);
          if (z) onZoneClick(z.id);
        }}
      />

      {hoveredZone && mousePos && (
        <div
          className="pointer-events-none absolute w-[224px] py-3 px-3.5 rounded-[14px] bg-gradient-to-br from-[#161920]/92 to-[#0e1015]/86 backdrop-blur-md border border-white/16 shadow-[0_16px_40px_rgba(0,0,0,0.5),inset_0_1px_0_rgba(255,255,255,0.10)]"
          style={{
            left: Math.min(
              mousePos.x - (containerRef.current?.getBoundingClientRect().left ?? 0) + 16,
              canvasSize.w - 240
            ),
            top: mousePos.y - (containerRef.current?.getBoundingClientRect().top ?? 0) - 60,
          }}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <span
              className="w-2 h-2 rounded-full"
              style={{ background: ZONE_COLORS[hoveredZone.label] ?? "#94a3b8" }}
            />
            <span className="text-[12px] font-semibold text-text">{hoveredZone.displayName}</span>
          </div>
          <div className="text-[11px] text-text-muted">
            {hoveredZone.category === "railing"
              ? `${hoveredZone.runningFeet.toFixed(1)} Rft`
              : `${hoveredZone.netAreaSqft.toFixed(1)} sq ft`}{" "}
            &middot; click to assign material
          </div>
        </div>
      )}
    </div>
  );
}

function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
