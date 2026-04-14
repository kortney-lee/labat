/**
 * nurture_email.ts — Static email templates for the Shania nurture workflow.
 *
 * 7 templates covering the full book + app funnel across three brands:
 *   wihy | communitygroceries | whatishealthy
 *
 * Placeholders (replaced at dispatch time):
 *   {{first_name}}     — recipient's first name (or "there" as fallback)
 *   {{brand_name}}     — brand display name
 *   {{brand_url}}      — brand website URL
 *   {{trial_url}}      — free trial signup URL
 *   {{book_url}}       — book purchase / download URL
 *   {{book_image_url}} — hosted book cover image (GCS)
 *   {{cta_label}}      — primary CTA button text
 *   {{unsubscribe_url}}— unsubscribe link
 */

export type NurtureEmailTemplateId =
  | "digital_book_delivery"
  | "hardcopy_upsell"
  | "free_trial_offer_wihy"
  | "free_trial_offer_cg"
  | "book_app_bundle_wihy"
  | "book_app_bundle_cg"
  | "final_urgency";

export interface NurtureEmailTemplate {
  id: NurtureEmailTemplateId;
  /** Which brand(s) this template is intended for. "all" = any brand. */
  brands: Array<"wihy" | "communitygroceries" | "whatishealthy" | "all">;
  /** Suggested send trigger / cadence note. */
  trigger: string;
  subject: string;
  /** Full HTML body. Uses {{placeholder}} tokens. */
  html: string;
}

// ─── Shared layout helpers ────────────────────────────────────────────────────

const emailWrap = (content: string, accentColor = "#fa5f06") => `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{{brand_name}}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:32px 16px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">

          <!-- Header bar -->
          <tr>
            <td style="background:${accentColor};padding:20px 32px;">
              <p style="margin:0;color:#ffffff;font-size:22px;font-weight:800;letter-spacing:-0.5px;">{{brand_name}}</p>
            </td>
          </tr>

          <!-- Body -->
          ${content}

          <!-- Footer -->
          <tr>
            <td style="padding:24px 32px;border-top:1px solid #f0f0f0;text-align:center;">
              <p style="margin:0;color:#9ca3af;font-size:12px;line-height:1.6;">
                You're receiving this because you requested resources from {{brand_name}}.<br/>
                <a href="{{unsubscribe_url}}" style="color:#9ca3af;">Unsubscribe</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
`.trim();

const ctaButton = (label: string, url: string, color = "#fa5f06") =>
  `<a href="${url}" style="display:inline-block;background:${color};color:#ffffff;font-size:16px;font-weight:700;text-decoration:none;padding:14px 32px;border-radius:8px;margin-top:8px;">${label}</a>`;

// ─── Template definitions ─────────────────────────────────────────────────────

const DIGITAL_BOOK_DELIVERY: NurtureEmailTemplate = {
  id: "digital_book_delivery",
  brands: ["whatishealthy"],
  trigger: "Immediately after user requests the free digital book",
  subject: "Your free copy of 'What Is Healthy' is ready 📖",
  html: emailWrap(`
  <tr>
    <td style="padding:40px 32px 24px;">
      <h1 style="margin:0 0 16px;font-size:28px;font-weight:800;color:#111827;line-height:1.2;">
        Hi {{first_name}}, your book is here!
      </h1>
      <p style="margin:0 0 24px;font-size:16px;line-height:1.7;color:#374151;">
        Thank you for requesting <strong>What Is Healthy</strong> — a research-backed guide
        to understanding what you're really putting in your body.
      </p>
    </td>
  </tr>
  <tr>
    <td style="padding:0 32px 24px;text-align:center;">
      <img src="{{book_image_url}}" alt="What Is Healthy Book Cover"
           style="max-width:220px;width:100%;border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,0.15);" />
    </td>
  </tr>
  <tr>
    <td style="padding:0 32px 32px;">
      <p style="margin:0 0 8px;font-size:15px;line-height:1.7;color:#374151;">
        Inside you'll discover:
      </p>
      <ul style="margin:0 0 24px;padding-left:20px;font-size:15px;line-height:2;color:#374151;">
        <li>How to read food labels like a researcher</li>
        <li>The 23 ingredients the food industry doesn't want you to notice</li>
        <li>Why most "healthy" marketing is designed to mislead you</li>
        <li>Simple swaps that make a real difference</li>
      </ul>
      <div style="text-align:center;">
        ${ctaButton("{{cta_label}}", "{{book_url}}", "#1e40af")}
      </div>
      <p style="margin:24px 0 0;font-size:13px;color:#9ca3af;text-align:center;">
        Powered by {{brand_name}} — <a href="{{brand_url}}" style="color:#9ca3af;">{{brand_url}}</a>
      </p>
    </td>
  </tr>
  `, "#1e40af"),
};

