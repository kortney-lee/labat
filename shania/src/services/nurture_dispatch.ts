/**
 * nurture_dispatch.ts — Send static nurture email/SMS templates to a user.
 *
 * Flow:
 *   1. Caller passes templateId + brand + recipient info
 *   2. Service resolves brand-specific placeholder values
 *   3. Template is rendered (all {{tokens}} replaced)
 *   4. Email → POSTed to Otaku Master agent → auth.wihy.ai delivery
 *   5. SMS   → POSTed to Otaku Master agent → auth.wihy.ai SMS delivery
 *
 * Supported brands: wihy | communitygroceries | whatishealthy
 *
 * Book image assets (uploaded to GCS):
 *   wihy-web-assets/images/book/BookGreen.jpg    (delivery / launch)
 *   wihy-web-assets/images/book/Book1.jpg        (hardcopy upsell)
 *   wihy-web-assets/images/book/BookOrange.jpg   (bundle / urgency)
 *   wihy-web-assets/images/book/Book6.jpg        (CG bundle)
 */

import { logger } from "../utils/logger";
import {
  NurtureEmailTemplateId,
  NURTURE_EMAIL_TEMPLATES,
} from "../templates/nurture_email";
import {
  NurtureSmsTemplateId,
  NURTURE_SMS_TEMPLATES,
} from "../templates/nurture_sms";

// ─── Types ────────────────────────────────────────────────────────────────────

export type NurtureTemplateId = NurtureEmailTemplateId; // email and SMS share the same IDs

export type NurtureBrand = "wihy" | "communitygroceries" | "whatishealthy";

export type NurtureChannel = "email" | "sms" | "both";

export interface NurtureRecipient {
  /** First name — falls back to "there" if not provided. */
  name?: string;
  /** Required when channel is "email" or "both". */
  email?: string;
  /** E.164 format (e.g. "+12125550100"). Required when channel is "sms" or "both". */
  phone?: string;
}

/** Override any auto-resolved placeholder value. */
export interface PlaceholderOverrides {
  first_name?: string;
  brand_name?: string;
  brand_url?: string;
  trial_url?: string;
  book_url?: string;
  book_image_url?: string;
  cta_label?: string;
  unsubscribe_url?: string;
}

export interface NurtureDispatchInput {
  templateId: NurtureTemplateId;
  brand: NurtureBrand;
  channel: NurtureChannel;
  recipient: NurtureRecipient;
  overrides?: PlaceholderOverrides;
}

export interface NurtureDispatchResult {
  templateId: NurtureTemplateId;
  brand: NurtureBrand;
  channelsSent: NurtureChannel[];
  errors: string[];
}

// ─── Brand defaults ───────────────────────────────────────────────────────────

interface BrandDefaults {
  brand_name: string;
  brand_url: string;
  trial_url: string;
  book_url: string;
  book_image_url: string;
  cta_label: string;
  unsubscribe_url: string;
}

const BRAND_DEFAULTS: Record<NurtureBrand, BrandDefaults> = {
  wihy: {
    brand_name: "WIHY",
    brand_url: "https://wihy.ai",
    trial_url: "https://wihy.ai/start",
    book_url: "https://whatishealthy.org",
    book_image_url: "https://storage.googleapis.com/wihy-web-assets/images/book/BookOrange.jpg",
    cta_label: "Start Free Trial",
    unsubscribe_url: "https://wihy.ai/unsubscribe",
  },
  communitygroceries: {
    brand_name: "Community Groceries",
    brand_url: "https://communitygroceries.com",
    trial_url: "https://communitygroceries.com/start",
    book_url: "https://whatishealthy.org",
    book_image_url: "https://storage.googleapis.com/wihy-web-assets/images/book/Book6.jpg",
    cta_label: "Start Free Trial",
    unsubscribe_url: "https://communitygroceries.com/unsubscribe",
  },
  whatishealthy: {
    brand_name: "What Is Healthy",
    brand_url: "https://whatishealthy.org",
    trial_url: "https://whatishealthy.org",
    book_url: "https://whatishealthy.org",
    book_image_url: "https://storage.googleapis.com/wihy-web-assets/images/book/BookGreen.jpg",
    cta_label: "Get Your Copy",
    unsubscribe_url: "https://whatishealthy.org/unsubscribe",
  },
};

