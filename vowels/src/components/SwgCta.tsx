"use client";

import { useEffect } from "react";

import { trackEvent } from "@/lib/analytics";

interface SwgCtaProps {
  /** Visual variant — "inline" for within article flow, "sidebar" for right rail */
  variant?: "inline" | "sidebar";
}

export function SwgCta({ variant = "inline" }: SwgCtaProps) {
  // Trigger the SWG prompt programmatically when the user clicks the CTA
  const handleClick = () => {
    trackEvent({ name: "swg_cta_click", params: { variant } });
    // swg-basic.js exposes the prompt via the SWG_BASIC queue
    (self as unknown as { SWG_BASIC?: Array<(s: { showOffers: () => void }) => void> })
      .SWG_BASIC?.push((subs) => subs.showOffers());
  };

  // Log impression once mounted
  useEffect(() => {
    trackEvent({ name: "swg_cta_impression", params: { variant } });
  }, [variant]);

  if (variant === "sidebar") {
    return (
      <section className="news-card p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">Weekly Briefing</p>
        <h3 className="mt-3 font-serif text-3xl leading-tight text-slate-950">
          Get the Nutrition Briefing
        </h3>
        <p className="mt-3 text-sm leading-7 text-slate-700">
          Clear insights. Real trends. Practical actions — every week.
        </p>
        <button
          onClick={handleClick}
          className="mt-5 w-full rounded-full bg-brand px-5 py-3 text-sm font-bold uppercase tracking-[0.12em] text-white transition hover:bg-black"
        >
          Subscribe Free
        </button>
        <p className="mt-3 text-[11px] text-slate-500">Powered by Subscribe with Google.</p>
      </section>
    );
  }

  // inline — appears inside article body flow
  return (
    <section className="my-8 rounded-[1.75rem] border-2 border-brand/30 bg-brand/5 px-6 py-8 text-center">
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand">Free Weekly Briefing</p>
      <h3 className="mt-3 font-serif text-3xl leading-tight text-slate-950">
        Understanding nutrition just got easier
      </h3>
      <p className="mt-3 text-sm leading-7 text-slate-700">
        Get the Weekly Nutrition Briefing — clear insights, real trends, and practical actions delivered to your inbox.
      </p>
      <button
        onClick={handleClick}
        className="mt-6 rounded-full bg-brand px-8 py-3 text-sm font-bold uppercase tracking-[0.14em] text-white transition hover:bg-black"
      >
        Get the Weekly Briefing
      </button>
      <p className="mt-4 text-[11px] text-slate-500">Powered by Subscribe with Google · Free · No spam.</p>
    </section>
  );
}