const HARDCOPY_UPSELL: NurtureEmailTemplate = {
  id: "hardcopy_upsell",
  brands: ["whatishealthy"],
  trigger: "D+2 after digital_book_delivery — encourage physical copy purchase",
  subject: "Want the physical copy? (It's worth it) 📚",
  html: emailWrap(`
  <tr>
    <td style="padding:40px 32px 24px;">
      <h1 style="margin:0 0 16px;font-size:28px;font-weight:800;color:#111827;line-height:1.2;">
        Hi {{first_name}}, how's the reading going?
      </h1>
      <p style="margin:0 0 16px;font-size:16px;line-height:1.7;color:#374151;">
        We hope you're enjoying <strong>What Is Healthy</strong>. A lot of our readers tell us
        they love having a physical copy they can highlight, share with family, and keep on the shelf.
      </p>
      <p style="margin:0 0 24px;font-size:16px;line-height:1.7;color:#374151;">
        The hardcover is a complete reference — every chapter, every research citation, every action guide — all in your hands.
      </p>
    </td>
  </tr>
  <tr>
    <td style="padding:0 32px 24px;text-align:center;">
      <img src="{{book_image_url}}" alt="What Is Healthy Hardcover"
           style="max-width:200px;width:100%;border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,0.15);" />
    </td>
  </tr>
  <tr>
    <td style="padding:0 32px 32px;">
      <div style="background:#f0fdf4;border-left:4px solid #16a34a;padding:16px 20px;border-radius:0 8px 8px 0;margin-bottom:24px;">
        <p style="margin:0;font-size:15px;font-weight:600;color:#15803d;">
          "I bought the digital version then immediately ordered the hardcover. Best decision."
        </p>
        <p style="margin:8px 0 0;font-size:13px;color:#6b7280;">— Verified reader</p>
      </div>
      <div style="text-align:center;">
        ${ctaButton("Order the Hardcover", "{{book_url}}", "#16a34a")}
      </div>
      <p style="margin:24px 0 0;font-size:13px;color:#9ca3af;text-align:center;">
        Questions? Reply to this email. We read every message.
      </p>
    </td>
  </tr>
  `, "#16a34a"),
};

const FREE_TRIAL_OFFER_WIHY: NurtureEmailTemplate = {
  id: "free_trial_offer_wihy",
  brands: ["wihy"],
  trigger: "D+4 for non-purchasers — nudge toward WIHY free trial",
  subject: "Still thinking? Your WIHY free trial is waiting",
  html: emailWrap(`
  <tr>
    <td style="padding:40px 32px 24px;">
      <h1 style="margin:0 0 16px;font-size:28px;font-weight:800;color:#111827;line-height:1.2;">
        {{first_name}}, your free WIHY trial is on us.
      </h1>
      <p style="margin:0 0 24px;font-size:16px;line-height:1.7;color:#374151;">
        You took the first step by learning about <em>What Is Healthy</em>. Now put that knowledge
        to work — WIHY gives you the tools to act on it every single day.
      </p>
    </td>
  </tr>
  <tr>
    <td style="padding:0 32px 24px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="padding:12px 16px;background:#fff7ed;border-radius:8px;margin-bottom:12px;display:block;">
            <p style="margin:0;font-size:15px;font-weight:700;color:#ea580c;">📱 Scan any product</p>
            <p style="margin:4px 0 0;font-size:14px;color:#374151;">Instantly know what's really in your food — from 4.1M+ analyzed products.</p>
          </td>
        </tr>
        <tr><td style="height:10px;"></td></tr>
        <tr>
          <td style="padding:12px 16px;background:#f0fdf4;border-radius:8px;">
            <p style="margin:0;font-size:15px;font-weight:700;color:#16a34a;">🥗 Get personalized meal plans</p>
            <p style="margin:4px 0 0;font-size:14px;color:#374151;">Built around your health goals, allergies, and what you actually want to eat.</p>
          </td>
        </tr>
        <tr><td style="height:10px;"></td></tr>
        <tr>
          <td style="padding:12px 16px;background:#eff6ff;border-radius:8px;">
            <p style="margin:0;font-size:15px;font-weight:700;color:#1d4ed8;">🔬 Research-backed answers</p>
            <p style="margin:4px 0 0;font-size:14px;color:#374151;">48M+ research articles. Ask anything about your health.</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="padding:24px 32px 32px;text-align:center;">
      ${ctaButton("{{cta_label}}", "{{trial_url}}", "#fa5f06")}
      <p style="margin:16px 0 0;font-size:13px;color:#9ca3af;">No credit card required. Cancel anytime.</p>
    </td>
  </tr>
  `),
};