/** Book cover image assigned per template to match the messaging tone. */
const TEMPLATE_BOOK_IMAGE: Partial<Record<NurtureTemplateId, Record<NurtureBrand, string>>> = {
  digital_book_delivery: {
    wihy: "https://storage.googleapis.com/wihy-web-assets/images/book/BookGreen.jpg",
    communitygroceries: "https://storage.googleapis.com/wihy-web-assets/images/book/BookGreen.jpg",
    whatishealthy: "https://storage.googleapis.com/wihy-web-assets/images/book/BookGreen.jpg",
  },
  hardcopy_upsell: {
    wihy: "https://storage.googleapis.com/wihy-web-assets/images/book/Book1.jpg",
    communitygroceries: "https://storage.googleapis.com/wihy-web-assets/images/book/Book1.jpg",
    whatishealthy: "https://storage.googleapis.com/wihy-web-assets/images/book/Book1.jpg",
  },
  book_app_bundle_wihy: {
    wihy: "https://storage.googleapis.com/wihy-web-assets/images/book/BookOrange.jpg",
    communitygroceries: "https://storage.googleapis.com/wihy-web-assets/images/book/BookOrange.jpg",
    whatishealthy: "https://storage.googleapis.com/wihy-web-assets/images/book/BookOrange.jpg",
  },
  book_app_bundle_cg: {
    wihy: "https://storage.googleapis.com/wihy-web-assets/images/book/Book6.jpg",
    communitygroceries: "https://storage.googleapis.com/wihy-web-assets/images/book/Book6.jpg",
    whatishealthy: "https://storage.googleapis.com/wihy-web-assets/images/book/Book6.jpg",
  },
  final_urgency: {
    wihy: "https://storage.googleapis.com/wihy-web-assets/images/book/Book9.jpg",
    communitygroceries: "https://storage.googleapis.com/wihy-web-assets/images/book/Book9.jpg",
    whatishealthy: "https://storage.googleapis.com/wihy-web-assets/images/book/Book9.jpg",
  },
};

// ─── Placeholder resolution ───────────────────────────────────────────────────

function resolvePlaceholders(
  templateId: NurtureTemplateId,
  brand: NurtureBrand,
  recipient: NurtureRecipient,
  overrides?: PlaceholderOverrides,
): Record<string, string> {
  const defaults = BRAND_DEFAULTS[brand];
  const bookImage =
    TEMPLATE_BOOK_IMAGE[templateId]?.[brand] ?? defaults.book_image_url;

  return {
    first_name: overrides?.first_name ?? recipient.name ?? "there",
    brand_name: overrides?.brand_name ?? defaults.brand_name,
    brand_url: overrides?.brand_url ?? defaults.brand_url,
    trial_url: overrides?.trial_url ?? defaults.trial_url,
    book_url: overrides?.book_url ?? defaults.book_url,
    book_image_url: overrides?.book_image_url ?? bookImage,
    cta_label: overrides?.cta_label ?? defaults.cta_label,
    unsubscribe_url: overrides?.unsubscribe_url ?? defaults.unsubscribe_url,
  };
}

function renderTemplate(template: string, placeholders: Record<string, string>): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_, key) => placeholders[key] ?? `{{${key}}}`);
}

// ─── Transport ────────────────────────────────────────────────────────────────

const MASTER_AGENT_URL = "https://wihy-master-agent-n4l2vldq3q-uc.a.run.app";
const ADMIN_TOKEN = process.env.INTERNAL_ADMIN_TOKEN || "";

