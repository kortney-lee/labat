"use client";

import { useEffect } from "react";

import { trackEvent } from "@/lib/analytics";

interface AdSlotProps {
  slotName: string;
  className?: string;
}

export function AdSlot({ slotName, className = "" }: AdSlotProps) {
  useEffect(() => {
    trackEvent({ name: "ad_impression", params: { slot: slotName } });
  }, [slotName]);

  return (
    <div className={`rounded-xl border border-dashed border-sky-300 bg-sky-50 p-4 text-center text-xs font-semibold uppercase tracking-wide text-sky-700 ${className}`}>
      {slotName}
    </div>
  );
}