const FREE_TRIAL_OFFER_CG: NurtureEmailTemplate = {
  id: "free_trial_offer_cg",
  brands: ["communitygroceries"],
  trigger: "D+4 for non-purchasers — nudge toward Community Groceries free trial",
  subject: "Feed your family better — free trial inside",
  html: emailWrap(`
  <tr>
    <td style="padding:40px 32px 24px;">
      <h1 style="margin:0 0 16px;font-size:28px;font-weight:800;color:#111827;line-height:1.2;">
        {{first_name}}, groceries with purpose are one click away.
      </h1>
      <p style="margin:0 0 24px;font-size:16px;line-height:1.7;color:#374151;">
        Community Groceries is more than a grocery app — it's a whole system for feeding your
        family better, spending less, and actually enjoying mealtime again.
      </p>
    </td>
  </tr>
  <tr>
    <td style="padding:0 32px 24px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="padding:12px 16px;background:#f0fdf4;border-radius:8px;margin-bottom:12px;">
            <p style="margin:0;font-size:15px;font-weight:700;color:#166534;">🗓 Weekly meal plans, done for you</p>
            <p style="margin:4px 0 0;font-size:14px;color:#374151;">Stop asking "what's for dinner?" — we plan the whole week for your family.</p>
          </td>
        </tr>
        <tr><td style="height:10px;"></td></tr>
        <tr>
          <td style="padding:12px 16px;background:#fff7ed;border-radius:8px;">
            <p style="margin:0;font-size:15px;font-weight:700;color:#c2410c;">🛒 Smart shopping lists</p>
            <p style="margin:4px 0 0;font-size:14px;color:#374151;">Auto-generated from your meal plan. Everything you need, nothing you don't.</p>
          </td>
        </tr>
        <tr><td style="height:10px;"></td></tr>
        <tr>
          <td style="padding:12px 16px;background:#eff6ff;border-radius:8px;">
            <p style="margin:0;font-size:15px;font-weight:700;color:#1d4ed8;">👨‍👩‍👧 Built for real families</p>
            <p style="margin:4px 0 0;font-size:14px;color:#374151;">Dietary needs, picky eaters, budget goals — all handled.</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="padding:24px 32px 32px;text-align:center;">
      ${ctaButton("{{cta_label}}", "{{trial_url}}", "#166534")}
      <p style="margin:16px 0 0;font-size:13px;color:#9ca3af;">Free to start. No credit card needed.</p>
    </td>
  </tr>
  `, "#166534"),
};

