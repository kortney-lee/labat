"use client";

import { useEffect } from "react";

import { trackEvent } from "@/lib/analytics";

// Standard IAB ad sizes – set explicit min-height to prevent CLS (Core Web Vitals)
const AD_SIZES: Record<string, { label: string; minH: string }> = {
  leaderboard:   { label: "728×90",  minH: "min-h-[90px]" },
  rectangle:     { label: "300×250", minH: "min-h-[250px]" },
  halfpage:      { label: "300×600", minH: "min-h-[600px]" },
  largerect:     { label: "336×280", minH: "min-h-[280px]" },
  mobilebanner:  { label: "320×50",  minH: "min-h-[50px]" },
  infeed:        { label: "fluid",   minH: "min-h-[100px]" },
};

interface AdSlotProps {
  slotName: string;
  /** IAB size key — controls min-height reservation to prevent layout shift */
  size?: keyof typeof AD_SIZES;
  /** sticky: wraps in a sticky sidebar container */
  sticky?: boolean;
  className?: string;
}

export function AdSlot({ slotName, size, sticky = false, className = "" }: AdSlotProps) {
  useEffect(() => {
    trackEvent({ name: "ad_impression", params: { slot: slotName, size: size ?? "custom" } });
  }, [slotName, size]);

  const sizeClass = size ? AD_SIZES[size].minH : "";
  const sizeLabel = size ? ` · ${AD_SIZES[size].label}` : "";

  const inner = (
    <div className={`rounded-[1.25rem] border border-dashed border-black/25 bg-sand p-4 text-center ${sizeClass} ${className}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Sponsored{sizeLabel}</p>
      <p className="mt-1 text-sm font-semibold text-slate-700">{slotName}</p>
    </div>
  );

  if (sticky) {
    return <div className="sticky top-24">{inner}</div>;
  }

  return inner;
}
