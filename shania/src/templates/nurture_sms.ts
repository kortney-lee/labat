/**
 * nurture_sms.ts — Static SMS templates for the Shania nurture workflow.
 *
 * 7 templates (one per nurture step), condensed for SMS delivery.
 * All messages are under 160 characters after placeholder substitution
 * using typical brand/URL lengths.
 *
 * Placeholders:
 *   {{first_name}}  — recipient's first name (or blank)
 *   {{brand_name}}  — brand display name
 *   {{brand_url}}   — brand short URL
 *   {{trial_url}}   — free trial signup URL
 *   {{book_url}}    — book purchase / download URL
 *   {{cta_label}}   — short action phrase (kept brief in SMS)
 */

export type NurtureSmsTemplateId =
  | "digital_book_delivery"
  | "hardcopy_upsell"
  | "free_trial_offer_wihy"
  | "free_trial_offer_cg"
  | "book_app_bundle_wihy"
  | "book_app_bundle_cg"
  | "final_urgency";

export interface NurtureSmsTemplate {
  id: NurtureSmsTemplateId;
  brands: Array<"wihy" | "communitygroceries" | "whatishealthy" | "all">;
  trigger: string;
  /** Plain text message. Keep under 160 chars after placeholder substitution. */
  message: string;
}

// ─── Template definitions ─────────────────────────────────────────────────────

const DIGITAL_BOOK_DELIVERY: NurtureSmsTemplate = {
  id: "digital_book_delivery",
  brands: ["whatishealthy"],
  trigger: "Immediately after user requests the free digital book",
  // ~135 chars with typical URLs
  message: "Hi {{first_name}}! Your free 'What Is Healthy' digital copy is ready. Read it here: {{book_url}} — {{brand_name}}",
};

const HARDCOPY_UPSELL: NurtureSmsTemplate = {
  id: "hardcopy_upsell",
  brands: ["whatishealthy"],
  trigger: "D+2 after digital delivery",
  // ~130 chars
  message: "Enjoying the book, {{first_name}}? Get the physical hardcover — great for sharing with family. Order: {{book_url}}",
};

const FREE_TRIAL_OFFER_WIHY: NurtureSmsTemplate = {
  id: "free_trial_offer_wihy",
  brands: ["wihy"],
  trigger: "D+4 — non-buyer follow-up for WIHY",
  // ~148 chars
  message: "{{first_name}}, put your health knowledge to work. Start your FREE WIHY trial — scan food, get meal plans & more: {{trial_url}}",
};

const FREE_TRIAL_OFFER_CG: NurtureSmsTemplate = {
  id: "free_trial_offer_cg",
  brands: ["communitygroceries"],
  trigger: "D+4 — non-buyer follow-up for Community Groceries",
  // ~143 chars
  message: "{{first_name}}, feed your family better starting this week. Free Community Groceries trial — meal plans + smart lists: {{trial_url}}",
};

const BOOK_APP_BUNDLE_WIHY: NurtureSmsTemplate = {
  id: "book_app_bundle_wihy",
  brands: ["wihy", "whatishealthy"],
  trigger: "D+6 — cross-sell: book + WIHY app",
  // ~148 chars
  message: "The book shows you WHAT. WIHY shows you HOW — every day. Get both and actually change how you eat: {{trial_url}} | Book: {{book_url}}",
};

const BOOK_APP_BUNDLE_CG: NurtureSmsTemplate = {
  id: "book_app_bundle_cg",
  brands: ["communitygroceries", "whatishealthy"],
  trigger: "D+6 — cross-sell: book + Community Groceries",
  // ~150 chars
  message: "Knowledge + action = a healthier family. Get 'What Is Healthy' + Community Groceries together. Start here: {{trial_url}}",
};

const FINAL_URGENCY: NurtureSmsTemplate = {
  id: "final_urgency",
  brands: ["all"],
  trigger: "D+10 — last-chance win-back, all brands",
  // ~145 chars
  message: "{{first_name}}, this is our last message. Start your health journey today — book, app, or both: {{brand_url}} (reply STOP to opt out)",
};

// ─── Exported catalog ─────────────────────────────────────────────────────────

export const NURTURE_SMS_TEMPLATES: Record<NurtureSmsTemplateId, NurtureSmsTemplate> = {
  digital_book_delivery: DIGITAL_BOOK_DELIVERY,
  hardcopy_upsell: HARDCOPY_UPSELL,
  free_trial_offer_wihy: FREE_TRIAL_OFFER_WIHY,
  free_trial_offer_cg: FREE_TRIAL_OFFER_CG,
  book_app_bundle_wihy: BOOK_APP_BUNDLE_WIHY,
  book_app_bundle_cg: BOOK_APP_BUNDLE_CG,
  final_urgency: FINAL_URGENCY,
};

export function getSmsTemplate(id: NurtureSmsTemplateId): NurtureSmsTemplate {
  return NURTURE_SMS_TEMPLATES[id];
}
