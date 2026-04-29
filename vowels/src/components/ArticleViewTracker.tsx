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
  }, [slug, category]);

  return null;
}
