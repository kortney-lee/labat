export type AdSlotType =
  | "homepage-top"
  | "homepage-feed"
  | "homepage-sidebar"
  | "article-top"
  | "article-mid"
  | "article-bottom"
  | "mobile-sticky";

export interface AdSlotConfig {
  slot: AdSlotType;
  label: string;
  adClient?: string;
  adSlotId?: string;
}
