export type AnalyticsEventName =
  | "article_view"
  | "cta_click"
  | "newsletter_signup"
  | "ad_impression"
  | "search_usage"
  | "swg_cta_click"
  | "swg_cta_impression";

export interface AnalyticsEvent {
  name: AnalyticsEventName;
  params?: Record<string, string | number | boolean>;
}
