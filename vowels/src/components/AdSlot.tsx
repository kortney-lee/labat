"use client";

import { useEffect } from "react";

import { trackEvent } from "@/lib/analytics";

declare global {
  interface Window {
    adsbygoogle?: Array<Record<string, unknown>>;
  }
}

// Standard IAB ad sizes – set explicit min-height to prevent CLS (Core Web Vitals)
const AD_SIZES: Record<string, { label: string; minH: string }> = {
  leaderboard:   { label: "728×90",  minH: "min-h-[90px]" },
  rectangle:     { label: "300×250", minH: "min-h-[250px]" },
  halfpage:      { label: "300×600", minH: "min-h-[600px]" },
  largerect:     { label: "336×280", minH: "min-h-[280px]" },
  mobilebanner:  { label: "320×50",  minH: "min-h-[50px]" },
  infeed:        { label: "fluid",   minH: "min-h-[100px]" },
};

const ADSENSE_CLIENT = process.env.NEXT_PUBLIC_ADSENSE_CLIENT || "";
const DEFAULT_SLOT_ID = process.env.NEXT_PUBLIC_ADSENSE_SLOT_DEFAULT || "";
const AD_TEST_MODE = process.env.NEXT_PUBLIC_ADSENSE_ADTEST === "on";

const SLOT_IDS: Record<string, string> = {
  "Homepage Leaderboard": process.env.NEXT_PUBLIC_ADSENSE_SLOT_HOMEPAGE_LEADERBOARD || "",
  "Search Top Leaderboard": process.env.NEXT_PUBLIC_ADSENSE_SLOT_SEARCH_TOP_LEADERBOARD || "",
  "Research Results Inline Ad": process.env.NEXT_PUBLIC_ADSENSE_SLOT_RESEARCH_RESULTS_INLINE || "",
  "Search Mid Rectangle": process.env.NEXT_PUBLIC_ADSENSE_SLOT_SEARCH_MID_RECTANGLE || "",
  "Sidebar Rectangle": process.env.NEXT_PUBLIC_ADSENSE_SLOT_SIDEBAR_RECTANGLE || "",
  "Sidebar Half Page": process.env.NEXT_PUBLIC_ADSENSE_SLOT_SIDEBAR_HALF_PAGE || "",
  "In-Feed Content Ad": process.env.NEXT_PUBLIC_ADSENSE_SLOT_INFEED || "",
  "Content Partner Rectangle": process.env.NEXT_PUBLIC_ADSENSE_SLOT_CONTENT_PARTNER || "",
  "Mobile Anchor Banner": process.env.NEXT_PUBLIC_ADSENSE_SLOT_MOBILE_ANCHOR || "",
  "Category Leaderboard": process.env.NEXT_PUBLIC_ADSENSE_SLOT_CATEGORY_LEADERBOARD || "",
  "Category In-Grid Ad": process.env.NEXT_PUBLIC_ADSENSE_SLOT_CATEGORY_INGRID || "",
  "Category Bottom Leaderboard": process.env.NEXT_PUBLIC_ADSENSE_SLOT_CATEGORY_BOTTOM || "",
  "Article Top Leaderboard": process.env.NEXT_PUBLIC_ADSENSE_SLOT_ARTICLE_TOP || "",
  "Article Mid-Content Rectangle": process.env.NEXT_PUBLIC_ADSENSE_SLOT_ARTICLE_MID || "",
  "Article Pre-Source Native": process.env.NEXT_PUBLIC_ADSENSE_SLOT_ARTICLE_PRE_SOURCE || "",
  "Article Exit Zone Native": process.env.NEXT_PUBLIC_ADSENSE_SLOT_ARTICLE_EXIT || "",
  "Article Post-Read Leaderboard": process.env.NEXT_PUBLIC_ADSENSE_SLOT_ARTICLE_POST || "",
  "Article Sidebar Rectangle": process.env.NEXT_PUBLIC_ADSENSE_SLOT_ARTICLE_SIDEBAR_RECTANGLE || "",
  "Article Sidebar Half Page": process.env.NEXT_PUBLIC_ADSENSE_SLOT_ARTICLE_SIDEBAR_HALF_PAGE || "",
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
  const slotId = SLOT_IDS[slotName] || DEFAULT_SLOT_ID;
  const hasLiveAd = Boolean(ADSENSE_CLIENT && slotId);

  useEffect(() => {
    trackEvent({ name: "ad_impression", params: { slot: slotName, size: size ?? "custom" } });
  }, [slotName, size]);

  useEffect(() => {
    if (!hasLiveAd) return;
    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch {
      // Ignore duplicate push errors from rapid rerenders.
    }
  }, [hasLiveAd, slotName, slotId]);

  const sizeClass = size ? AD_SIZES[size].minH : "";
  const sizeLabel = size ? ` · ${AD_SIZES[size].label}` : "";

  const inner = hasLiveAd ? (
    <div className={`rounded-[1.25rem] border border-black/10 bg-sand/30 p-2 ${sizeClass} ${className}`}>
      <ins
        className="adsbygoogle block h-full w-full"
        style={{ display: "block" }}
        data-ad-client={ADSENSE_CLIENT}
        data-ad-slot={slotId}
        data-ad-format="auto"
        data-full-width-responsive="true"
        data-adtest={AD_TEST_MODE ? "on" : undefined}
        aria-label={slotName}
      />
    </div>
  ) : (
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
