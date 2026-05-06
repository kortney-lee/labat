"use client";

import { useEffect } from "react";

import { trackEvent } from "@/lib/analytics";

interface ArticleViewTrackerProps {
  slug: string;
  category: string;
}

export function ArticleViewTracker({ slug, category }: ArticleViewTrackerProps) {
  useEffect(() => {
    trackEvent({ name: "article_view", params: { slug, category } });

    let hasTrackedDepth = false;
    let hasTrackedTime = false;

    const trackDepth = () => {
      if (hasTrackedDepth) return;
      const doc = document.documentElement;
      const maxScrollable = doc.scrollHeight - window.innerHeight;
      if (maxScrollable <= 0) return;
      const depth = Math.round((window.scrollY / maxScrollable) * 100);
      if (depth >= 60) {
        hasTrackedDepth = true;
        trackEvent({ name: "article_scroll_depth_60", params: { slug, category, depth } });
      }
    };

    const trackCtaClick = (event: MouseEvent) => {
      const target = event.target as HTMLElement | null;
      const link = target?.closest("a[data-wihy-cta]") as HTMLAnchorElement | null;
      if (!link) return;

      trackEvent({
        name: "article_wihy_cta_click",
        params: {
          slug,
          category,
          label: link.textContent?.trim() || "WIHY CTA",
          href: link.href,
          placement: link.dataset.wihyCta || "inline",
        },
      });
    };

    const timeTimer = window.setTimeout(() => {
      if (hasTrackedTime) return;
      hasTrackedTime = true;
      trackEvent({ name: "article_engaged_time_90s", params: { slug, category, seconds: 90 } });
    }, 90000);

    window.addEventListener("scroll", trackDepth, { passive: true });
    document.addEventListener("click", trackCtaClick);

    trackDepth();

    return () => {
      window.removeEventListener("scroll", trackDepth);
      document.removeEventListener("click", trackCtaClick);
      window.clearTimeout(timeTimer);
    };
  }, [slug, category]);

  return null;
}
