import type { AdSlotConfig } from "@/types/ads";

export const adSlots: Record<string, AdSlotConfig> = {
  homepageTop: { slot: "homepage-top", label: "Homepage Leaderboard" },
  homepageFeed: { slot: "homepage-feed", label: "Homepage In-Feed" },
  homepageSidebar: { slot: "homepage-sidebar", label: "Homepage Sidebar" },
  articleTop: { slot: "article-top", label: "Article Top Banner" },
  articleMid: { slot: "article-mid", label: "Article Mid-Article" },
  articleBottom: { slot: "article-bottom", label: "Article Bottom Native" },
  mobileSticky: { slot: "mobile-sticky", label: "Mobile Sticky Banner" },
};
