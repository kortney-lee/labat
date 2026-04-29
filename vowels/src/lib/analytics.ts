import type { AnalyticsEvent } from "@/types/analytics";

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
  }
}

export const GA_MEASUREMENT_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID || "";

export function trackEvent(event: AnalyticsEvent): void {
  if (typeof window === "undefined") return;
  if (!window.gtag) return;
  window.gtag("event", event.name, event.params || {});
}