const BOOK_APP_BUNDLE_WIHY: NurtureEmailTemplate = {
  id: "book_app_bundle_wihy",
  brands: ["wihy", "whatishealthy"],
  trigger: "D+6 — cross-sell: book knowledge + WIHY app in daily use",
  subject: "The book taught you what. WIHY shows you how. 🔬",
  html: emailWrap(`
  <tr>
    <td style="padding:40px 32px 24px;">
      <h1 style="margin:0 0 16px;font-size:28px;font-weight:800;color:#111827;line-height:1.2;">
        {{first_name}}, the book is just the beginning.
      </h1>
      <p style="margin:0 0 24px;font-size:16px;line-height:1.7;color:#374151;">
        <em>What Is Healthy</em> shows you what the food industry has been hiding.
        WIHY turns that knowledge into daily action — right at your fingertips.
      </p>
    </td>
  </tr>
  <tr>
    <td style="padding:0 32px 24px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td width="48%" style="padding:16px;background:#1e293b;border-radius:8px;vertical-align:top;">
            <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">The Book</p>
            <p style="margin:0 0 8px;font-size:17px;font-weight:800;color:#ffffff;">What Is Healthy</p>
            <ul style="margin:0;padding-left:18px;font-size:13px;line-height:1.9;color:#cbd5e1;">
              <li>The knowledge foundation</li>
              <li>121 pages of research</li>
              <li>23 ingredients exposed</li>
              <li>Read once, reference forever</li>
            </ul>
          </td>
          <td width="4%"></td>
          <td width="48%" style="padding:16px;background:#fa5f06;border-radius:8px;vertical-align:top;">
            <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#fed7aa;text-transform:uppercase;letter-spacing:1px;">The App</p>
            <p style="margin:0 0 8px;font-size:17px;font-weight:800;color:#ffffff;">WIHY</p>
            <ul style="margin:0;padding-left:18px;font-size:13px;line-height:1.9;color:#fff7ed;">
              <li>Apply it every day</li>
              <li>Scan any product instantly</li>
              <li>Personalized meal plans</li>
              <li>48M+ research articles</li>
            </ul>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="padding:24px 32px 32px;text-align:center;">
      <p style="margin:0 0 16px;font-size:15px;font-weight:600;color:#374151;">
        Get both and actually change how you eat.
      </p>
      ${ctaButton("{{cta_label}}", "{{trial_url}}", "#fa5f06")}
      <p style="margin:12px 0 0;font-size:13px;color:#9ca3af;">
        Also grab the book: <a href="{{book_url}}" style="color:#fa5f06;">{{book_url}}</a>
      </p>
    </td>
  </tr>
  `),
};

const BOOK_APP_BUNDLE_CG: NurtureEmailTemplate = {
  id: "book_app_bundle_cg",
  brands: ["communitygroceries", "whatishealthy"],
  trigger: "D+6 — cross-sell: book knowledge + Community Groceries meal planning",
  subject: "Your healthier family starts with two things 🥦",
  html: emailWrap(`
  <tr>
    <td style="padding:40px 32px 24px;">
      <h1 style="margin:0 0 16px;font-size:28px;font-weight:800;color:#111827;line-height:1.2;">
        {{first_name}}, knowledge + action = a healthier family.
      </h1>
      <p style="margin:0 0 24px;font-size:16px;line-height:1.7;color:#374151;">
        <em>What Is Healthy</em> taught you what to eat and what to avoid.
        Community Groceries does the work of putting it all on the table — every week, for your whole family.
      </p>
    </td>
  </tr>
  <tr>
    <td style="padding:0 32px 24px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td width="48%" style="padding:16px;background:#1e293b;border-radius:8px;vertical-align:top;">
            <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">The Book</p>
            <p style="margin:0 0 8px;font-size:17px;font-weight:800;color:#ffffff;">What Is Healthy</p>
            <ul style="margin:0;padding-left:18px;font-size:13px;line-height:1.9;color:#cbd5e1;">
              <li>Understand what's in your food</li>
              <li>Decode misleading labels</li>
              <li>Research-backed decisions</li>
              <li>A guide the whole family can use</li>
            </ul>
          </td>
          <td width="4%"></td>
          <td width="48%" style="padding:16px;background:#166534;border-radius:8px;vertical-align:top;">
            <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#bbf7d0;text-transform:uppercase;letter-spacing:1px;">The App</p>
            <p style="margin:0 0 8px;font-size:17px;font-weight:800;color:#ffffff;">Community Groceries</p>
            <ul style="margin:0;padding-left:18px;font-size:13px;line-height:1.9;color:#dcfce7;">
              <li>Weekly plans built for your family</li>
              <li>Smart shopping lists, auto-generated</li>
              <li>Handles allergens & picky eaters</li>
              <li>Budget-friendly options built in</li>
            </ul>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="padding:24px 32px 32px;text-align:center;">
      <p style="margin:0 0 16px;font-size:15px;font-weight:600;color:#374151;">
        Smarter groceries. Healthier meals. Less stress.
      </p>
      ${ctaButton("{{cta_label}}", "{{trial_url}}", "#166534")}
      <p style="margin:12px 0 0;font-size:13px;color:#9ca3af;">
        Also grab the book: <a href="{{book_url}}" style="color:#166534;">{{book_url}}</a>
      </p>
    </td>
  </tr>
  `, "#166534"),
};