async function sendViaOtakuMaster(payload: {
  title: string;
  message: string;
  htmlBody?: string;
  recipient: { email?: string; phone?: string };
  templateId: string;
  brand: string;
  channel: "email" | "sms";
}): Promise<void> {
  if (!ADMIN_TOKEN) {
    logger.warn("INTERNAL_ADMIN_TOKEN not set — skipping nurture dispatch");
    return;
  }

  const resp = await fetch(`${MASTER_AGENT_URL}/api/otaku/master/alert`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": ADMIN_TOKEN,
    },
    body: JSON.stringify({
      severity: "info",
      title: payload.title,
      message: payload.message,
      html_body: payload.htmlBody,
      service: "wihy-shania-graphics",
      recipient: payload.recipient,
      details: {
        templateId: payload.templateId,
        brand: payload.brand,
        channel: payload.channel,
        type: "nurture",
      },
    }),
  });

  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Otaku Master alert failed: ${resp.status} ${body}`);
  }
}

// ─── Main dispatch function ───────────────────────────────────────────────────

/**
 * Dispatch a nurture template to a recipient via email, SMS, or both.
 * Errors per channel are collected and returned — partial success is allowed.
 */
export async function dispatchNurtureTemplate(
  input: NurtureDispatchInput,
): Promise<NurtureDispatchResult> {
  const { templateId, brand, channel, recipient, overrides } = input;
  const placeholders = resolvePlaceholders(templateId, brand, recipient, overrides);
  const channelsSent: NurtureChannel[] = [];
  const errors: string[] = [];

  const sendEmail = channel === "email" || channel === "both";
  const sendSms = channel === "sms" || channel === "both";

  // ── Email ──
  if (sendEmail) {
    if (!recipient.email) {
      errors.push("email: recipient.email is required for email channel");
    } else {
      const tpl = NURTURE_EMAIL_TEMPLATES[templateId];
      if (!tpl) {
        errors.push(`email: unknown templateId "${templateId}"`);
      } else {
        try {
          const subject = renderTemplate(tpl.subject, placeholders);
          const htmlBody = renderTemplate(tpl.html, placeholders);

          await sendViaOtakuMaster({
            title: subject,
            message: `Nurture email: ${templateId} for ${brand}`,
            htmlBody,
            recipient: { email: recipient.email },
            templateId,
            brand,
            channel: "email",
          });

          channelsSent.push("email");
          logger.info(`Nurture email sent: ${templateId} → ${recipient.email} (${brand})`);
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : String(err);
          errors.push(`email: ${msg}`);
          logger.warn(`Nurture email failed [${templateId}]: ${msg}`);
        }
      }
    }
  }

  // ── SMS ──
  if (sendSms) {
    if (!recipient.phone) {
      errors.push("sms: recipient.phone is required for sms channel");
    } else {
      const tpl = NURTURE_SMS_TEMPLATES[templateId as NurtureSmsTemplateId];
      if (!tpl) {
        errors.push(`sms: unknown templateId "${templateId}"`);
      } else {
        try {
          const message = renderTemplate(tpl.message, placeholders);

          await sendViaOtakuMaster({
            title: `SMS: ${templateId}`,
            message,
            recipient: { phone: recipient.phone },
            templateId,
            brand,
            channel: "sms",
          });

          channelsSent.push("sms");
          logger.info(`Nurture SMS sent: ${templateId} → ${recipient.phone} (${brand})`);
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : String(err);
          errors.push(`sms: ${msg}`);
          logger.warn(`Nurture SMS failed [${templateId}]: ${msg}`);
        }
      }
    }
  }

  return { templateId, brand, channelsSent, errors };
}

// ─── Convenience: dispatch by trigger event ───────────────────────────────────

/**
 * Map a trigger event name to the correct template + brand + channel.
 * Used by downstream workflows to avoid coupling to templateIds directly.
 *
 * Trigger events:
 *   "book_requested"          → digital_book_delivery (whatishealthy)
 *   "book_delivered_d2"       → hardcopy_upsell (whatishealthy)
 *   "no_purchase_wihy_d4"     → free_trial_offer_wihy
 *   "no_purchase_cg_d4"       → free_trial_offer_cg
 *   "bundle_wihy_d6"          → book_app_bundle_wihy
 *   "bundle_cg_d6"            → book_app_bundle_cg
 *   "final_urgency_d10"       → final_urgency (infers brand from input)
 */
const TRIGGER_MAP: Record<
  string,
  { templateId: NurtureTemplateId; brand: NurtureBrand }
> = {
  book_requested: { templateId: "digital_book_delivery", brand: "whatishealthy" },
  book_delivered_d2: { templateId: "hardcopy_upsell", brand: "whatishealthy" },
  no_purchase_wihy_d4: { templateId: "free_trial_offer_wihy", brand: "wihy" },
  no_purchase_cg_d4: { templateId: "free_trial_offer_cg", brand: "communitygroceries" },
  bundle_wihy_d6: { templateId: "book_app_bundle_wihy", brand: "wihy" },
  bundle_cg_d6: { templateId: "book_app_bundle_cg", brand: "communitygroceries" },
  final_urgency_d10: { templateId: "final_urgency", brand: "whatishealthy" },
};

export async function dispatchByTrigger(
  trigger: string,
  recipient: NurtureRecipient,
  channel: NurtureChannel = "both",
  overrides?: PlaceholderOverrides,
): Promise<NurtureDispatchResult | null> {
  const mapping = TRIGGER_MAP[trigger];
  if (!mapping) {
    logger.warn(`dispatchByTrigger: unknown trigger "${trigger}"`);
    return null;
  }

  return dispatchNurtureTemplate({
    templateId: mapping.templateId,
    brand: mapping.brand,
    channel,
    recipient,
    overrides,
  });
}
