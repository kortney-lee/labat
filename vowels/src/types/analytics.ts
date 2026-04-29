export type AnalyticsEventName =
  | "article_view"
  | "cta_click"
  | "newsletter_signup"
  | "ad_impression"
  | "search_usage";

export interface AnalyticsEvent {
  name: AnalyticsEventName;
  params?: Record<string, string | number | boolean>;
}
