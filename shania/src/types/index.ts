/** Shared types for the Shania graphics service. */

import { FormatKey } from "../config/formats";

export type ImageFormat = "png" | "webp" | "jpeg";

export type ThemeName = "wihy_default" | "dark" | "light" | "bold";
export type ArtDirection = "editorial" | "poster" | "data_lab" | "lifestyle";

export interface TemplateData {
  headline: string;
  subtext?: string;
  cta?: string;
  productName?: string;
  productImage?: string;
  score?: number;
  badge?: string;
  theme?: ThemeName;
  artDirection?: ArtDirection;
  showLogo?: boolean;
  /** ingredient_breakdown */
  items?: Array<{ name: string; score: number; verdict: string }>;
  /** comparison_split */
  leftLabel?: string;
  rightLabel?: string;
  leftItems?: string[];
  rightItems?: string[];
  /** quote_card */
  quote?: string;
  attribution?: string;
  /** photo_overlay, photo_caption */
  photoUrl?: string;
  /** stat_card */
  statNumber?: string;
  statLabel?: string;
  /** stat_card, research_card — key data findings */
  dataPoints?: string[];
  /** stat_card, research_card — citation/source line */
  source?: string;
  /** cg_community — tip variant */
  tip?: string;
  tipLabel?: string;
}

export interface GenerateRequest {
  templateId: string;
  data: TemplateData;
  format?: ImageFormat;
  outputSize?: FormatKey;
  brand?: string;
}

export interface BulkGenerateRequest {
  items: GenerateRequest[];
}

export interface GenerateResult {
  id: string;
  templateId: string;
  url: string;
  format: ImageFormat;
  width: number;
  height: number;
  createdAt: string;
}

export interface TemplateMeta {
  id: string;
  name: string;
  description: string;
  defaultFormat: FormatKey;
  requiredFields: string[];
  optionalFields: string[];
}
