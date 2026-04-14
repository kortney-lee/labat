/** Supported output formats with pixel dimensions. */

export interface FormatSpec {
  width: number;
  height: number;
  label: string;
}

export const FORMATS: Record<string, FormatSpec> = {
  feed_square: { width: 1080, height: 1080, label: "Feed Post (1:1)" },
  story_vertical: { width: 1080, height: 1920, label: "Story / Reel Cover (9:16)" },
  ad_landscape: { width: 1200, height: 628, label: "Ad / Social Share" },
  blog_hero: { width: 1600, height: 900, label: "Blog / SEO Hero (16:9)" },
} as const;

export type FormatKey = keyof typeof FORMATS;

export const DEFAULT_FORMAT: FormatKey = "feed_square";
