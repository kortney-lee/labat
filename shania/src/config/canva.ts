/**
 * config/canva.ts — Canva integration configuration
 *
 * Stores brand-to-Canva-template mappings and API settings
 * All Canva design template IDs are set per brand for consistency
 */

import { BrandId } from "./brand";
import { logger } from "../utils/logger";

/**
 * Brand → Canva Design Template ID mapping
 *
 * Each brand has a pre-designed Canva template that can accept dynamic text fields.
 * Template IDs must be created in Canva and stored in GCP Secret Manager.
 *
 * Design template variables supported:
 * - headline: Main title text
 * - subtext: Secondary text
 * - cta: Call-to-action button text
 * - quote: Quote text (for quote templates)
 * - statNumber: Large stat number (for stat card templates)
 * - statLabel: Stat label text
 * - dataPoints: Array of key findings
 * - photoUrl: Photo/image URL to embed
 * - productImage: Product image URL
 * - items: Array of items with name/score/verdict
 * - badge: Badge/label overlay text
 * - tip: Tip/advice text
 */
export const BRAND_CANVA_TEMPLATES: Record<BrandId, string> = {
  // WIHY - Primary health brand
  // Template: Modern stat/research card with orange + blue brand colors
  wihy: process.env.CANVA_TEMPLATE_WIHY || "design_wihy_default",

  // Community Groceries - Food & recipe brand
  // Template: Warm lifestyle card with app screenshots, green accent colors
  communitygroceries: process.env.CANVA_TEMPLATE_CG || "design_cg_default",

  // Vowels - Children's nutrition book publisher
  // Template: Educational data card with purple/blue academic tones, book imagery
  vowels: process.env.CANVA_TEMPLATE_VOWELS || "design_vowels_default",

  // Snacking Well - Snack industry brand
  // Template: Product-focused card with snack imagery, gold accents
  snackingwell: process.env.CANVA_TEMPLATE_SNACKINGWELL || "design_snackingwell_default",

  // Children's Nutrition - Sub-brand (parent: vowels)
  // Template: Same as vowels (educational, family-friendly)
  childrennutrition: process.env.CANVA_TEMPLATE_CHILDRENNUTRITION || "design_vowels_default",

  // Parenting with Christ - Religious parenting brand
  // Template: Warm family-focused card with faith messaging
  parentingwithchrist:
    process.env.CANVA_TEMPLATE_PARENTINGWITHCHRIST || "design_parentingwithchrist_default",

  // Otaku Lounge - Anime/pop culture brand
  // Template: Vibrant, dynamic card with anime-inspired colors (purple, hot pink)
  otakulounge: process.env.CANVA_TEMPLATE_OTAKULOUNGE || "design_otakulounge_default",
};

/**
 * Validate that all required Canva template IDs are configured
 */
export function validateCanvaConfig(): boolean {
  const missing = Object.entries(BRAND_CANVA_TEMPLATES)
    .filter(([, templateId]) => templateId.startsWith("design_") && templateId.endsWith("_default"))
    .map(([brand]) => brand);

  if (missing.length > 0) {
    logger.warn(
      `⚠️  Canva templates not yet configured for brands: ${missing.join(", ")}. Using placeholder IDs.`,
    );
    return false;
  }

  logger.info(`✅ Canva templates configured for ${Object.keys(BRAND_CANVA_TEMPLATES).length} brands`);
  return true;
}

/**
 * Canva API configuration
 */
export const CANVA_CONFIG = {
  apiUrl: "https://api.canva.com",
  apiVersion: "v1",
  timeout: 30000, // 30 seconds for design creation + export
};

/**
 * Export formats for Canva designs
 */
export type CanvaExportFormat = "png" | "jpeg" | "pdf" | "webp";

/**
 * Get the Canva template ID for a brand
 */
export function getCanvaTemplateForBrand(brandId: BrandId): string {
  const templateId = BRAND_CANVA_TEMPLATES[brandId];
  if (!templateId) {
    throw new Error(`No Canva template configured for brand: ${brandId}`);
  }
  return templateId;
}

/**
 * Map old template IDs to Canva design fields
 * This helps translate existing template logic to Canva variable names
 */
export const OLD_TEMPLATE_TO_CANVA_MAPPING: Record<string, string> = {
  stat_card: "wihy", // Maps to stat/data card template
  research_card: "wihy",
  hook_square: "wihy",
  hook_vertical: "wihy",
  photo_overlay: "wihy",
  photo_caption: "wihy",
  quote_card: "wihy",
  cta_card: "wihy",
  comparison_split: "wihy",
  ingredient_breakdown: "wihy",
  "cg-recipe-tip": "communitygroceries",
  "cg-community": "communitygroceries",
  "cg-warm-card": "communitygroceries",
  "cg-fresh-pick": "communitygroceries",
  "vowels-clean-card": "vowels",
  "vowels-research-tip": "vowels",
  "vowels-community": "vowels",
  "vowels-data-card": "vowels",
};

/**
 * GCP Secret Manager keys for Canva credentials
 * These will be used to load credentials from Secret Manager in production
 */
export const CANVA_GCP_SECRETS = {
  apiToken: "canva-api-token", // Contains Canva API access token
  templates: "canva-brand-templates", // JSON: { brand_id: "template_id", ... }
};
