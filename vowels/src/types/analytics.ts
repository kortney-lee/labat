export type AnalyticsEventName =
  | "article_view"
  | "article_scroll_depth_60"
  | "article_engaged_time_90s"
  | "article_wihy_cta_click"
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