const FINAL_URGENCY: NurtureEmailTemplate = {
  id: "final_urgency",
  brands: ["all"],
  trigger: "D+10 — last-chance win-back for all brands",
  subject: "{{first_name}}, this is our last message to you.",
  html: emailWrap(`
  <tr>
    <td style="padding:40px 32px 24px;">
      <h1 style="margin:0 0 16px;font-size:28px;font-weight:800;color:#111827;line-height:1.2;">
        Last chance, {{first_name}}.
      </h1>
      <p style="margin:0 0 16px;font-size:16px;line-height:1.7;color:#374151;">
        We've sent you resources about <em>What Is Healthy</em> and {{brand_name}} because
        we believe you're serious about your health. But we won't keep reaching out forever.
      </p>
      <p style="margin:0 0 24px;font-size:16px;line-height:1.7;color:#374151;">
        If you're ready to stop guessing and start making informed decisions about what
        you eat — today is the day to act.
      </p>
    </td>
  </tr>
  <tr>
    <td style="padding:0 32px 24px;">
      <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:20px 24px;">
        <p style="margin:0 0 12px;font-size:15px;font-weight:700;color:#991b1b;">
          What you'll miss if you don't start:
        </p>
        <ul style="margin:0;padding-left:18px;font-size:14px;line-height:2;color:#374151;">
          <li>Continuing to eat products with hidden harmful ingredients</li>
          <li>Paying full price for "healthy" foods that are mostly marketing</li>
          <li>Struggling with meal planning that takes hours every week</li>
          <li>Not knowing what 3 out of 4 ingredients on the label actually are</li>
        </ul>
      </div>
    </td>
  </tr>
  <tr>
    <td style="padding:24px 32px 32px;text-align:center;">
      ${ctaButton("{{cta_label}}", "{{brand_url}}", "#1e40af")}
      <p style="margin:16px 0 0;font-size:14px;color:#374151;">
        Or get the book at <a href="{{book_url}}" style="color:#1e40af;font-weight:600;">{{book_url}}</a>
      </p>
      <p style="margin:16px 0 0;font-size:12px;color:#9ca3af;">
        After this, we'll stop emailing. No hard feelings — we just respect your inbox.<br/>
        <a href="{{unsubscribe_url}}" style="color:#9ca3af;">Unsubscribe</a>
      </p>
    </td>
  </tr>
  `, "#1e40af"),
};

// ─── Exported catalog ─────────────────────────────────────────────────────────

export const NURTURE_EMAIL_TEMPLATES: Record<NurtureEmailTemplateId, NurtureEmailTemplate> = {
  digital_book_delivery: DIGITAL_BOOK_DELIVERY,
  hardcopy_upsell: HARDCOPY_UPSELL,
  free_trial_offer_wihy: FREE_TRIAL_OFFER_WIHY,
  free_trial_offer_cg: FREE_TRIAL_OFFER_CG,
  book_app_bundle_wihy: BOOK_APP_BUNDLE_WIHY,
  book_app_bundle_cg: BOOK_APP_BUNDLE_CG,
  final_urgency: FINAL_URGENCY,
};

export function getEmailTemplate(id: NurtureEmailTemplateId): NurtureEmailTemplate {
  return NURTURE_EMAIL_TEMPLATES[id];
}
